"""Demo portfolio change report notifier.

POST後の取引一覧+ポートフォリオ概況をメール送信する軽量ヘルパー。
EmailClient のみを共通基盤として利用する。
"""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.external.email_client import EmailClient

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "demo"
SUBJECT_MAX_LEN = 40
VALUATION_HISTORY_TAIL = 7


def _build_env() -> Environment:
    """Jinja2 Environment 構築（html のみ autoescape）."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html", "j2"), default_for_string=False, default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _fetch_json(url: str, timeout: int) -> Optional[Any]:
    """API を叩いて success レスの data だけ返す. 失敗時 None."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("fetch failed: url=%s err=%s", url, exc)
        return None
    if not isinstance(payload, dict) or not payload.get("success"):
        logger.warning("fetch non-success: url=%s payload=%s", url, payload)
        return None
    return payload.get("data")


def fetch_portfolio_snapshot(base_url: str, timeout: int = 10) -> Dict[str, Any]:
    """3つの demo API をまとめて取得（graceful degrade）."""
    base = base_url.rstrip("/")
    errors: List[str] = []
    portfolio = _fetch_json(f"{base}/api/v1/demo/portfolio", timeout)
    if portfolio is None:
        errors.append("portfolio")
    holdings = _fetch_json(f"{base}/api/v1/demo/portfolio/holdings", timeout)
    if holdings is None:
        errors.append("holdings")
    history = _fetch_json(
        f"{base}/api/v1/demo/portfolio/valuation-history?period=1m", timeout
    )
    if history is None:
        errors.append("valuation_history")
        tail = None
    else:
        tail = history[-VALUATION_HISTORY_TAIL:] if isinstance(history, list) else None
    return {
        "portfolio": portfolio,
        "holdings": holdings if isinstance(holdings, list) else None,
        "valuation_history": tail,
        "errors": errors,
    }


STATUS_LABELS: Dict[str, str] = {
    "success": "✅ 成功",
    "failed": "❌ 失敗",
    "skipped": "⏭ スキップ",
    "dry_run": "🔍 dry-run",
}


def _count_results(trade_results: List[Dict]) -> Tuple[int, int, int]:
    """成功・失敗・スキップ件数（dry_run は失敗にカウントしない）."""
    succeeded = sum(1 for t in trade_results if t.get("status") == "success")
    failed = sum(1 for t in trade_results if t.get("status") == "failed")
    skipped = sum(1 for t in trade_results if t.get("status") == "skipped")
    return succeeded, failed, skipped


def _format_yen(amount: float) -> str:
    """¥1,015,200 形式（K表記しない）."""
    try:
        return f"¥{int(round(amount)):,}"
    except (TypeError, ValueError):
        return "¥-"


def build_subject(
    trade_results: List[Dict],
    snapshot: Dict[str, Any],
    today_jst: date,
    dry_run: bool = False,
) -> str:
    """40字以内の件名（4パターン）."""
    md = today_jst.strftime("%-m/%-d")
    total = len(trade_results)
    succeeded, failed, _skipped = _count_results(trade_results)
    portfolio = snapshot.get("portfolio") or {}
    asset = portfolio.get("total_asset")
    pct = portfolio.get("daily_change_total_asset_percent")
    asset_str = _format_yen(asset) if asset is not None else "¥-"
    pct_str = f" ({pct:+.1f}%)" if isinstance(pct, (int, float)) else ""

    if dry_run:
        subject = f"[{md} demo/dry-run] 提案{total}件 (POST未実行)"
    elif failed == total and total > 0:
        subject = f"[{md} demo] 取引{total}件全失敗 ❌"
    elif failed > 0:
        subject = f"[{md} demo] 取引{succeeded}/{total}件成功 ⚠️ 資産{asset_str}{pct_str}"
    else:
        subject = f"[{md} demo] 取引{succeeded}件・資産{asset_str}{pct_str}"
    # 40字制約: 超過時はパーセント・金額を順に切り落として短縮
    if len(subject) > SUBJECT_MAX_LEN and pct_str:
        subject = subject.replace(pct_str, "")
    if len(subject) > SUBJECT_MAX_LEN and asset_str in subject:
        subject = subject.replace(f"資産{asset_str}", "資産¥-")
    return subject


def _build_holdings_sorted(
    holdings: Optional[List[Dict]], total_value: float
) -> List[Dict]:
    """構成比降順の保有銘柄リスト（テンプレ用整形）."""
    if not holdings:
        return []
    enriched: List[Dict] = []
    for h in holdings:
        cv = float(h.get("current_value") or 0)
        weight = (cv / total_value * 100.0) if total_value > 0 else 0.0
        etf_info = h.get("etf_info") or h.get("etf") or {}
        enriched.append({
            "etf_code": h.get("etf_code"),
            "etf_name": (etf_info or {}).get("name"),
            "quantity": h.get("quantity") or 0,
            "current_price": h.get("current_price") or 0,
            "current_value": cv,
            "unrealized_pnl": h.get("unrealized_pnl") or 0,
            "unrealized_pnl_percent": h.get("unrealized_pnl_percent") or 0,
            "weight_pct": weight,
        })
    enriched.sort(key=lambda x: x["weight_pct"], reverse=True)
    return enriched


