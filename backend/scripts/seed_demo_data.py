"""Seed demo user data for unauthenticated preview."""
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
from src.models import CashFlow, Favorite, Trade, User, db  # noqa: E402

DEMO_USER_ID = "demo"
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "D3m0$ecur3!Passw0rd#2026"

# サンプル取引データ（実在のETF銘柄コード）
DEMO_TRADES = [
    {
        "etf_code": "1306",
        "trade_type": "buy",
        "quantity": 10,
        "price": 2450.0,
        "trade_date": date(2025, 4, 10),
        "memo": "TOPIX連動ETF 初回購入",
    },
    {
        "etf_code": "1306",
        "trade_type": "buy",
        "quantity": 5,
        "price": 2380.0,
        "trade_date": date(2025, 7, 15),
        "memo": "TOPIX連動ETF 追加購入",
    },
    {
        "etf_code": "1321",
        "trade_type": "buy",
        "quantity": 3,
        "price": 40500.0,
        "trade_date": date(2025, 5, 20),
        "memo": "日経225連動ETF",
    },
    {
        "etf_code": "1475",
        "trade_type": "buy",
        "quantity": 20,
        "price": 2650.0,
        "trade_date": date(2025, 6, 1),
        "memo": "iシェアーズ TOPIX",
    },
    {
        "etf_code": "1329",
        "trade_type": "buy",
        "quantity": 5,
        "price": 39800.0,
        "trade_date": date(2025, 8, 12),
        "memo": "iシェアーズ 日経225",
    },
    {
        "etf_code": "1348",
        "trade_type": "buy",
        "quantity": 15,
        "price": 2520.0,
        "trade_date": date(2025, 9, 3),
        "memo": "MAXIS トピックス",
    },
    {
        "etf_code": "1321",
        "trade_type": "sell",
        "quantity": 1,
        "price": 41200.0,
        "trade_date": date(2025, 10, 22),
        "memo": "日経225連動ETF 一部利確",
    },
    # 完全売却銘柄（過去保有銘柄表示テスト用）
    {
        "etf_code": "2558",
        "trade_type": "buy",
        "quantity": 30,
        "price": 2180.0,
        "trade_date": date(2025, 5, 8),
        "memo": "MAXIS 米国株式 S&P500 購入",
    },
    {
        "etf_code": "2558",
        "trade_type": "sell",
        "quantity": 30,
        "price": 2350.0,
        "trade_date": date(2025, 9, 18),
        "memo": "MAXIS 米国株式 S&P500 全量売却（利確）",
    },
]

# サンプルお気に入りデータ
DEMO_FAVORITES = ["1306", "1321", "1475", "1348"]

# サンプル入出金データ
DEMO_CASH_FLOWS = [
    {
        "flow_type": "deposit",
        "amount": 500000,
        "flow_date": date(2025, 4, 1),
        "memo": "初回入金",
    },
    {
        "flow_type": "deposit",
        "amount": 200000,
        "flow_date": date(2025, 7, 1),
        "memo": "追加入金",
    },
    {
        "flow_type": "withdrawal",
        "amount": 50000,
        "flow_date": date(2025, 11, 15),
        "memo": "一部出金",
    },
]


def seed_demo_user():
    """Create or recreate demo user with sample data (idempotent)."""
    # 既存のデモユーザーを削除（cascade で関連データも削除）
    existing = User.query.filter_by(user_id=DEMO_USER_ID).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        print("  -> Existing demo user deleted (cascade)")

    # デモユーザー作成
    user = User(
        user_id=DEMO_USER_ID,
        username=DEMO_USERNAME,
        is_admin=False,
        is_active=True,
    )
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    db.session.flush()  # Get user.id

    # 取引データ投入
    for trade_data in DEMO_TRADES:
        trade = Trade(user_id=user.id, **trade_data)
        db.session.add(trade)
    print(f"  -> {len(DEMO_TRADES)} trades created")

    # お気に入りデータ投入
    for etf_code in DEMO_FAVORITES:
        favorite = Favorite(user_id=user.id, etf_code=etf_code)
        db.session.add(favorite)
    print(f"  -> {len(DEMO_FAVORITES)} favorites created")

    # 入出金データ投入
    for cf_data in DEMO_CASH_FLOWS:
        cash_flow = CashFlow(user_id=user.id, **cf_data)
        db.session.add(cash_flow)
    print(f"  -> {len(DEMO_CASH_FLOWS)} cash flows created")

    db.session.commit()
    print(f"  -> Demo user created (PK={user.id})")


def main():
    """Run demo data seed script."""
    app = create_app()
    with app.app_context():
        print("Seeding demo user data...")
        seed_demo_user()
        print("Demo data seed complete!")


if __name__ == "__main__":
    main()
