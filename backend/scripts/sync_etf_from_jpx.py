#!/usr/bin/env python3
"""Sync ETF master data directly from JPX website to database.

This script fetches ETF/ETN lists from JPX, estimates categories,
and syncs directly to the database without using etf_master.json.

Usage:
    python scripts/sync_etf_from_jpx.py
"""
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

# Load .env file if it exists
project_root = Path(__file__).resolve().parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import create_app  # noqa: E402
from src.models import db  # noqa: E402
from src.repositories import BatchLogRepository, CategoryRepository, ETFRepository  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# JPX ETF/ETN URLs
JPX_ETF_URL = "https://www.jpx.co.jp/equities/products/etfs/issues/01.html"
JPX_ETN_URL = "https://www.jpx.co.jp/equities/products/etns/issues/01.html"
JPX_LEVERAGED_URL = "https://www.jpx.co.jp/equities/products/etfs/leveraged-inverse/01.html"

# Category estimation rules
CATEGORY_RULES = [
    (["TOPIX", "日経", "東証", "JPX"], "国内株式"),
    (["S&P", "NASDAQ", "ダウ", "MSCI", "米国", "新興国", "先進国", "全世界"], "外国株式"),
    (["REIT", "リート", "不動産"], "REIT"),
    (["債券", "国債"], "国内債券"),
    (["米国債", "外国債", "ハイイールド"], "外国債券"),
    (["金", "原油", "銀", "プラチナ", "商品", "コモディティ"], "コモディティ"),
    (["レバレッジ", "ブル", "2倍"], "レバレッジ"),
    (["インバース", "ベア", "ダブルインバース"], "インバース"),
]


