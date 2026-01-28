#!/usr/bin/env python3
"""Fetch ETF and ETN list from JPX and convert to JSON.

Usage:
    python scripts/fetch_etf_list.py

Output:
    src/data/etf_master.json
"""
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# JPX ETF/ETN一覧ページURL
JPX_ETF_URL = "https://www.jpx.co.jp/equities/products/etfs/issues/01.html"
JPX_ETN_URL = "https://www.jpx.co.jp/equities/products/etns/issues/01.html"

OUTPUT_PATH = Path(__file__).parent.parent / "src" / "data" / "etf_master.json"


def parse_expense_ratio(text: str) -> Optional[float]:
    """Parse expense ratio from text (e.g., '0.12%' -> 0.12)."""
    if not text:
        return None
    text = text.strip()
    # 「%」を除去して数値に変換
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

        # 信託報酬（cells[4]）をパース
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

        # 管理費用（cells[6]）をパース
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


def fetch_jpx_etf_list() -> list:
    """Fetch ETF list from JPX website."""
    return fetch_jpx_etf_page(JPX_ETF_URL)


def fetch_jpx_etn_list() -> list:
    """Fetch ETN list from JPX website."""
    return fetch_jpx_etn_page(JPX_ETN_URL)


def save_json(items: list) -> None:
    """Save ETF/ETN list to JSON file."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    etf_count = len([i for i in items if i.get("type") == "ETF"])
    etn_count = len([i for i in items if i.get("type") == "ETN"])

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "etfs": items,
                "count": len(items),
                "etf_count": etf_count,
                "etn_count": etn_count,
                "source": "JPX",
                "source_urls": [JPX_ETF_URL, JPX_ETN_URL],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(f"Saved {len(items)} items (ETF: {etf_count}, ETN: {etn_count}) to {OUTPUT_PATH}")


def main() -> int:
    """Main entry point."""
    try:
        # Fetch ETFs
        etfs = fetch_jpx_etf_list()
        if not etfs:
            logger.error("No ETFs found")
            return 1

        # Fetch ETNs
        etns = fetch_jpx_etn_list()
        logger.info(f"Fetched {len(etns)} ETNs")

        # Combine ETF and ETN lists
        all_items = etfs + etns

        save_json(all_items)

        # Statistics
        code_4digit = len([e for e in all_items if len(e["code"]) == 4 and e["code"].isdigit()])
        code_3a = len([e for e in all_items if e["code"].endswith("A")])
        logger.info(f"Statistics: 4-digit codes={code_4digit}, 3-digit+A codes={code_3a}")

        return 0

    except requests.RequestException as e:
        logger.error(f"Failed to fetch page: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
