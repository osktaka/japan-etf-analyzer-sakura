"""Seed initial data for categories and tags."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import create_app  # noqa: E402
from src.repositories import CategoryRepository, TagRepository  # noqa: E402

CATEGORIES = [
    {"name": "国内株式", "description": "日本国内の株式市場に連動するETF", "sort_order": 1},
    {"name": "外国株式", "description": "海外の株式市場に連動するETF", "sort_order": 2},
    {"name": "国内債券", "description": "日本国内の債券に連動するETF", "sort_order": 3},
    {"name": "外国債券", "description": "海外の債券に連動するETF", "sort_order": 4},
    {"name": "REIT", "description": "不動産投資信託に連動するETF", "sort_order": 5},
    {"name": "コモディティ", "description": "金や原油などの商品に連動するETF", "sort_order": 6},
    {"name": "レバレッジ", "description": "指数の値動きの2倍等に連動するETF", "sort_order": 7},
    {"name": "インバース", "description": "指数の値動きの逆に連動するETF", "sort_order": 8},
]

# 6カテゴリ・41タグ
TAGS = [
    # 業種(sector) - 9個 - 青系
    {"name": "金融", "color": "#3B82F6", "category": "sector"},
    {"name": "テクノロジー", "color": "#2563EB", "category": "sector"},
    {"name": "ヘルスケア", "color": "#1D4ED8", "category": "sector"},
    {"name": "エネルギー", "color": "#1E40AF", "category": "sector"},
    {"name": "素材", "color": "#1E3A8A", "category": "sector"},
    {"name": "消費", "color": "#60A5FA", "category": "sector"},
    {"name": "機械・製造", "color": "#93C5FD", "category": "sector"},
    {"name": "通信", "color": "#BFDBFE", "category": "sector"},
    {"name": "公益", "color": "#DBEAFE", "category": "sector"},
    # テーマ(theme) - 10個 - 緑系
    {"name": "AI・半導体", "color": "#10B981", "category": "theme"},
    {"name": "EV・自動運転", "color": "#059669", "category": "theme"},
    {"name": "クリーンエネルギー", "color": "#047857", "category": "theme"},
    {"name": "DX", "color": "#065F46", "category": "theme"},
    {"name": "高配当", "color": "#064E3B", "category": "theme"},
    {"name": "ESG", "color": "#34D399", "category": "theme"},
    {"name": "小型株", "color": "#6EE7B7", "category": "theme"},
    {"name": "バリュー", "color": "#A7F3D0", "category": "theme"},
    {"name": "グロース", "color": "#D1FAE5", "category": "theme"},
    {"name": "インデックス", "color": "#ECFDF5", "category": "theme"},
    # 地域(region) - 8個 - 紫系
    {"name": "国内", "color": "#8B5CF6", "category": "region"},
    {"name": "米国", "color": "#7C3AED", "category": "region"},
    {"name": "先進国", "color": "#6D28D9", "category": "region"},
    {"name": "新興国", "color": "#5B21B6", "category": "region"},
    {"name": "全世界", "color": "#4C1D95", "category": "region"},
    {"name": "アジア", "color": "#A78BFA", "category": "region"},
    {"name": "ヨーロッパ", "color": "#C4B5FD", "category": "region"},
    {"name": "中国", "color": "#DDD6FE", "category": "region"},
    # 資産クラス(asset) - 4個 - オレンジ系
    {"name": "株式", "color": "#F59E0B", "category": "asset"},
    {"name": "債券", "color": "#D97706", "category": "asset"},
    {"name": "REIT", "color": "#B45309", "category": "asset"},
    {"name": "コモディティ", "color": "#92400E", "category": "asset"},
    # 経済情勢(economic) - 7個 - 赤系
    {"name": "円安", "color": "#EF4444", "category": "economic"},
    {"name": "円高", "color": "#DC2626", "category": "economic"},
    {"name": "金利上昇", "color": "#B91C1C", "category": "economic"},
    {"name": "金利低下", "color": "#991B1B", "category": "economic"},
    {"name": "インフレヘッジ", "color": "#7F1D1D", "category": "economic"},
    {"name": "景気敏感", "color": "#F87171", "category": "economic"},
    {"name": "ディフェンシブ", "color": "#FCA5A5", "category": "economic"},
    # 政策(policy) - 3個 - ピンク系
    {"name": "防衛関連", "color": "#EC4899", "category": "policy"},
    {"name": "インフラ", "color": "#DB2777", "category": "policy"},
    {"name": "半導体政策", "color": "#BE185D", "category": "policy"},
]


def seed_categories():
    """Seed category data."""
    repo = CategoryRepository()
    created = 0
    for cat_data in CATEGORIES:
        category = repo.create_if_not_exists(
            name=cat_data["name"],
            description=cat_data["description"],
            sort_order=cat_data["sort_order"],
        )
        if category:
            created += 1
    return created


def seed_tags():
    """Seed tag data."""
    repo = TagRepository()
    created = 0
    for tag_data in TAGS:
        tag = repo.create_if_not_exists(
            name=tag_data["name"],
            color=tag_data["color"],
            category=tag_data.get("category"),
        )
        if tag:
            created += 1
    return created


def main():
    """Run seed data script."""
    app = create_app()
    with app.app_context():
        print("Seeding categories...")
        cat_count = seed_categories()
        print(f"  -> {cat_count} categories processed")

        print("Seeding tags...")
        tag_count = seed_tags()
        print(f"  -> {tag_count} tags processed")

        print("Seed data complete!")


if __name__ == "__main__":
    main()