def parse_expense_ratio(text: str) -> Optional[float]:
    """Parse expense ratio from text (e.g., '0.12%' -> 0.12)."""
    if not text:
        return None
    text = text.strip()
    match = re.search(r"([\d.]+)\s*%?", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def fetch_jpx_etf_page(url: str) -> list:
    """Fetch ETF list from JPX website by scraping HTML table.

    ETF table columns: [連動対象指標, コード, 名称, 管理会社, 信託報酬]
    """
    logger.info(f"Fetching ETF list from {url}")

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    items = []

    table = soup.find("table")
    if not table:
        raise ValueError("ETF table not found on page")

    rows = table.find_all("tr")
    logger.info(f"Found {len(rows)} rows in ETF table")

    for row in rows[1:]:  # Skip header
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue

        code = cells[1].get_text(strip=True)
        name = cells[2].get_text(strip=True)
        index = cells[0].get_text(strip=True)
        manager = cells[3].get_text(strip=True)

        # Parse expense ratio
        expense_ratio = None
        if len(cells) > 4:
            expense_ratio = parse_expense_ratio(cells[4].get_text(strip=True))

        # Clean up name (remove iNAV link text)
        name = re.sub(r"iNAV.*$", "", name).strip()
        name = re.sub(r"\s+", " ", name)

        # Clean up manager (remove search code)
        manager = re.sub(r"\(\d+\)$", "", manager).strip()
        manager = re.sub(r"\(\d+$", "", manager).strip()
        manager = re.sub(r"株式会社$", "", manager).strip()

        # Validate code (4-digit or 3-digit+A)
        if re.match(r"^(\d{4}|\d{3}A)$", code):
            entry = {
                "code": code,
                "name": name,
                "index": index,
                "manager": manager,
                "type": "ETF",
            }
            if expense_ratio is not None:
                entry["expense_ratio"] = expense_ratio
            items.append(entry)

    logger.info(f"Fetched {len(items)} ETFs")
    return items


def fetch_jpx_etn_page(url: str) -> list:
    """Fetch ETN list from JPX website by scraping HTML table.

    ETN table columns: [上場日, 連動対象指標, コード, 名称, 発行者, 償還日, 管理費用, ...]
    """
    logger.info(f"Fetching ETN list from {url}")

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    items = []

    table = soup.find("table")
    if not table:
        raise ValueError("ETN table not found on page")

    rows = table.find_all("tr")
    logger.info(f"Found {len(rows)} rows in ETN table")

    for row in rows[1:]:  # Skip header
        cells = row.find_all(["td", "th"])
        if len(cells) < 7:
            continue

        # ETN table: [上場日, 連動対象指標, コード, 名称, 発行者, 償還日, 管理費用, ...]
        code = cells[2].get_text(strip=True)
        name = cells[3].get_text(strip=True)
        index = cells[1].get_text(strip=True)
        manager = cells[4].get_text(strip=True)

        # Parse expense ratio
        expense_ratio = parse_expense_ratio(cells[6].get_text(strip=True))

        # Clean up name (remove iNAV link text)
        name = re.sub(r"iNAV.*$", "", name).strip()
        name = re.sub(r"\s+", " ", name)

        # Clean up manager (remove search code)
        manager = re.sub(r"\(\d+\)$", "", manager).strip()
        manager = re.sub(r"\(\d+$", "", manager).strip()
        manager = re.sub(r"株式会社$", "", manager).strip()

        # Validate code (4-digit or 3-digit+A)
        if re.match(r"^(\d{4}|\d{3}A)$", code):
            entry = {
                "code": code,
                "name": name,
                "index": index,
                "manager": manager,
                "type": "ETN",
            }
            if expense_ratio is not None:
                entry["expense_ratio"] = expense_ratio
            items.append(entry)

    logger.info(f"Fetched {len(items)} ETNs")
    return items


def fetch_all_from_jpx() -> tuple:
    """Fetch all ETF/ETN lists from JPX and remove duplicates.

    Returns:
        tuple: (unique_items, etf_count, etn_count, leveraged_count)
    """
    # Fetch ETFs
    etfs = fetch_jpx_etf_page(JPX_ETF_URL)
    if not etfs:
        raise RuntimeError("No ETFs found")

    # Fetch ETNs
    etns = fetch_jpx_etn_page(JPX_ETN_URL)
    logger.info(f"Fetched {len(etns)} ETNs")

    # Fetch Leveraged/Inverse ETFs
    leveraged = fetch_jpx_etf_page(JPX_LEVERAGED_URL)
    logger.info(f"Fetched {len(leveraged)} Leveraged/Inverse ETFs")

    # Combine all lists
    all_items = etfs + etns + leveraged

    # Remove duplicates by code (keep first occurrence)
    seen_codes: Set[str] = set()
    unique_items = []
    for item in all_items:
        if item["code"] not in seen_codes:
            seen_codes.add(item["code"])
            unique_items.append(item)

    duplicates_removed = len(all_items) - len(unique_items)
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate entries")

    etf_count = len([i for i in unique_items if i.get("type") == "ETF"])
    etn_count = len([i for i in unique_items if i.get("type") == "ETN"])

    return unique_items, etf_count, etn_count, len(leveraged)


def estimate_category(index_name: str, etf_name: str) -> str:
    """Estimate category from index name and ETF name."""
    search_text = f"{index_name} {etf_name}"

    # Check leveraged/inverse first
    for keywords, category in CATEGORY_RULES:
        if category in ("レバレッジ", "インバース"):
            for keyword in keywords:
                if keyword in search_text:
                    return category

    # Check other categories
    for keywords, category in CATEGORY_RULES:
        if category not in ("レバレッジ", "インバース"):
            for keyword in keywords:
                if keyword in search_text:
                    return category

    return "国内株式"  # Default


def ensure_columns():
    """Ensure index_name, manager, and type columns exist in etfs table."""
    conn = db.engine.connect()

    try:
        conn.execute(text("SELECT index_name FROM etfs LIMIT 1"))
    except Exception:
        conn.execute(text("ALTER TABLE etfs ADD COLUMN index_name VARCHAR(100)"))
        conn.commit()
        logger.info("Added column: index_name")

    try:
        conn.execute(text("SELECT manager FROM etfs LIMIT 1"))
    except Exception:
        conn.execute(text("ALTER TABLE etfs ADD COLUMN manager VARCHAR(100)"))
        conn.commit()
        logger.info("Added column: manager")

    try:
        conn.execute(text("SELECT type FROM etfs LIMIT 1"))
    except Exception:
        conn.execute(text("ALTER TABLE etfs ADD COLUMN type VARCHAR(10) DEFAULT 'ETF' NOT NULL"))
        conn.commit()
        logger.info("Added column: type")

    conn.close()


def sync_to_db(items: list) -> tuple:
    """Sync ETF data to database.

    Args:
        items: List of ETF/ETN data dictionaries

    Returns:
        tuple: (created_count, updated_count)
    """
    etf_repo = ETFRepository()
    category_repo = CategoryRepository()

    # Build category map
    categories = category_repo.get_all_sorted()
    category_map = {c.name: c.id for c in categories}
    logger.info(f"Categories: {list(category_map.keys())}")

    created = 0
    updated = 0

    for etf_data in items:
        code = etf_data.get("code")
        name = etf_data.get("name", "")
        index_name = etf_data.get("index", "")
        manager = etf_data.get("manager", "")
        expense_ratio = etf_data.get("expense_ratio")
        etf_type = etf_data.get("type", "ETF")

        # Estimate category
        category_name = estimate_category(index_name, name)
        category_id = category_map.get(category_name)

        # Check if ETF exists
        existing = etf_repo.get_by_code(code)

        # Prepare data for save
        data_to_save = {
            "code": code,
            "name": name,
            "index_name": index_name,
            "manager": manager,
            "category_id": category_id,
            "type": etf_type,
        }

        if expense_ratio is not None:
            data_to_save["expense_ratio"] = expense_ratio

        etf_repo.create_or_update(data_to_save)

        if existing:
            updated += 1
        else:
            created += 1

    return created, updated


def main() -> int:
    """Main entry point."""
    app = create_app()
    with app.app_context():
        batch_log_repo = BatchLogRepository()
        batch_log = batch_log_repo.create(
            batch_name="sync_etf_from_jpx",
            status="running",
            started_at=datetime.utcnow(),
        )
        logger.info(f"Batch log created: id={batch_log.id}")

        try:
            # Phase 1: Ensure DB schema
            logger.info("Ensuring database columns...")
            ensure_columns()

            # Phase 2: Fetch from JPX
            logger.info("Fetching ETF/ETN data from JPX...")
            items, etf_count, etn_count, leveraged_count = fetch_all_from_jpx()
            logger.info(
                f"Fetched {len(items)} items "
                f"(ETF: {etf_count}, ETN: {etn_count}, Leveraged: {leveraged_count})"
            )

            if not items:
                raise RuntimeError("No items fetched from JPX")

            # Phase 3: Sync to DB
            logger.info("Syncing to database...")
            created, updated = sync_to_db(items)
            logger.info(f"Created: {created}, Updated: {updated}")

            # Success
            batch_log_repo.update(
                batch_log.id,
                status="success",
                finished_at=datetime.utcnow(),
            )
            logger.info(f"Batch log updated: id={batch_log.id}, status=success")
            logger.info("Sync complete!")

            return 0

        except requests.RequestException as e:
            # Network error
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            batch_log_repo.update(
                batch_log.id,
                status="failed",
                finished_at=datetime.utcnow(),
                error_message=error_msg,
            )
            return 1

        except Exception as e:
            # Other errors
            error_msg = str(e)
            logger.error(f"Failed: {error_msg}")
            batch_log_repo.update(
                batch_log.id,
                status="failed",
                finished_at=datetime.utcnow(),
                error_message=error_msg,
            )
            return 1


if __name__ == "__main__":
    sys.exit(main())
