"""モメンタム売買シミュレーション CLIエントリポイント。

Usage:
    python scripts/simulation/simulate.py 1306
    python scripts/simulation/simulate.py 1306 --variant threshold
    python scripts/simulation/simulate.py 1306 --start-date 2024-01-01
    python scripts/simulation/simulate.py 1306 --variant threshold --buy-threshold 15
"""

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# パス設定（backend/scripts/simulation/ → backend/scripts/ → backend/ → project root）
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent
BACKEND_DIR = SCRIPTS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# simulation パッケージのインポートに必要
sys.path.insert(0, str(SCRIPTS_DIR))
# src パッケージのインポートに必要
sys.path.insert(0, str(BACKEND_DIR))

# 環境変数設定（本番環境用）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

from src.app import create_app  # noqa: E402
from src.models.price_history import PriceHistory  # noqa: E402

from simulation.engine import SimulationEngine  # noqa: E402
from simulation.strategies.momentum import MomentumStrategy  # noqa: E402


def parse_args() -> argparse.Namespace:
    """CLI引数をパースする。"""
    parser = argparse.ArgumentParser(
        description="モメンタム売買シミュレーション",
    )
    parser.add_argument("etf_code", help="ETFコード（例: 1306）")
    parser.add_argument(
        "--strategy", default="momentum", help="戦略名（デフォルト: momentum）",
    )
    parser.add_argument(
        "--variant", default="label", choices=["label", "threshold"],
        help="戦略バリアント（デフォルト: label）",
    )
    parser.add_argument(
        "--capital", type=float, default=1_000_000, help="初期資金（デフォルト: 1000000）",
    )
    parser.add_argument("--start-date", help="開始日 YYYY-MM-DD")
    parser.add_argument("--end-date", help="終了日 YYYY-MM-DD")
    parser.add_argument(
        "--buy-threshold", type=float, default=10.0,
        help="買い閾値（年率%%、thresholdバリアント用、デフォルト: 10）",
    )
    parser.add_argument(
        "--sell-threshold", type=float, default=0.0,
        help="売り閾値（年率%%、thresholdバリアント用、デフォルト: 0）",
    )
    return parser.parse_args()


def load_prices(etf_code: str, start_date: date, end_date: date) -> list:
    """DBから価格データを取得する。

    Returns:
        [{"date": date, "close": float}, ...] 日付昇順
    """
    records = (
        PriceHistory.query
        .filter(PriceHistory.etf_code == etf_code)
        .filter(PriceHistory.date >= start_date)
        .filter(PriceHistory.date <= end_date)
        .filter(PriceHistory.close.isnot(None))
        .order_by(PriceHistory.date.asc())
        .all()
    )
    return [{"date": r.date, "close": float(r.close)} for r in records]


def resolve_dates(args: argparse.Namespace) -> tuple:
    """開始日・終了日を解決する。ウォームアップ用に90日前から取得。"""
    end_date = date.today()
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    if args.start_date:
        sim_start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    else:
        sim_start = end_date - timedelta(days=365)

    # ウォームアップ用に90日前からデータ取得
    data_start = sim_start - timedelta(days=90)
    return data_start, sim_start, end_date


def main() -> int:
    """メイン処理。"""
    args = parse_args()

    app = create_app()
    with app.app_context():
        data_start, sim_start, end_date = resolve_dates(args)
        prices = load_prices(args.etf_code, data_start, end_date)

        if not prices:
            print(f"Error: ETFコード '{args.etf_code}' の価格データが見つかりません。")
            return 1

        if len(prices) < 100:
            print(
                f"Warning: データが {len(prices)} 件しかありません"
                f"（推奨: 100件以上）。結果の信頼性が低い可能性があります。"
            )

        strategy = MomentumStrategy(
            variant=args.variant,
            buy_threshold=args.buy_threshold,
            sell_threshold=args.sell_threshold,
        )
        signals = strategy.generate_signals(prices)

        engine = SimulationEngine(capital=args.capital)
        result = engine.run(signals)

        strategy_label = f"Momentum ({args.variant})"
        if args.variant == "threshold":
            strategy_label += f" buy>{args.buy_threshold}% sell<{args.sell_threshold}%"
        SimulationEngine.print_report(result, strategy_name=strategy_label)

        return 0


if __name__ == "__main__":
    sys.exit(main())
