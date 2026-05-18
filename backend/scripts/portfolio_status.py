"""Read-only ポートフォリオ状況スナップショット (my-portfolio スキル F1/F2 用).

PortfolioService（＝分割調整済み）経由で総資産・銘柄別損益・A群/B群配分・
リバランス計画（drift_pp / next_rebalance_date）を取得し JSON で stdout 出力する。

read-only: INSERT/UPDATE/DELETE/commit は一切行わない。SQLite 直接クエリで
trades.quantity / unit_price / 価格時系列を取得して計算に使わない
（CLAUDE.md「株式分割の管理」ルール厳守）。

実行例:
    docker compose exec -T backend python3 scripts/portfolio_status.py
    docker compose exec -T backend python3 scripts/portfolio_status.py --user test
"""
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

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

from src.app import create_app  # noqa: E402
from src.repositories.user_repository import UserRepository  # noqa: E402
from src.services.daily_advisor_service import classify_buckets  # noqa: E402
from src.services.portfolio_rebalance_service import (  # noqa: E402
    PortfolioRebalanceService,
)
from src.services.portfolio_service import PortfolioService  # noqa: E402
from src.services.strategy_loader import StrategyLoader  # noqa: E402


def _resolve_user_id(user_id_str: str):
    """user_id 文字列(=users.user_id列) → users.id (int) を解決.

    AdvisorRunner._resolve_user_id と同じ手段（UserRepository.get_by_user_id）を
    再利用する。DB 直クエリでの重複実装はしない。
    """
    repo = UserRepository()
    user = (
        repo.get_by_user_id(user_id_str)
        if hasattr(repo, "get_by_user_id")
        else None
    )
    return user.id if user else None


def build_status(user_id_str: str) -> dict:
    """ポートフォリオ状況を辞書で構築（read-only）."""
    strategy_file = Path(
        os.environ.get(
            "STRATEGY_FILE",
            str(PROJECT_ROOT / "docs" / "12_personal_strategy.md"),
        )
    )
    strategy = StrategyLoader.load(strategy_file)

    user_id_int = _resolve_user_id(user_id_str)
    if user_id_int is None:
        return {
            "user_id": user_id_str,
            "resolved": False,
            "error": f"user {user_id_str!r} not found",
        }

    ps = PortfolioService()
    summary = ps.get_portfolio_summary(user_id_int)
    holdings = ps.get_holdings(user_id_int)

    # 銘柄別損益（分割調整済み: PortfolioService 出力をそのまま使用）
    holdings_out = [
        {
            "etf_code": h.get("etf_code"),
            "name": (h.get("etf") or {}).get("name"),
            "quantity": h.get("quantity"),
            "average_cost": h.get("average_cost"),
            "current_price": h.get("current_price"),
            "current_value": h.get("current_value"),
            "unrealized_pnl": h.get("unrealized_pnl"),
            "unrealized_pnl_percent": h.get("unrealized_pnl_percent"),
            "holding_days": h.get("holding_days"),
            "holding_period": h.get("holding_period"),
        }
        for h in holdings
    ]

    # A群/B群 実績配分（classify_buckets は構成比[0-1]を返す）
    cash_balance = float(summary.get("cash_balance", 0.0))
    actual_buckets = classify_buckets(
        holdings=holdings,
        cash_balance=cash_balance,
        strategy=strategy,
    )
    bucket_rows = []
    for key in ("group_a", "group_b", "cash"):
        bdef = strategy.target_buckets.get(key)
        actual_pct = round(actual_buckets.get(key, 0.0) * 100.0, 2)
        target_pct = round(bdef.weight_pct, 2) if bdef is not None else None
        drift_pp = (
            round(actual_pct - target_pct, 2)
            if target_pct is not None
            else None
        )
        bucket_rows.append(
            {
                "bucket": key,
                "label_ja": bdef.label_ja if bdef is not None else key,
                "target_pct": target_pct,
                "actual_pct": actual_pct,
                "drift_pp": drift_pp,
            }
        )
    other_pct = round(actual_buckets.get("other", 0.0) * 100.0, 2)
    if other_pct > 0:
        bucket_rows.append(
            {
                "bucket": "other",
                "label_ja": "採用外保有",
                "target_pct": 0.0,
                "actual_pct": other_pct,
                "drift_pp": other_pct,
            }
        )

    # リバランス計画（next_rebalance_date / 銘柄別 drift_pp）
    rebalance = None
    try:
        plan = PortfolioRebalanceService(strategy).calculate_rebalance_plan(
            user_id=user_id_int, as_of_date=date.today()
        )
        rebalance = {
            "is_rebalance_day": bool(plan.is_rebalance_day),
            "next_rebalance_date": (
                plan.next_rebalance_date.isoformat()
                if plan.next_rebalance_date is not None
                else None
            ),
            "days_to_next_rebalance": int(plan.days_to_next_rebalance),
            "sell_actions_count": len(plan.sell_actions),
            "buy_actions_count": len(plan.buy_actions),
            "deviations": {
                code: round(v, 2) for code, v in plan.deviations.items()
            },
        }
    except Exception as e:  # noqa: BLE001
        rebalance = {"error": f"rebalance plan failed: {e}"}

    return {
        "user_id": user_id_str,
        "resolved": True,
        "as_of": date.today().isoformat(),
        "summary": {
            "total_asset": summary.get("total_asset"),
            "total_value": summary.get("total_value"),
            "total_cost": summary.get("total_cost"),
            "cash_balance": summary.get("cash_balance"),
            "total_unrealized_pnl": summary.get("total_unrealized_pnl"),
            "total_unrealized_pnl_percent": summary.get(
                "total_unrealized_pnl_percent"
            ),
            "holdings_count": summary.get("holdings_count"),
        },
        "holdings": holdings_out,
        "bucket_allocation": bucket_rows,
        "rebalance": rebalance,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only portfolio status snapshot (my-portfolio F1/F2)"
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("ADVISOR_USER_ID", "test"),
        help="user_id 文字列（既定: test）",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        status = build_status(args.user)

    print(json.dumps(status, ensure_ascii=False, indent=2, default=str))
    return 0 if status.get("resolved") else 1


if __name__ == "__main__":
    sys.exit(main())
