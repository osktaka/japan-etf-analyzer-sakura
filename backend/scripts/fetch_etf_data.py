"""Seed ETF data with static values (for MVP)."""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import create_app
from src.models import db
from src.repositories import CategoryRepository, ETFRepository, TagRepository

ETF_LIST = [
    {
        "code": "1306",
        "name": "TOPIX連動型上場投資信託",
        "category": "国内株式",
        "tags": ["低コスト", "人気", "初心者向け", "大型"],
        "description": "TOPIXに連動する国内株式ETF。日本を代表する国内株式インデックス。",
        "expense_ratio": "0.066",
        "dividend_yield": "2.10",
        "market_price": "2505",
        "nav": "2500",
        "total_assets": "15000000000000",
    },
    {
        "code": "1321",
        "name": "日経225連動型上場投資信託",
        "category": "国内株式",
        "tags": ["人気", "初心者向け", "大型"],
        "description": "日経平均株価に連動するETF。日本を代表する株価指数。",
        "expense_ratio": "0.198",
        "dividend_yield": "1.80",
        "market_price": "30500",
        "nav": "30450",
        "total_assets": "8000000000000",
    },
    {
        "code": "1343",
        "name": "NEXT FUNDS 東証REIT指数連動型上場投信",
        "category": "REIT",
        "tags": ["高配当", "分散投資"],
        "description": "東証REIT指数に連動するETF。不動産投資信託に分散投資。",
        "expense_ratio": "0.155",
        "dividend_yield": "4.20",
        "market_price": "1850",
        "nav": "1845",
        "total_assets": "450000000000",
    },
    {
        "code": "1550",
        "name": "MAXIS 海外株式（MSCIコクサイ）上場投信",
        "category": "外国株式",
        "tags": ["分散投資", "低コスト"],
        "description": "先進国株式に投資するETF。日本を除く先進国に分散投資。",
        "expense_ratio": "0.088",
        "dividend_yield": "1.50",
        "market_price": "4200",
        "nav": "4195",
        "total_assets": "120000000000",
    },
    {
        "code": "2558",
        "name": "MAXIS 米国株式（S&P500）上場投信",
        "category": "外国株式",
        "tags": ["人気", "成長", "低コスト"],
        "description": "S&P500指数に連動するETF。米国大型株に投資。",
        "expense_ratio": "0.077",
        "dividend_yield": "1.30",
        "market_price": "18500",
        "nav": "18490",
        "total_assets": "800000000000",
    },
    {
        "code": "1476",
        "name": "iシェアーズ・コア Jリート ETF",
        "category": "REIT",
        "tags": ["高配当", "安定運用"],
        "description": "東証REIT指数に連動するETF。低コストでJリートに投資。",
        "expense_ratio": "0.165",
        "dividend_yield": "4.10",
        "market_price": "1950",
        "nav": "1945",
        "total_assets": "350000000000",
    },
    {
        "code": "1489",
        "name": "NEXT FUNDS 日経平均高配当株50指数連動型上場投信",
        "category": "国内株式",
        "tags": ["高配当", "人気"],
        "description": "日経平均構成銘柄の中から配当利回りの高い50銘柄に投資。",
        "expense_ratio": "0.308",
        "dividend_yield": "4.50",
        "market_price": "52000",
        "nav": "51900",
        "total_assets": "500000000000",
    },
    {
        "code": "2559",
        "name": "MAXIS 全世界株式（オール・カントリー）上場投信",
        "category": "外国株式",
        "tags": ["分散投資", "初心者向け", "低コスト"],
        "description": "全世界の株式に分散投資するETF。新興国含む。",
        "expense_ratio": "0.078",
        "dividend_yield": "1.60",
        "market_price": "17800",
        "nav": "17790",
        "total_assets": "600000000000",
    },
]


def seed_etf_data():
    """Seed ETF data from predefined list."""
    cat_repo = CategoryRepository()
    tag_repo = TagRepository()
    etf_repo = ETFRepository()

    for etf_info in ETF_LIST:
        code = etf_info["code"]
        print(f"Processing ETF: {code} - {etf_info['name']}")

        category = cat_repo.get_by_name(etf_info["category"])
        if not category:
            print(f"  Warning: Category '{etf_info['category']}' not found")
            continue

        etf_data = {
            "code": code,
            "name": etf_info["name"],
            "description": etf_info["description"],
            "category_id": category.id,
            "expense_ratio": Decimal(etf_info["expense_ratio"]),
            "dividend_yield": Decimal(etf_info["dividend_yield"]),
            "market_price": Decimal(etf_info["market_price"]),
            "nav": Decimal(etf_info["nav"]),
            "total_assets": Decimal(etf_info["total_assets"]),
        }

        etf = etf_repo.create_or_update(etf_data)
        print(f"  -> ETF saved: {etf.code}")

        for tag_name in etf_info.get("tags", []):
            tag = tag_repo.get_by_name(tag_name)
            if tag:
                etf_repo.add_tag(etf.code, tag.id)
                print(f"  -> Tag added: {tag_name}")


def main():
    """Run ETF data fetch script."""
    app = create_app()
    with app.app_context():
        print("Fetching and seeding ETF data...")
        seed_etf_data()
        print("ETF data seeding complete!")


if __name__ == "__main__":
    main()
