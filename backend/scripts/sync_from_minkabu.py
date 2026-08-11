#!/usr/bin/env python3
"""Sync dividend yield and total assets data from Minkabu (minkabu.jp) to database.

Usage:
    python scripts/sync_from_minkabu.py
    python scripts/sync_from_minkabu.py --codes 1306,1489
    python scripts/sync_from_minkabu.py --limit 10 --dry-run
    python scripts/sync_from_minkabu.py --rate-limit 2.0

Options:
    --codes CODES       Comma-separated ETF codes (default: all DB ETFs)
    --limit N           Limit number of ETFs to process
    --rate-limit N      Rate limit in seconds between requests (default: 1.5)
    --force             Run even on non-market days (holidays/weekends)
    --dry-run           Show what would be done without making changes
"""
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from base_batch import BaseBatchScript  # noqa: E402
from src.utils.market_calendar import is_market_open_day  # noqa: E402

MINKABU_URL = "https://minkabu.jp/stock/{code}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def fetch_minkabu_data(code: str, rate_limit: float = 1.5) -> dict:
    """Fetch dividend yield and total assets from Minkabu for a given ETF code.

    Args:
        code: ETF code (e.g., "1306")
        rate_limit: Sleep seconds after request

    Returns:
        dict with keys 'dividend_yield' (Optional[float]) and
        'total_assets' (Optional[int])
    """
    url = MINKABU_URL.format(code=code)
    headers = {"User-Agent": USER_AGENT}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    html = response.text
    dividend_yield = _parse_dividend_yield(html)
    total_assets = _parse_total_assets(html)

    time.sleep(rate_limit)
    return {
        "dividend_yield": dividend_yield,
        "total_assets": total_assets,
    }


def fetch_dividend_yield(code: str, rate_limit: float = 1.5) -> Optional[float]:
    """Fetch dividend yield from Minkabu for a given ETF code.

    Backward-compatible wrapper around fetch_minkabu_data.

    Args:
        code: ETF code (e.g., "1306")
        rate_limit: Sleep seconds after request

    Returns:
        Dividend yield as float (e.g., 1.81) or None if unavailable
    """
    data = fetch_minkabu_data(code, rate_limit)
    return data["dividend_yield"]


def _parse_dividend_yield(html: str) -> Optional[float]:
    """Parse dividend yield from Minkabu HTML.

    Extracts the yield value from the stock reference
    indicators section.
    ETFs use "分配金利回り", stocks use "配当利回り".

    Args:
        html: Raw HTML string from Minkabu

    Returns:
        Dividend yield as float or None if not found
    """
    soup = BeautifulSoup(html, "html.parser")
    keywords = ["分配金利回り", "配当利回り"]

    # thタグで探す（ETF: 分配金利回り, 株式: 配当利回り）
    th_tags = soup.find_all("th")
    for th in th_tags:
        text = th.get_text(strip=True)
        if any(kw in text for kw in keywords):
            td = th.find_next_sibling("td")
            if td:
                return _extract_yield_value(td.get_text(strip=True))

    # フォールバック: dtタグで探す
    dt_tags = soup.find_all("dt")
    for dt in dt_tags:
        text = dt.get_text(strip=True)
        if any(kw in text for kw in keywords):
            dd = dt.find_next_sibling("dd")
            if dd:
                return _extract_yield_value(dd.get_text(strip=True))

    return None


def _parse_total_assets(html: str) -> Optional[int]:
    """Parse total assets from Minkabu HTML.

    Extracts the total assets value from th/td or dt/dd patterns.
    Looks for text containing "純資産".

    Args:
        html: Raw HTML string from Minkabu

    Returns:
        Total assets in yen as int or None if not found
    """
    soup = BeautifulSoup(html, "html.parser")

    # thタグで探す
    th_tags = soup.find_all("th")
    for th in th_tags:
        text = th.get_text(strip=True)
        if "純資産" in text:
            td = th.find_next_sibling("td")
            if td:
                value = _extract_total_assets_value(td.get_text(strip=True))
                if value is not None:
                    return value

    # フォールバック: dtタグで探す
    dt_tags = soup.find_all("dt")
    for dt in dt_tags:
        text = dt.get_text(strip=True)
        if "純資産" in text:
            dd = dt.find_next_sibling("dd")
            if dd:
                value = _extract_total_assets_value(dd.get_text(strip=True))
                if value is not None:
                    return value

    return None


def _extract_total_assets_value(text: str) -> Optional[int]:
    """Extract total assets value from text like '336,430.7億円'.

    Handles units:
        - 億円: multiply by 100,000,000
        - 百万円: multiply by 1,000,000

    Args:
        text: Text containing total assets value

    Returns:
        Total assets in yen as int or None if not parseable
    """
    if not text or "---" in text or "N/A" in text:
        return None

    # カンマ除去
    cleaned = text.replace(",", "")

    # 億円単位
    match = re.search(r"([\d.]+)\s*億円", cleaned)
    if match:
        try:
            value = float(match.group(1))
            return int(value * 100_000_000)
        except ValueError:
            return None

    # 百万円単位
    match = re.search(r"([\d.]+)\s*百万円", cleaned)
    if match:
        try:
            value = float(match.group(1))
            return int(value * 1_000_000)
        except ValueError:
            return None

    return None


