"""ETF Rating notifier.

`/etf-rating` スキルが生成した `email_payload.json` を読み込み、
Jinja2 でメール本文を組み立てて EmailClient.send で送信する。

fail-soft 設計: SMTP/テンプレ/JSON 不正でも例外を呼び出し元に投げず、
False を返してバッチ全体を止めないようにする（呼び出し側でログ済み）。
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.external.email_client import EmailClient

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "etf_rating"
JST = timezone(timedelta(hours=9))

# calc_params.json の探索パス候補（ホスト直接実行 / Docker / 環境変数）.
# どこから実行されても見つかるよう複数候補を試す（fail-soft）.
def _calc_params_candidates() -> List[Path]:
    here = Path(__file__).resolve()
    candidates: List[Path] = []
    # 1. 明示環境変数（最優先）
    env_path = os.environ.get("ETF_RATING_CALC_PARAMS_PATH")
    if env_path:
        candidates.append(Path(env_path))
    # 2. ホスト直接実行: backend/src/services/notifier.py → parents[3] = プロジェクトルート
    candidates.append(here.parents[3] / ".claude/skills/etf-rating/calc_params.json")
    # 3. Docker コンテナ実行: /app/src/services/notifier.py → APP_BASE_DIR=/app
    app_base = os.environ.get("APP_BASE_DIR")
    if app_base:
        candidates.append(Path(app_base) / ".claude/skills/etf-rating/calc_params.json")
    # 4. CWD 起点（cron 等から相対実行された場合）
    candidates.append(Path.cwd() / ".claude/skills/etf-rating/calc_params.json")
    return candidates


def _load_calc_params() -> Dict[str, Any]:
    """calc_params.json を起動時に1回読み込む.

    SSOT として `.claude/skills/etf-rating/calc_params.json` の `mail` セクションを参照する。
    複数のパス候補を順に試し、最初に見つかったものを使用する。
    全候補不在・JSON破損・キー欠損はフォールバック（fail-soft）。
    """
    last_err: Optional[Exception] = None
    for path in _calc_params_candidates():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            last_err = exc
            continue
    logger.warning(
        "calc_params load failed (using defaults): last_err=%s", last_err,
    )
    return {}


_CALC_PARAMS = _load_calc_params()
_MAIL_PARAMS = _CALC_PARAMS.get("mail", {}) if isinstance(_CALC_PARAMS, dict) else {}

# 件名最大字数（既定40字）
SUBJECT_MAX_LEN = int(_MAIL_PARAMS.get("subject_max_chars", 40))

# 2段階閾値（WARN: ログ警告のみ / ERROR: Gmail clip 現実的リスク警告強化）
HTML_SIZE_WARN_BYTES = int(_MAIL_PARAMS.get("html_size_warn_kb", 90)) * 1024
HTML_SIZE_ERROR_BYTES = int(_MAIL_PARAMS.get("html_size_error_kb", 100)) * 1024

# flags リスト内の type 値から「追い風」「警戒」件数を集計するためのキー集合。
# Phase 1/2 で生成される type 値とテンプレ表記の対応:
#   - strong_tailwind / strong_bullish → 強い追い風
#   - severe_risk / critical_risk / warning → 警戒
TAILWIND_FLAG_TYPES = frozenset({"strong_tailwind", "strong_bullish"})
WARNING_FLAG_TYPES = frozenset({"severe_risk", "critical_risk", "warning"})


def _build_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(
            # html.j2 のみ autoescape ON. md.j2 は明示的に除外して
            # Markdown テンプレートで意図しない HTML エスケープ事故を防ぐ
            enabled_extensions=("html.j2", "html"),
            default_for_string=False,
            default=False,
        ),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _load_payload(payload_path: Path) -> Optional[Dict[str, Any]]:
    """JSON 読込. 失敗時 None."""
    try:
        with payload_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("payload load failed: path=%s err=%s", payload_path, exc)
        return None
    if not isinstance(data, dict):
        logger.error("payload root is not dict: type=%s", type(data).__name__)
        return None
    return data


def _truncate_subject(subject: str) -> str:
    """件名40字以内に丸める（超過時は末尾を `…` 置換）."""
    if len(subject) <= SUBJECT_MAX_LEN:
        return subject
    return subject[: SUBJECT_MAX_LEN - 1] + "…"


def _count_flag_types(flags: Any) -> Tuple[int, int]:
    """flags リストから (強い追い風件数, 警戒件数) を集計する.

    Phase 1/2 が生成する flags リストの各要素は `{"code": "...", "type": "...", ...}`
    形式。type 値を `TAILWIND_FLAG_TYPES` / `WARNING_FLAG_TYPES` に照合する。

    なお `highlights.strong_tailwind` / `highlights.critical_risk` 等のリスト
    形式キーは集計対象外（payload 側の集計ルール変更時のブレを防ぐため、件名は
    flags リストを唯一の入力とする）。
    """
    tailwind = 0
    warning = 0
    if isinstance(flags, list):
        for f in flags:
            if not isinstance(f, dict):
                continue
            t = f.get("type")
            if t in TAILWIND_FLAG_TYPES:
                tailwind += 1
            elif t in WARNING_FLAG_TYPES:
                warning += 1
    return tailwind, warning


def _avg_net_score(ratings: List[Dict[str, Any]]) -> Optional[float]:
    """ratings の net_score 単純平均（小数1位）. データ無しなら None."""
    scores = [
        r.get("net_score") for r in ratings
        if isinstance(r, dict) and isinstance(r.get("net_score"), (int, float))
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def _build_subject(payload: Dict[str, Any], today_jst: datetime) -> str:
    """件名生成.

    payload.subject に固定文字列があっても **flags リストから件数を再集計** して
    notifier 側で常に組み立て直す（過去の payload 生成バグで「強0警0」が固定
    出力されたインシデント対応）。

    フォーマット:
        通常        : [M/D ETF Rating] N銘柄 平均X.X点／強い追い風 K銘柄
        警戒あり    : [M/D ETF Rating] N銘柄 平均X.X点／強い追い風 K銘柄／警戒 W銘柄
        強・警ゼロ  : [M/D ETF Rating] N銘柄 平均X.X点
        ratings無し : [M/D ETF Rating] 0銘柄

    40字超過時は短縮（"ETF Rating" → "ETF R" → プレフィックス省略の順）。
    """
    ratings = payload.get("ratings") or []
    flags = payload.get("flags") or []
    md = today_jst.strftime("%-m/%-d")
    count = len(ratings)
    avg = _avg_net_score(ratings)
    tailwind, warning = _count_flag_types(flags)

    if count == 0:
        return _truncate_subject(f"[{md} ETF Rating] 0銘柄")

    avg_part = f"平均{avg}点" if avg is not None else ""
    tail_part = f"強い追い風 {tailwind}銘柄" if tailwind > 0 else ""
    warn_part = f"警戒 {warning}銘柄" if warning > 0 else ""
    flag_parts = "／".join(p for p in (tail_part, warn_part) if p)

    body_parts = [f"{count}銘柄"]
    if avg_part:
        body_parts.append(avg_part)
    body = " ".join(body_parts)
    if flag_parts:
        body = f"{body}／{flag_parts}"

    subject = f"[{md} ETF Rating] {body}"
    if len(subject) <= SUBJECT_MAX_LEN:
        return subject

    # 短縮ステップ1: "ETF Rating" → "ETF R"
    short1 = f"[{md} ETF R] {body}"
    if len(short1) <= SUBJECT_MAX_LEN:
        return short1

    # 短縮ステップ2: 末尾の警戒部を落とす
    if warn_part and tail_part:
        body2 = f"{count}銘柄 {avg_part}／{tail_part}" if avg_part else f"{count}銘柄／{tail_part}"
        short2 = f"[{md} ETF R] {body2}"
        if len(short2) <= SUBJECT_MAX_LEN:
            return short2

    # 短縮ステップ3: フラグ件数省略
    body3 = f"{count}銘柄 {avg_part}" if avg_part else f"{count}銘柄"
    short3 = f"[{md} ETF R] {body3}"
    if len(short3) <= SUBJECT_MAX_LEN:
        return short3

    # それでも超過する場合は末尾を「…」に切り詰める
    return _truncate_subject(subject)


def _enrich_ratings(ratings: List[Dict[str, Any]], today_jst: datetime) -> List[Dict[str, Any]]:
    """各 rating に criteria_age_days を付与（既に存在すれば尊重）."""
    enriched: List[Dict[str, Any]] = []
    today = today_jst.date()
    for r in ratings:
        copy = dict(r)
        if copy.get("criteria_age_days") is None:
            updated = copy.get("criteria_updated_at") or copy.get("criteria_version_date")
            if updated:
                try:
                    dt = datetime.fromisoformat(str(updated)).date()
                    copy["criteria_age_days"] = (today - dt).days
                except ValueError:
                    copy["criteria_age_days"] = None
            else:
                copy["criteria_age_days"] = None
        enriched.append(copy)
    return enriched


def _render(payload: Dict[str, Any], today_jst: datetime) -> Tuple[str, str, str]:
    """payload から (subject, plain, html) を組み立てる.

    payload に既に完成済み `plain_body` / `html_body` がある場合はそれを尊重する。
    無ければ Jinja2 でテンプレートから生成する。
    """
    subject = _build_subject(payload, today_jst)

    plain = payload.get("plain_body")
    html = payload.get("html_body")

    if plain and html:
        return subject, str(plain), str(html)

    env = _build_env()
    ratings = _enrich_ratings(payload.get("ratings") or [], today_jst)
    params = {
        "subject": subject,
        "today_iso": today_jst.strftime("%Y-%m-%d"),
        "sent_at": today_jst.strftime("%H:%M JST"),
        "ratings": ratings,
        "flags": payload.get("flags") or [],
        "market_snapshot": payload.get("market_snapshot"),
        # history_sparklines: v2 で実装予定（履歴3日蓄積後）。
        # 現テンプレ（rating.md.j2 / rating.html.j2）からは未参照のため context から除外。
        "next_tune_date": payload.get("next_tune_date"),
        "summary_text": payload.get("summary_text"),
        "criteria_warnings": payload.get("criteria_warnings") or [],
    }
    if not plain:
        plain = env.get_template("rating.md.j2").render(**params)
    if not html:
        html = env.get_template("rating.html.j2").render(**params)
    return subject, str(plain), str(html)


def _preview(subject: str, plain: str, html: str) -> None:
    """dry-run 時のプレビュー出力."""
    sep = "=" * 60
    print(sep)
    print(f"SUBJECT: {subject}")
    print(sep)
    print("PLAIN BODY:")
    print(plain)
    print(sep)
    html_bytes = len(html.encode("utf-8"))
    print(f"HTML SIZE: {html_bytes:,} bytes")
    # 2段階閾値: WARN（90KB既定）でログ注意のみ / ERROR（100KB既定）で Gmail clip 現実的警告
    if html_bytes > HTML_SIZE_ERROR_BYTES:
        print(
            f"ERROR: HTML exceeds {HTML_SIZE_ERROR_BYTES:,} bytes "
            f"(Gmail will likely clip — consider reducing detail_summary_lines)."
        )
    elif html_bytes > HTML_SIZE_WARN_BYTES:
        print(
            f"WARNING: HTML exceeds {HTML_SIZE_WARN_BYTES:,} bytes "
            f"(approaching Gmail clip threshold {HTML_SIZE_ERROR_BYTES:,})."
        )
    print(sep)


def notify_etf_rating(
    payload_path: Path,
    dry_run: bool = False,
) -> bool:
    """ETF評価結果メールを送信. 成功 True / 失敗 or skip False.

    fail-soft: 内部例外は全て捕捉してログ出力し False を返す。
    """
    enabled = os.environ.get("ETF_RATING_MAIL_ENABLED", "0") == "1"
    effective_dry_run = dry_run or not enabled
    if not enabled and not dry_run:
        logger.info(
            "ETF_RATING_MAIL_ENABLED is not set to '1'; forcing dry-run mode."
        )

    if not payload_path.exists():
        logger.error("payload not found: %s", payload_path)
        return False
    payload = _load_payload(payload_path)
    if payload is None:
        return False

    today_jst = datetime.now(JST)
    try:
        subject, plain, html = _render(payload, today_jst)
    except Exception as exc:  # noqa: BLE001
        logger.error("render failed: %s", exc, exc_info=True)
        return False

    html_bytes = len(html.encode("utf-8"))
    # 2段階閾値: WARN（接近警告） / ERROR（Gmail clip 現実的リスク）
    if html_bytes > HTML_SIZE_ERROR_BYTES:
        logger.error(
            "HTML body exceeds ERROR threshold %d bytes (got %d) — Gmail will likely clip.",
            HTML_SIZE_ERROR_BYTES, html_bytes,
        )
    elif html_bytes > HTML_SIZE_WARN_BYTES:
        logger.warning(
            "HTML body exceeds WARN threshold %d bytes (got %d) — approaching clip limit.",
            HTML_SIZE_WARN_BYTES, html_bytes,
        )

    if effective_dry_run:
        _preview(subject, plain, html)
        logger.info("dry-run: email not sent (subject=%r)", subject)
        return False

    try:
        client = EmailClient()
        return client.send(subject, plain, html)
    except Exception as exc:  # noqa: BLE001
        logger.error("send failed: %s", exc, exc_info=True)
        return False


def _cli() -> int:
    """簡易CLI: `python -m src.services.etf_rating_notifier <payload.json> [--dry-run]`"""
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(
            "Usage: python -m src.services.etf_rating_notifier "
            "<payload.json> [--dry-run]"
        )
        return 0
    payload_path = Path(args[0])
    dry_run = "--dry-run" in args[1:]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ok = notify_etf_rating(payload_path, dry_run=dry_run)
    return 0 if ok or dry_run else 1


if __name__ == "__main__":
    sys.exit(_cli())
