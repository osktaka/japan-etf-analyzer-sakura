"""Stock split detection service for automatic split detection."""
import logging
from datetime import date, datetime
from typing import Optional

import yfinance as yf

from src.models import StockSplit
from src.repositories import StockSplitRepository

logger = logging.getLogger(__name__)


class SplitDetectionService:
    """Service for detecting stock splits from price changes."""

    # 株価変動の閾値（パーセント）
    PRICE_CHANGE_THRESHOLD = 30.0

    def __init__(self):
        """Initialize service with repository."""
        self.repository = StockSplitRepository()

    def check_for_splits(
        self,
        etf_code: str,
        previous_close: float,
        current_close: float,
        current_date: date,
    ) -> Optional[StockSplit]:
        """Check if a stock split occurred based on price change.

        Args:
            etf_code: ETF code (e.g., "1306")
            previous_close: Previous day's closing price
            current_close: Current day's closing price
            current_date: Current date

        Returns:
            StockSplit object if split detected, None otherwise
        """
        # 価格変動率を計算
        if previous_close == 0:
            logger.warning(f"{etf_code}: Previous close is zero, skipping split check")
            return None

        change_percent = ((current_close - previous_close) / previous_close) * 100

        # 閾値を超えない場合はスキップ
        if abs(change_percent) < self.PRICE_CHANGE_THRESHOLD:
            return None

        logger.info(
            f"{etf_code}: Large price change detected: {change_percent:.2f}% "
            f"(prev={previous_close}, curr={current_close})"
        )

        # yfinanceで分割情報を確認
        try:
            ticker = f"{etf_code}.T"
            stock = yf.Ticker(ticker)
            splits = stock.splits

            if splits.empty:
                logger.warning(
                    f"{etf_code}: Large price change but no splits in yfinance"
                )
                return None

            # 最新の分割情報を取得
            latest_split_date = splits.index[-1].date()
            split_ratio = float(splits.iloc[-1])

            # 既に登録済みかチェック
            if self.repository.exists(etf_code, latest_split_date):
                logger.info(
                    f"{etf_code}: Split already registered for {latest_split_date}"
                )
                return None

            # StockSplitオブジェクトを作成
            stock_split = StockSplit(
                etf_code=etf_code,
                split_date=latest_split_date,
                ratio=split_ratio,
                is_applied=False,
                detected_at=datetime.utcnow(),
                previous_close=previous_close,
                current_close=current_close,
                change_percent=change_percent,
            )

            logger.info(
                f"{etf_code}: Stock split detected - date={latest_split_date}, "
                f"ratio={split_ratio}, change={change_percent:.2f}%"
            )

            return stock_split

        except Exception as e:
            logger.error(f"{etf_code}: Failed to check splits from yfinance: {e}")
            return None

    def register_split(self, stock_split: StockSplit) -> Optional[StockSplit]:
        """Register a detected stock split to the database.

        Args:
            stock_split: StockSplit object to register

        Returns:
            Registered StockSplit object or None if failed
        """
        try:
            # 重複チェック（念のため）
            if self.repository.exists(stock_split.etf_code, stock_split.split_date):
                logger.warning(
                    f"{stock_split.etf_code}: Split already exists for "
                    f"{stock_split.split_date}"
                )
                return None

            # DBに保存
            created = self.repository.create(stock_split)
            logger.info(
                f"{created.etf_code}: Stock split registered - id={created.id}, "
                f"date={created.split_date}, ratio={created.ratio}"
            )
            return created

        except Exception as e:
            logger.error(
                f"{stock_split.etf_code}: Failed to register split: {e}",
                exc_info=True,
            )
            return None
