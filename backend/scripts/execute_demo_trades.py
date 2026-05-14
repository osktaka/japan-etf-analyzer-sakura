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


def _exit_code(succeeded: int, failed: int, skipped: int) -> int:
    """Determine exit code from aggregate results."""
    if failed == 0:
        return 0
    if succeeded > 0 or skipped > 0:
        return 2
    return 1


def _process_trades(
    trades: List[Dict[str, Any]],
    existing_trades: List[Any],
    base_url: str,
    effective_execute: bool,
    today_iso: str,
) -> Tuple[int, int, int]:
    """Iterate the plan and post each trade. Returns (succeeded, failed, skipped)."""
    succeeded = failed = skipped = 0
    for idx, trade in enumerate(trades, 1):
        label = f"[{idx}/{len(trades)}] {trade.get('etf_code')} {trade.get('trade_type')} x{trade.get('quantity')}"
        if is_duplicate(trade, existing_trades):
            logger.info(f"skipped (already posted today): {label}")
            skipped += 1
            continue
        payload = build_payload(trade, today_iso)
        if not effective_execute:
            logger.info(f"sending (dry-run): {label} payload={payload}")
            continue
        logger.info(f"sending: {label}")
        ok, msg = post_trade(base_url, payload)
        if ok:
            logger.info(f"sent: {label} ({msg})")
            succeeded += 1
        else:
            logger.error(f"failed: {label} ({msg})")
            failed += 1
    return succeeded, failed, skipped


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
        succeeded, failed, skipped = _process_trades(
            trades, existing, base_url, effective_execute, today_iso
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

    return _exit_code(succeeded, failed, skipped)


if __name__ == "__main__":
    sys.exit(main())
