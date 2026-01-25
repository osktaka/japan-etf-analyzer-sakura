#!/usr/bin/env python3
"""Fetch ETF list from JPX and convert to JSON.

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

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# JPX ETF一覧ページURL
JPX_ETF_URL = "https://www.jpx.co.jp/equities/products/etfs/issues/01.html"

OUTPUT_PATH = Path(__file__).parent.parent / "src" / "data" / "etf_master.json"


def fetch_jpx_etf_list() -> list:
    """Fetch ETF list from JPX website by scraping HTML table."""
    logger.info(f"Fetching ETF list from {JPX_ETF_URL}")

    response = requests.get(JPX_ETF_URL, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    etfs = []

    table = soup.find("table")
    if not table:
        raise ValueError("ETF table not found on page")

    rows = table.find_all("tr")
    logger.info(f"Found {len(rows)} rows in table")

    for row in rows[1:]:  # Skip header
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue

        code = cells[1].get_text(strip=True)
        name = cells[2].get_text(strip=True)
        index = cells[0].get_text(strip=True)
        manager = cells[3].get_text(strip=True)

        # Clean up name (remove iNAV link text)
        name = re.sub(r"iNAV.*$", "", name).strip()
        name = re.sub(r"\s+", " ", name)

        # Clean up manager (remove search code)
        manager = re.sub(r"\(\d+\)$", "", manager).strip()
        manager = re.sub(r"\(\d+$", "", manager).strip()
        manager = re.sub(r"株式会社$", "", manager).strip()

        # Validate code (4-digit or 3-digit+A)
        if re.match(r"^(\d{4}|\d{3}A)$", code):
            etfs.append(
                {
                    "code": code,
                    "name": name,
                    "index": index,
                    "manager": manager,
                }
            )

    return etfs


def save_json(etfs: list) -> None:
    """Save ETF list to JSON file."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "etfs": etfs,
                "count": len(etfs),
                "source": "JPX",
                "source_url": JPX_ETF_URL,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(f"Saved {len(etfs)} ETFs to {OUTPUT_PATH}")


def main() -> int:
    """Main entry point."""
    try:
        etfs = fetch_jpx_etf_list()

        if not etfs:
            logger.error("No ETFs found")
            return 1

        save_json(etfs)

        # Statistics
        code_4digit = len([e for e in etfs if len(e["code"]) == 4 and e["code"].isdigit()])
        code_3a = len([e for e in etfs if e["code"].endswith("A")])
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
