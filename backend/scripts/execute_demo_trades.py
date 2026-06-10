"""Post planned demo trades to the API (cron-driven).

Reads ``reports/{user}/trades_execution_plan.json`` produced by the
portfolio-analysis-v2 skill and POSTs each trade to
``/api/v1/demo/trades``. Idempotent via a daily marker file and a DB
duplicate check.
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# プロジェクトルートを特定（backend/scripts/ → backend/ → project root）
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 環境変数設定（本番環境用）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

import requests  # noqa: E402

from src.app import create_app  # noqa: E402
from src.repositories.batch_log_repository import BatchLogRepository  # noqa: E402
from src.repositories.trade_repository import TradeRepository  # noqa: E402
from src.repositories.user_repository import UserRepository  # noqa: E402

BATCH_NAME = "demo_trade_post"
BASE_URLS = {
    "dev": "http://localhost:8902",
    "prod": "https://kima3.net/japan-etf-analyzer",
}
JST = timezone(timedelta(hours=9))
MEMO_PREFIX = "[auto]"

# 参考終値との許容乖離（PROMPT.md セクション10.5 の 5% ルール）
PRICE_DEVIATION_LIMIT = 0.05

logger = logging.getLogger("execute_demo_trades")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments (dry-run/execute is mutually exclusive)."""
    parser = argparse.ArgumentParser(
        description="Post planned demo trades to the demo API."
    )
    parser.add_argument("--user", required=True, help='User ID (e.g., "demo")')
    parser.add_argument(
        "--env", choices=["dev", "prod"], default="dev", help="POST target environment"
    )
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="Required when --env prod --execute",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Log only, no POST")
    mode.add_argument("--execute", action="store_true", help="Actually POST")
    return parser.parse_args()


def setup_logging() -> None:
    """Configure logger to write to file and stdout."""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "execute_demo_trades.log"
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)


def check_marker(marker_path: Path) -> bool:
    """Return True if today's marker file already exists."""
    return marker_path.exists()


def load_plan(path: Path) -> Optional[List[Dict[str, Any]]]:
    """Load trades_execution_plan.json. Returns None if file is missing."""
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    trades = data.get("trades", [])
    if not isinstance(trades, list):
        return []
    return trades


def is_duplicate(trade: Dict[str, Any], existing_trades: List[Any]) -> bool:
    """Check if today's DB already contains an equivalent posted trade.

    plan_id 一致は `build_payload` が memo に書き込む `[plan_id=<id>]` タグの
    完全一致で判定する（部分一致による prefix 衝突を避けるため）。
    """
    plan_id = trade.get("plan_id")
    etf_code = trade.get("etf_code")
    trade_type = trade.get("trade_type")
    plan_tag = f"[plan_id={plan_id}]" if plan_id else None
    for ex in existing_trades:
        if ex.etf_code != etf_code or ex.trade_type != trade_type:
            continue
        memo = ex.memo or ""
        if plan_tag:
            if plan_tag in memo:
                return True
        else:
            if memo.startswith(MEMO_PREFIX):
                return True
    return False


def build_payload(trade: Dict[str, Any], today_iso: str) -> Dict[str, Any]:
    """Build POST body, ensuring memo carries auto-marker / plan_id."""
    memo = trade.get("memo") or ""
    plan_id = trade.get("plan_id")
    tag = MEMO_PREFIX if not plan_id else f"{MEMO_PREFIX}[plan_id={plan_id}]"
    if tag not in memo:
        memo = f"{tag} {memo}".strip()
    return {
        "etf_code": trade["etf_code"],
        "trade_type": trade["trade_type"],
        "quantity": trade["quantity"],
        "price": trade["price"],
        "trade_date": trade.get("trade_date", today_iso),
        "memo": memo,
    }


def post_trade(
    base_url: str, payload: Dict[str, Any], timeout: int = 15
) -> Tuple[bool, str]:
    """POST a single trade. Returns (success, message)."""
    url = base_url.rstrip("/") + "/api/v1/demo/trades"
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        return False, f"connection error: {exc}"
    if 200 <= resp.status_code < 300:
        return True, f"HTTP {resp.status_code}"
    return False, f"HTTP {resp.status_code}: {resp.text[:200]}"


