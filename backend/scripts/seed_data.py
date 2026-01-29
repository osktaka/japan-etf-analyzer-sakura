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

TAGS = [
    {"name": "高配当", "color": "#10B981"},
    {"name": "低コスト", "color": "#3B82F6"},
    {"name": "人気", "color": "#F59E0B"},
    {"name": "安定運用", "color": "#6366F1"},
    {"name": "成長", "color": "#EC4899"},
    {"name": "分散投資", "color": "#8B5CF6"},
    {"name": "初心者向け", "color": "#14B8A6"},
    {"name": "大型", "color": "#EF4444"},
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
