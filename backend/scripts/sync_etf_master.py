"""Sync ETF master data from etf_master.json to database."""
import json
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import create_app  # noqa: E402
from src.models import db  # noqa: E402
from src.repositories import CategoryRepository, ETFRepository  # noqa: E402


def ensure_columns():
    """Ensure index_name and manager columns exist in etfs table."""
    conn = db.engine.connect()

    # カラムの存在確認と追加
    try:
        conn.execute(text("SELECT index_name FROM etfs LIMIT 1"))
    except Exception:
        conn.execute(text("ALTER TABLE etfs ADD COLUMN index_name VARCHAR(100)"))
        conn.commit()
        print("  -> Added column: index_name")

    try:
        conn.execute(text("SELECT manager FROM etfs LIMIT 1"))
    except Exception:
        conn.execute(text("ALTER TABLE etfs ADD COLUMN manager VARCHAR(100)"))
        conn.commit()
        print("  -> Added column: manager")

    try:
        conn.execute(text("SELECT type FROM etfs LIMIT 1"))
    except Exception:
        conn.execute(
            text("ALTER TABLE etfs ADD COLUMN type VARCHAR(10) DEFAULT 'ETF' NOT NULL")
        )
        conn.commit()
        print("  -> Added column: type")

    conn.close()


# カテゴリ推定ルール
CATEGORY_RULES = [
    (["TOPIX", "日経", "東証", "JPX"], "国内株式"),
    (
        ["S&P", "NASDAQ", "ダウ", "MSCI", "米国", "新興国", "先進国", "全世界"],
        "外国株式",
    ),
    (["REIT", "リート", "不動産"], "REIT"),
    (["債券", "国債"], "国内債券"),
    (["米国債", "外国債", "ハイイールド"], "外国債券"),
    (["金", "原油", "銀", "プラチナ", "商品", "コモディティ"], "コモディティ"),
    (["レバレッジ", "ブル", "2倍"], "レバレッジ"),
    (["インバース", "ベア", "ダブルインバース"], "インバース"),
]


def estimate_category(index_name: str, etf_name: str) -> str:
    """Estimate category from index name and ETF name."""
    search_text = f"{index_name} {etf_name}"

    # レバレッジ・インバースを優先判定
    for keywords, category in CATEGORY_RULES:
        if category in ("レバレッジ", "インバース"):
            for keyword in keywords:
                if keyword in search_text:
                    return category

    # その他のカテゴリを判定
    for keywords, category in CATEGORY_RULES:
        if category not in ("レバレッジ", "インバース"):
            for keyword in keywords:
                if keyword in search_text:
                    return category

    return "国内株式"  # デフォルト


def sync_etf_master():
    """Sync ETF master data to database."""
    data_path = Path(__file__).parent.parent / "src" / "data" / "etf_master.json"

    if not data_path.exists():
        print(f"Error: {data_path} not found")
        return 0, 0

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    etfs = data.get("etfs", [])
    print(f"Found {len(etfs)} ETFs in master data")

    etf_repo = ETFRepository()
    category_repo = CategoryRepository()

    # カテゴリ名 -> ID のマッピングを作成
    categories = category_repo.get_all_sorted()
    category_map = {c.name: c.id for c in categories}
    print(f"Categories: {list(category_map.keys())}")

    created = 0
    updated = 0

    for etf_data in etfs:
        code = etf_data.get("code")
        name = etf_data.get("name", "")
        index_name = etf_data.get("index", "")
        manager = etf_data.get("manager", "")
        expense_ratio = etf_data.get("expense_ratio")
        etf_type = etf_data.get("type", "ETF")  # デフォルトは'ETF'

        # カテゴリを推定
        category_name = estimate_category(index_name, name)
        category_id = category_map.get(category_name)

        # 既存データをチェック
        existing = etf_repo.get_by_code(code)

        # データを作成または更新
        data_to_save = {
            "code": code,
            "name": name,
            "index_name": index_name,
            "manager": manager,
            "category_id": category_id,
            "type": etf_type,
        }

        # 信託報酬がある場合は追加
        if expense_ratio is not None:
            data_to_save["expense_ratio"] = expense_ratio

        etf_repo.create_or_update(data_to_save)

        if existing:
            updated += 1
        else:
            created += 1

    return created, updated


def main():
    """Run sync script."""
    from datetime import datetime

    from src.repositories import BatchLogRepository

    app = create_app()
    with app.app_context():
        # バッチログ記録開始
        batch_log_repo = BatchLogRepository()
        batch_log = batch_log_repo.create(
            batch_name="sync_etf_master",
            status="running",
            started_at=datetime.utcnow(),
        )
        print(f"Batch log created: id={batch_log.id}")

        try:
            print("Ensuring database columns...")
            ensure_columns()

            print("Syncing ETF master data...")
            created, updated = sync_etf_master()
            print(f"  -> Created: {created}, Updated: {updated}")
            print("Sync complete!")

            # バッチログを成功で更新
            batch_log_repo.update(
                batch_log.id,
                status="success",
                finished_at=datetime.utcnow(),
            )
            print(f"Batch log updated: id={batch_log.id}, status=success")

        except Exception as e:
            # バッチログを失敗で更新
            batch_log_repo.update(
                batch_log.id,
                status="failed",
                finished_at=datetime.utcnow(),
                error_message=str(e),
            )
            print(f"Batch log updated: id={batch_log.id}, status=failed")
            raise


if __name__ == "__main__":
    main()