def _extract_yield_value(text: str) -> Optional[float]:
    """Extract numeric yield value from text like '1.81%'.

    Args:
        text: Text containing yield value (e.g., "1.81%", "---")

    Returns:
        Yield as float or None if not parseable
    """
    if not text or "---" in text or "N/A" in text:
        return None

    match = re.search(r"([\d.]+)\s*%?", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _load_all_etf_codes() -> list:
    """Load all ETF codes from database.

    Returns:
        Sorted list of ETF code strings
    """
    from src.models import ETF

    etfs = ETF.query.order_by(ETF.code).all()
    return [etf.code for etf in etfs]


def _update_from_minkabu(code: str, data: dict) -> None:
    """Update dividend yield and total assets for a single ETF.

    Args:
        code: ETF code
        data: dict with 'dividend_yield' and 'total_assets' keys
    """
    from src.models import ETF, db

    etf = ETF.query.filter_by(code=code).first()
    if not etf:
        return

    updated = False
    if data.get("dividend_yield") is not None:
        etf.dividend_yield = data["dividend_yield"]
        updated = True
    if data.get("total_assets") is not None:
        etf.total_assets = data["total_assets"]
        updated = True

    if updated:
        db.session.commit()


class SyncFromMinkabuScript(BaseBatchScript):
    """Dividend yield and total assets sync from Minkabu batch script."""

    batch_name = "sync_from_minkabu"
    description = "Sync dividend yield and total assets from Minkabu"
    enable_batch_log = True
    enable_progress = True
    progress_interval = 10

    def add_custom_arguments(self, parser):
        """Add custom CLI arguments."""
        parser.add_argument(
            "--codes",
            type=str,
            help="Comma-separated ETF codes (e.g., 1306,1489)",
        )
        parser.add_argument(
            "--rate-limit",
            type=float,
            default=1.5,
            help="Rate limit in seconds between requests (default: 1.5)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of ETFs to process",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even on non-market days (holidays/weekends)",
        )

    def execute(self) -> int:
        """Main execution logic."""
        # 非営業日は配当利回り・純資産額が動かないため、466件のスクレイプごと見送る。
        # 本番crontabは曜日指定のみで祝日を判別できないため、ここで止める必要がある。
        today = date.today()
        if not self.args.force and not is_market_open_day(today):
            self.logger.info(
                f"Non-market day ({today}), skipping minkabu sync "
                "(use --force to run anyway)"
            )
            return 0

        # Build target code list
        codes = self._resolve_target_codes()
        if not codes:
            self.logger.error("No ETF codes to process")
            return 1

        self.logger.info(f"Processing {len(codes)} ETFs...")

        # Start batch log
        self._start_batch_log(total_count=len(codes))

        success_count = 0
        fail_count = 0

        try:
            for i, code in enumerate(codes, 1):
                try:
                    result = self._process_single(code, i, len(codes))
                    if result:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    self.logger.error(f"[{i}/{len(codes)}] {code}: Error - {e}")
                    fail_count += 1

                # Update progress
                self._update_progress(last_item_code=code)

            # Final progress update
            if codes:
                self._final_progress_update(last_item_code=codes[-1])

            # Finish batch log
            # success_count / total_count を渡すことで、全件失敗ケースを
            # BaseBatchScript._finish_batch_log で status='failed' に補正させる
            self._finish_batch_log(
                success=True,
                success_count=success_count,
                total_count=len(codes),
            )

            # Summary
            self.logger.info("-" * 60)
            self.logger.info(
                f"Completed: {success_count} success, {fail_count} failed "
                f"(total: {len(codes)})"
            )

            return 0

        except Exception as e:
            self._finish_batch_log(success=False, error_message=str(e))
            raise

    def _resolve_target_codes(self) -> list:
        """Resolve target ETF codes from CLI args or database.

        Returns:
            Sorted list of ETF code strings
        """
        if self.args.codes:
            codes = [c.strip() for c in self.args.codes.split(",")]
            codes.sort()
        else:
            codes = _load_all_etf_codes()

        if self.args.limit:
            codes = codes[: self.args.limit]
            self.logger.info(f"Limited to first {self.args.limit} ETFs")

        return codes

    def _process_single(self, code: str, index: int, total: int) -> bool:
        """Process a single ETF code.

        Args:
            code: ETF code
            index: Current index (1-based)
            total: Total count

        Returns:
            True if successful, False otherwise
        """
        data = fetch_minkabu_data(code, self.args.rate_limit)
        yield_value = data["dividend_yield"]
        total_assets = data["total_assets"]

        yield_str = f"{yield_value}%" if yield_value else "N/A"
        assets_str = f"{total_assets:,}円" if total_assets else "N/A"

        if self.args.dry_run:
            self.logger.info(
                f"[{index}/{total}] {code}: [DRY-RUN] "
                f"yield={yield_str}, total_assets={assets_str}"
            )
            return yield_value is not None or total_assets is not None

        if yield_value is None and total_assets is None:
            self.logger.warning(
                f"[{index}/{total}] {code}: "
                f"Could not fetch dividend yield or total assets"
            )
            return False

        _update_from_minkabu(code, data)
        self.logger.info(
            f"[{index}/{total}] {code}: Updated "
            f"yield={yield_str}, total_assets={assets_str}"
        )
        return True


if __name__ == "__main__":
    script = SyncFromMinkabuScript()
    sys.exit(script.run())