def fetch_portfolio_state(base_url: str, timeout: int = 15) -> Dict[str, Any]:
    """Fetch demo cash balance and split-adjusted holdings via demo GET APIs.

    保有数量・現金は PortfolioService 経由の demo GET エンドポイント
    （分割調整済み）から取得する。DB 生 trades は参照しない。

    Returns
    -------
    dict
        ``{"cash_balance": float, "holdings": {etf_code: quantity}}``。
        取得失敗時は ``{}`` を返し、呼び出し側で検証スキップ判断に使う。
    """
    base = base_url.rstrip("/")
    try:
        pf = requests.get(base + "/api/v1/demo/portfolio", timeout=timeout)
        hd = requests.get(
            base + "/api/v1/demo/portfolio/holdings", timeout=timeout
        )
    except requests.RequestException as exc:
        logger.warning(f"portfolio state fetch failed (skip pre-checks): {exc}")
        return {}
    if pf.status_code != 200 or hd.status_code != 200:
        logger.warning(
            f"portfolio state fetch HTTP error (skip pre-checks): "
            f"portfolio={pf.status_code} holdings={hd.status_code}"
        )
        return {}
    cash = (pf.json().get("data") or {}).get("cash_balance", 0)
    holdings = {
        h["etf_code"]: h.get("quantity", 0)
        for h in (hd.json().get("data") or [])
    }
    return {"cash_balance": cash, "holdings": holdings}


def fetch_reference_price(
    base_url: str, etf_code: str, timeout: int = 15
) -> Optional[float]:
    """Fetch an ETF's latest close (market_price) via the ETF detail API.

    market_price は分割中立の直近終値であり、価格乖離・分割整合チェックの
    基準値として用いる。取得失敗時は None（当該チェックをスキップ）。
    """
    url = base_url.rstrip("/") + f"/api/v1/etfs/{etf_code}"
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    price = (resp.json().get("data") or {}).get("market_price")
    return float(price) if price else None


def validate_trade(
    trade: Dict[str, Any],
    state: Dict[str, Any],
    reference_price: Optional[float],
) -> Optional[str]:
    """Pre-POST validation gate. Returns a reason string when the trade is invalid.

    検証項目（いずれも API/サービス層由来のデータで判定）:
    - 買い: 必要額が利用可能現金以内か
    - 売り: 数量が分割調整後の保有数量以内か
    - 価格乖離: price が直近終値の ±5% 以内か
    - 分割整合: price が終値の概ね分割比（またはその逆数）ぶんズレていないか
    """
    trade_type = trade.get("trade_type")
    etf_code = trade.get("etf_code")
    quantity = trade.get("quantity") or 0
    price = trade.get("price") or 0

    if trade_type == "buy":
        required = quantity * price
        cash = state.get("cash_balance", 0)
        if required > cash:
            return f"現金不足: 必要額{required:,.0f}円 > 残高{cash:,.0f}円"
    elif trade_type == "sell":
        held = state.get("holdings", {}).get(etf_code, 0)
        if quantity > held:
            return f"保有超過売却: 売却{quantity} > 保有{held:g}"

    if reference_price and price > 0:
        deviation = abs(price - reference_price) / reference_price
        if deviation > PRICE_DEVIATION_LIMIT:
            return (
                f"価格乖離{deviation * 100:.1f}%: plan価格{price:,.0f}円 "
                f"vs 終値{reference_price:,.0f}円"
            )

    return None


def _exit_code(succeeded: int, failed: int, skipped: int) -> int:
    """Determine exit code from aggregate results."""
    if failed == 0:
        return 0
    if succeeded > 0 or skipped > 0:
        return 2
    return 1


