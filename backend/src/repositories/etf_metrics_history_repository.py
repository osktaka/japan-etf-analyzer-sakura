"""Repository for EtfMetricsHistory model."""
from datetime import date, datetime
from typing import Dict, List, Optional

from src.models import EtfMetricsHistory, db

from .base_repository import BaseRepository


class EtfMetricsHistoryRepository(BaseRepository):
    """Repository for managing ETF metrics history data."""

    model = EtfMetricsHistory

    def __init__(self):
        """Initialize repository with EtfMetricsHistory model."""
        super().__init__()

    def get_by_date(
        self, etf_code: str, target_date: date
    ) -> Optional[EtfMetricsHistory]:
        """Get metrics history by ETF code and date.

        Args:
            etf_code: ETF code
            target_date: Target date

        Returns:
            EtfMetricsHistory object or None
        """
        return EtfMetricsHistory.query.filter_by(
            etf_code=etf_code, date=target_date
        ).first()

    def get_metrics_batch_for_date(
        self, etf_codes: List[str], target_date: date
    ) -> Dict[str, EtfMetricsHistory]:
        """Get metrics history for multiple ETFs on a specific date.

        Args:
            etf_codes: List of ETF codes
            target_date: Target date

        Returns:
            Dictionary mapping ETF code to EtfMetricsHistory object
        """
        records = EtfMetricsHistory.query.filter(
            EtfMetricsHistory.etf_code.in_(etf_codes),
            EtfMetricsHistory.date == target_date,
        ).all()
        return {record.etf_code: record for record in records}

    def upsert(
        self,
        etf_code: str,
        target_date: date,
        dividend_yield: Optional[float] = None,
        expense_ratio: Optional[float] = None,
        total_assets: Optional[float] = None,
        deviation_rate: Optional[float] = None,
        return_1y: Optional[float] = None,
        return_3y: Optional[float] = None,
        volatility: Optional[float] = None,
        momentum_label: Optional[str] = None,
        regression_rate_1m: Optional[float] = None,
        regression_rate_3m: Optional[float] = None,
        regression_rate_6m: Optional[float] = None,
        regression_rate_1y: Optional[float] = None,
        regression_rate_3y: Optional[float] = None,
        regression_rate_5y: Optional[float] = None,
        regression_rate_10y: Optional[float] = None,
        regression_rate_20y: Optional[float] = None,
    ) -> EtfMetricsHistory:
        """Insert or update metrics history.

        Args:
            etf_code: ETF code
            target_date: Target date
            dividend_yield: Dividend yield
            expense_ratio: Expense ratio
            total_assets: Total assets
            deviation_rate: NAV deviation rate
            return_1y: 1-year return rate
            return_3y: 3-year return rate
            volatility: Annualized volatility
            momentum_label: Momentum label (e.g. "上昇加速")
            regression_rate_1m: 1-month regression rate
            regression_rate_3m: 3-month regression rate
            regression_rate_6m: 6-month regression rate
            regression_rate_1y: 1-year regression rate
            regression_rate_3y: 3-year regression rate
            regression_rate_5y: 5-year regression rate
            regression_rate_10y: 10-year regression rate
            regression_rate_20y: 20-year regression rate

        Returns:
            EtfMetricsHistory object
        """
        existing = self.get_by_date(etf_code, target_date)

        if existing:
            existing.dividend_yield = dividend_yield
            existing.expense_ratio = expense_ratio
            existing.total_assets = total_assets
            existing.deviation_rate = deviation_rate
            existing.return_1y = return_1y
            existing.return_3y = return_3y
            existing.volatility = volatility
            existing.momentum_label = momentum_label
            existing.regression_rate_1m = regression_rate_1m
            existing.regression_rate_3m = regression_rate_3m
            existing.regression_rate_6m = regression_rate_6m
            existing.regression_rate_1y = regression_rate_1y
            existing.regression_rate_3y = regression_rate_3y
            existing.regression_rate_5y = regression_rate_5y
            existing.regression_rate_10y = regression_rate_10y
            existing.regression_rate_20y = regression_rate_20y
            existing.updated_at = datetime.utcnow()
        else:
            existing = EtfMetricsHistory(
                etf_code=etf_code,
                date=target_date,
                dividend_yield=dividend_yield,
                expense_ratio=expense_ratio,
                total_assets=total_assets,
                deviation_rate=deviation_rate,
                return_1y=return_1y,
                return_3y=return_3y,
                volatility=volatility,
                momentum_label=momentum_label,
                regression_rate_1m=regression_rate_1m,
                regression_rate_3m=regression_rate_3m,
                regression_rate_6m=regression_rate_6m,
                regression_rate_1y=regression_rate_1y,
                regression_rate_3y=regression_rate_3y,
                regression_rate_5y=regression_rate_5y,
                regression_rate_10y=regression_rate_10y,
                regression_rate_20y=regression_rate_20y,
            )
            db.session.add(existing)

        db.session.commit()
        return existing

    def bulk_upsert(self, records: List[Dict], target_date: date) -> int:
        """Bulk insert or update metrics history.

        Args:
            records: List of dicts with keys: etf_code, dividend_yield,
                     expense_ratio, total_assets, deviation_rate,
                     return_1y, return_3y, volatility,
                     momentum_label, regression_rate_1m, regression_rate_3m,
                     regression_rate_6m, regression_rate_1y,
                     regression_rate_3y, regression_rate_5y,
                     regression_rate_10y, regression_rate_20y
            target_date: Target date for all records

        Returns:
            Number of records processed
        """
        etf_codes = [r["etf_code"] for r in records]
        existing_map = self.get_metrics_batch_for_date(etf_codes, target_date)

        for record in records:
            etf_code = record["etf_code"]
            existing = existing_map.get(etf_code)

            if existing:
                existing.dividend_yield = record.get("dividend_yield")
                existing.expense_ratio = record.get("expense_ratio")
                existing.total_assets = record.get("total_assets")
                existing.deviation_rate = record.get("deviation_rate")
                existing.return_1y = record.get("return_1y")
                existing.return_3y = record.get("return_3y")
                existing.volatility = record.get("volatility")
                existing.momentum_label = record.get("momentum_label")
                existing.regression_rate_1m = record.get("regression_rate_1m")
                existing.regression_rate_3m = record.get("regression_rate_3m")
                existing.regression_rate_6m = record.get("regression_rate_6m")
                existing.regression_rate_1y = record.get("regression_rate_1y")
                existing.regression_rate_3y = record.get("regression_rate_3y")
                existing.regression_rate_5y = record.get("regression_rate_5y")
                existing.regression_rate_10y = record.get("regression_rate_10y")
                existing.regression_rate_20y = record.get("regression_rate_20y")
                existing.updated_at = datetime.utcnow()
            else:
                new_record = EtfMetricsHistory(
                    etf_code=etf_code,
                    date=target_date,
                    dividend_yield=record.get("dividend_yield"),
                    expense_ratio=record.get("expense_ratio"),
                    total_assets=record.get("total_assets"),
                    deviation_rate=record.get("deviation_rate"),
                    return_1y=record.get("return_1y"),
                    return_3y=record.get("return_3y"),
                    volatility=record.get("volatility"),
                    momentum_label=record.get("momentum_label"),
                    regression_rate_1m=record.get("regression_rate_1m"),
                    regression_rate_3m=record.get("regression_rate_3m"),
                    regression_rate_6m=record.get("regression_rate_6m"),
                    regression_rate_1y=record.get("regression_rate_1y"),
                    regression_rate_3y=record.get("regression_rate_3y"),
                    regression_rate_5y=record.get("regression_rate_5y"),
                    regression_rate_10y=record.get("regression_rate_10y"),
                    regression_rate_20y=record.get("regression_rate_20y"),
                )
                db.session.add(new_record)

        db.session.commit()
        return len(records)

    def get_momentum_history(
        self, etf_code: str, limit: int = 30
    ) -> List[EtfMetricsHistory]:
        """Get momentum history for an ETF.

        Args:
            etf_code: ETF code
            limit: Number of records to return (default: 30, max: 90)

        Returns:
            List of EtfMetricsHistory objects with momentum_label
        """
        limit = min(limit, 90)
        return (
            EtfMetricsHistory.query.filter(
                EtfMetricsHistory.etf_code == etf_code,
                EtfMetricsHistory.momentum_label.isnot(None),
            )
            .order_by(EtfMetricsHistory.date.desc())
            .limit(limit)
            .all()
        )