def _daily_change_text(portfolio: Optional[Dict]) -> Tuple[str, str]:
    """前日比テキストと色（緑/赤/グレー）を返す."""
    if not portfolio:
        return "-", "#666"
    diff = portfolio.get("daily_change_total_asset")
    pct = portfolio.get("daily_change_total_asset_percent")
    if diff is None or pct is None:
        return "-", "#666"
    color = "#27ae60" if diff >= 0 else "#c0392b"
    return f"{diff:+,.0f}円 ({pct:+.2f}%)", color


def _build_failed_details(trade_results: List[Dict]) -> List[Dict]:
    """失敗のみ抽出."""
    return [
        {
            "etf_code": t.get("etf_code"),
            "trade_type": t.get("trade_type"),
            "quantity": t.get("quantity") or 0,
            "http_status": t.get("http_status"),
            "error_message": t.get("error_message"),
        }
        for t in trade_results
        if t.get("status") not in ("success", "skipped")
    ]


def _enrich_trade_results(
    trade_results: List[Dict], holdings: Optional[List[Dict]]
) -> List[Dict]:
    """holdings から etf_code → name の辞書を作り、各取引に etf_name と
    status_label を付与した新リストを返す（元リストは変更しない）。"""
    name_map: Dict[str, str] = {}
    for h in holdings or []:
        code = h.get("etf_code")
        info = h.get("etf_info") or h.get("etf") or {}
        name = (info or {}).get("name")
        if code and name:
            name_map[code] = name
    enriched: List[Dict] = []
    for t in trade_results:
        copy = dict(t)
        copy.setdefault("etf_name", name_map.get(t.get("etf_code"), "-"))
        copy["status_label"] = STATUS_LABELS.get(t.get("status", ""), t.get("status", ""))
        enriched.append(copy)
    return enriched


def render_email(
    trade_results: List[Dict],
    snapshot: Dict[str, Any],
    today_jst: date,
    dry_run: bool,
    batch_log_id: Optional[int],
) -> Tuple[str, str]:
    """Jinja2 でレンダリング. (plain_md, html) を返す."""
    env = _build_env()
    succeeded, failed, skipped = _count_results(trade_results)
    portfolio = snapshot.get("portfolio") or {}
    total_value = float(portfolio.get("total_value") or 0)
    daily_text, daily_color = _daily_change_text(portfolio)
    enriched_results = _enrich_trade_results(trade_results, snapshot.get("holdings"))
    params = {
        "subject": build_subject(trade_results, snapshot, today_jst, dry_run),
        "trade_results": enriched_results,
        "snapshot": snapshot,
        "today_iso": today_jst.isoformat(),
        "dry_run": dry_run,
        "batch_log_id": batch_log_id,
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "holdings_sorted": _build_holdings_sorted(snapshot.get("holdings"), total_value),
        "daily_change_text": daily_text,
        "daily_change_color": daily_color,
        "failed_details": _build_failed_details(trade_results),
    }
    md = env.get_template("portfolio_change.md.j2").render(**params)
    html = env.get_template("portfolio_change.html.j2").render(**params)
    return md, html


def should_send(
    trigger: str,
    enabled: bool,
    dry_run: bool,
    succeeded: int,
    failed: int,
) -> bool:
    """送信判定マトリクス."""
    if not enabled:
        return False
    if trigger == "never":
        return False
    if trigger == "always":
        return True
    if trigger == "on_trade":
        return (not dry_run) and (succeeded + failed) > 0
    return False


def notify(
    trade_results: List[Dict],
    today_jst: date,
    dry_run: bool,
    batch_log_id: Optional[int],
    base_url: str = "http://localhost:8902",
) -> bool:
    """エントリ. 環境変数で有効化制御. SMTP例外は捕捉."""
    enabled = os.environ.get("DEMO_PORTFOLIO_REPORT_ENABLED", "0") == "1"
    trigger = os.environ.get("DEMO_PORTFOLIO_REPORT_TRIGGER", "on_trade")
    succeeded, failed, _ = _count_results(trade_results)
    if not should_send(trigger, enabled, dry_run, succeeded, failed):
        logger.info(
            "demo notify skipped: enabled=%s trigger=%s dry_run=%s succeeded=%d failed=%d",
            enabled, trigger, dry_run, succeeded, failed,
        )
        return False
    try:
        snapshot = fetch_portfolio_snapshot(base_url)
        subject = build_subject(trade_results, snapshot, today_jst, dry_run)
        md, html = render_email(
            trade_results, snapshot, today_jst, dry_run, batch_log_id
        )
        client = EmailClient()
        return client.send(subject, md, html)
    except Exception as exc:  # noqa: BLE001
        logger.error("demo notify failed: %s", exc, exc_info=True)
        return False