def _build_result(
    trade: Dict[str, Any],
    payload: Dict[str, Any],
    status: str,
    http_status: Optional[int] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a single trade_results dict (notifier-compatible shape)."""
    return {
        "etf_code": trade.get("etf_code"),
        "trade_type": trade.get("trade_type"),
        "quantity": trade.get("quantity"),
        "price": trade.get("price"),
        "memo": payload.get("memo", trade.get("memo") or ""),
        "status": status,
        "http_status": http_status,
        "error_message": error_message,
    }


def _parse_http_status(msg: str) -> Optional[int]:
    """Extract integer HTTP status from post_trade message. None if not parseable."""
    # Messages look like "HTTP 201" or "HTTP 500: boom" or "connection error: ..."
    if not msg.startswith("HTTP "):
        return None
    try:
        rest = msg[len("HTTP "):]
        head = rest.split(":", 1)[0].strip()
        return int(head)
    except (ValueError, IndexError):
        return None


def _process_trades(
    trades: List[Dict[str, Any]],
    existing_trades: List[Any],
    base_url: str,
    effective_execute: bool,
    today_iso: str,
    portfolio_state: Optional[Dict[str, Any]] = None,
) -> Tuple[int, int, int, List[Dict[str, Any]]]:
    """Iterate the plan and post each trade.

    Returns (succeeded, failed, skipped, results).
    ``results`` は notifier に渡せる形式の dict のリスト。
    検証違反は POST せず failed として計上し、サーバ側 400 と exit code を揃える。
    """
    state = portfolio_state or {}
    succeeded = failed = skipped = 0
    results: List[Dict[str, Any]] = []
    for idx, trade in enumerate(trades, 1):
        label = f"[{idx}/{len(trades)}] {trade.get('etf_code')} {trade.get('trade_type')} x{trade.get('quantity')}"
        if is_duplicate(trade, existing_trades):
            logger.info(f"skipped (already posted today): {label}")
            skipped += 1
            results.append(
                _build_result(
                    trade,
                    {"memo": trade.get("memo") or ""},
                    status="skipped",
                    error_message="duplicate",
                )
            )
            continue
        if state:
            reference_price = fetch_reference_price(base_url, trade.get("etf_code"))
            reason = validate_trade(trade, state, reference_price)
            if reason:
                logger.error(f"rejected (pre-check): {label} ({reason})")
                failed += 1
                results.append(
                    _build_result(
                        trade,
                        {"memo": trade.get("memo") or ""},
                        status="failed",
                        error_message=f"pre-check: {reason}",
                    )
                )
                continue
        payload = build_payload(trade, today_iso)
        if not effective_execute:
            logger.info(f"sending (dry-run): {label} payload={payload}")
            results.append(_build_result(trade, payload, status="dry_run"))
            continue
        logger.info(f"sending: {label}")
        ok, msg = post_trade(base_url, payload)
        http_status = _parse_http_status(msg)
        if ok:
            logger.info(f"sent: {label} ({msg})")
            succeeded += 1
            results.append(
                _build_result(trade, payload, status="success", http_status=http_status)
            )
        else:
            logger.error(f"failed: {label} ({msg})")
            failed += 1
            results.append(
                _build_result(
                    trade,
                    payload,
                    status="failed",
                    http_status=http_status,
                    error_message=msg,
                )
            )
    return succeeded, failed, skipped, results


def main() -> int:
    """Entry point."""
    setup_logging()
    args = parse_args()

    if args.env == "prod" and args.execute and not args.confirm_production:
        logger.error("production POST requires --confirm-production")
        return 1

    env_flag = os.environ.get("DEMO_TRADE_POST_ENABLED", "")
    effective_execute = bool(args.execute)
    if effective_execute and env_flag != "1":
        logger.warning(
            "DEMO_TRADE_POST_ENABLED != '1'; falling back to dry-run mode"
        )
        effective_execute = False

    today_jst = datetime.now(JST).date()
    today_iso = today_jst.isoformat()
    user_dir = PROJECT_ROOT / "reports" / args.user
    marker_path = user_dir / f".trades_posted_{today_jst.strftime('%Y%m%d')}"
    plan_path = user_dir / "trades_execution_plan.json"

    if check_marker(marker_path):
        logger.info(f"already posted today (marker={marker_path.name})")
        return 0

    trades = load_plan(plan_path)
    if trades is None:
        logger.info(f"plan not found: {plan_path}")
        return 0
    if not trades:
        logger.info("no trades to execute")
        return 0

    app = create_app()
    with app.app_context():
        user_repo = UserRepository()
        user = user_repo.get_by_user_id(args.user)
        if not user:
            logger.error(f"user not found: user_id={args.user}")
            return 1

        trade_repo = TradeRepository()
        batch_repo = BatchLogRepository()
        existing = trade_repo.get_by_date_range(user.id, today_jst, today_jst)

        batch_log = batch_repo.create(
            batch_name=BATCH_NAME,
            status="running",
            started_at=datetime.utcnow(),
            total_count=len(trades),
        )
        logger.info(
            f"start: user={args.user} env={args.env} execute={effective_execute} "
            f"trades={len(trades)} batch_log_id={batch_log.id}"
        )

        base_url = BASE_URLS[args.env]
        portfolio_state = fetch_portfolio_state(base_url)
        succeeded, failed, skipped, results = _process_trades(
            trades, existing, base_url, effective_execute, today_iso, portfolio_state
        )

        logger.info(
            f"summary: succeeded={succeeded} failed={failed} skipped={skipped}"
        )

        status = "success" if failed == 0 else (
            "success" if succeeded + skipped > 0 else "failed"
        )
        err_msg = None if failed == 0 else f"{failed} POST(s) failed"
        batch_repo.update(
            batch_log.id,
            status=status,
            finished_at=datetime.utcnow(),
            error_message=err_msg,
        )

        if effective_execute and (succeeded > 0 or (failed == 0 and skipped > 0)):
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_text(today_iso, encoding="utf-8")
            logger.info(f"marker created: {marker_path}")

        # ポートフォリオ変更レポートメール（通知失敗は exit code に影響させない）
        try:
            from src.services import demo_portfolio_notifier  # local import

            sent = demo_portfolio_notifier.notify(
                trade_results=results,
                today_jst=today_jst,
                dry_run=(not effective_execute),
                batch_log_id=batch_log.id,
                base_url=base_url,
            )
            if sent:
                logger.info("portfolio report email sent")
            else:
                logger.info(
                    "portfolio report email not sent "
                    "(trigger condition / SMTP failed / disabled)"
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"portfolio report notification error (continuing): {exc}"
            )

    return _exit_code(succeeded, failed, skipped)


if __name__ == "__main__":
    sys.exit(main())
