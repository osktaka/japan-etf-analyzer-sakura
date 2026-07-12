"""ETF service for ETF business logic."""
from typing import Dict, List, Optional

from src.repositories import (
    ETFRepository,
    EtfMetricsHistoryRepository,
    ScoreCacheRepository,
)
from src.models import PerformanceCache
from src.services.scoring_service import ScoringService

# Map score sort fields to scoring service perspective keys or axis keys
SCORE_SORT_FIELDS = {
    "score_balance": "balance",
    "score_dividend": "dividend",
    "score_low_cost": "low-cost",
    "score_stability": "stability",
    "score_volume": "volume",
    "score_growth": "growth",
    "score_custom": "custom",
    # Axis scores
    "axis_dividend_power": "axis_scores.dividend_power",
    "axis_cost_efficiency": "axis_scores.cost_efficiency",
    "axis_scale_reliability": "axis_scores.scale_reliability",
    "axis_trading_quality": "axis_scores.trading_quality",
    "axis_return_performance": "axis_scores.return_performance",
    # Evaluation score (balance by default)
    "evaluation_score": "score",
}

# Map perspective names to API response keys
PERSPECTIVE_TO_KEY = {
    "balance": "score_balance",
    "dividend": "score_dividend",
    "low-cost": "score_low_cost",
    "stability": "score_stability",
    "volume": "score_volume",
    "growth": "score_growth",
}


class ETFService:
    """Service for ETF operations."""

    def __init__(self):
        """Initialize service with repository."""
        self.repository = ETFRepository()
        self.score_cache_repository = ScoreCacheRepository()
        self.scoring_service = ScoringService()
        self.metrics_history_repository = EtfMetricsHistoryRepository()

    def search(
        self,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        momentum_labels: Optional[List[str]] = None,
        min_dividend_yield: Optional[float] = None,
        max_expense_ratio: Optional[float] = None,
        favorite_codes: Optional[List[str]] = None,
        holding_codes: Optional[List[str]] = None,
        sort: Optional[str] = None,
        order: str = "asc",
        return_type: str = "price",
        scoring_mode: str = "full",
        perspective: str = "balance",
        custom_weights: Optional[Dict] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict:
        """Search ETFs with filters."""
        # Check if this is a score sort
        is_score_sort = sort in SCORE_SORT_FIELDS

        # For custom score sort, we need custom_weights
        if sort == "score_custom" and not custom_weights:
            # Fallback to balance if custom_weights not provided
            sort = "score_balance"

        if is_score_sort:
            # Score sort: get all matching ETFs, compute scores, sort, then paginate
            all_etfs = self.repository.search(
                keyword=keyword,
                category_id=category_id,
                tag_ids=tag_ids,
                momentum_labels=momentum_labels,
                min_dividend_yield=min_dividend_yield,
                max_expense_ratio=max_expense_ratio,
                favorite_codes=favorite_codes,
                holding_codes=holding_codes,
                sort=None,  # No DB sort
                order=order,
                return_type=return_type,
                limit=None,  # Get all
                offset=0,
            )

            # Get scores from cache (with fallback to calculation)
            codes = [etf.code for etf in all_etfs]
            # For custom sort, calculate on-the-fly with custom_weights
            if sort == "score_custom":
                all_scores = self._get_batch_custom_scores(
                    codes, scoring_mode, custom_weights
                )
            else:
                all_scores = self.get_batch_scores(codes, scoring_mode)

            # Get the score key to sort by
            score_key = SCORE_SORT_FIELDS[sort]

            # Helper function to get nested value (e.g., "axis_scores.dividend_power")
            def get_score_value(etf):
                scores_data = all_scores.get(etf.code, {})
                if "." in score_key:
                    # Nested key (e.g., "axis_scores.dividend_power")
                    parts = score_key.split(".")
                    value = scores_data
                    for part in parts:
                        value = value.get(part) if isinstance(value, dict) else None
                        if value is None:
                            return -1
                    return value if value is not None else -1
                elif score_key == "custom":
                    # Custom score (uses 'score' field from custom calculation)
                    return scores_data.get("score", -1)
                else:
                    # Top-level key (e.g., "balance", "score")
                    return scores_data.get(score_key, -1)

            # Sort by score (missing scores = -1, sorted to end)
            all_etfs.sort(key=get_score_value, reverse=(order == "desc"))

            # Apply pagination
            total = len(all_etfs)
            etfs = all_etfs[offset : offset + limit]
        else:
            # Normal sort: use repository pagination
            etfs = self.repository.search(
                keyword=keyword,
                category_id=category_id,
                tag_ids=tag_ids,
                momentum_labels=momentum_labels,
                min_dividend_yield=min_dividend_yield,
                max_expense_ratio=max_expense_ratio,
                favorite_codes=favorite_codes,
                holding_codes=holding_codes,
                sort=sort,
                order=order,
                return_type=return_type,
                limit=limit,
                offset=offset,
            )
            total = self.repository.count(
                keyword=keyword,
                category_id=category_id,
                tag_ids=tag_ids,
                momentum_labels=momentum_labels,
                min_dividend_yield=min_dividend_yield,
                max_expense_ratio=max_expense_ratio,
                favorite_codes=favorite_codes,
                holding_codes=holding_codes,
            )

        # Get scores for all ETFs with the specified perspective
        codes = [etf.code for etf in etfs]
        # カスタムの場合は計算、それ以外はキャッシュから取得
        if perspective == "custom" and custom_weights:
            all_scores = self._get_batch_custom_scores(
                codes, scoring_mode, custom_weights
            )
        else:
            all_scores = self._get_scores_for_perspective(
                codes, perspective, scoring_mode
            )

        # Merge scores into items
        items = []
        for etf in etfs:
            item = etf.to_summary_dict()
            score_data = all_scores.get(etf.code)
            if score_data:
                item["score"] = score_data["score"]
                item["axis_scores"] = score_data["axis_scores"]
            else:
                item["score"] = None
                item["axis_scores"] = None
            items.append(item)

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_by_code(self, code: str) -> Optional[dict]:
        """Get ETF details by code."""
        etf = self.repository.get_by_code(code)
        if not etf:
            return None

        # Get basic ETF data
        result = etf.to_dict()

        # Get score from cache (all 6 perspectives)
        score_caches = self.score_cache_repository.get_by_code(code)

        # Add all perspective scores
        balance_cache = None
        for cache in score_caches:
            key = PERSPECTIVE_TO_KEY.get(cache.perspective)
            if key:
                result[key] = cache.total_score
            if cache.perspective == "balance":
                balance_cache = cache

        # Set default score and axis_scores from balance perspective
        if balance_cache:
            result["score"] = balance_cache.total_score
            result["score_full"] = balance_cache.total_score_full
            result["axis_scores"] = {
                "dividend_power": balance_cache.dividend_power,
                "cost_efficiency": balance_cache.cost_efficiency,
                "scale_reliability": balance_cache.scale_reliability,
                "trading_quality": balance_cache.trading_quality,
                "return_performance": balance_cache.return_performance,
            }
        else:
            result["score"] = None
            result["score_full"] = None
            result["axis_scores"] = None

        # Add score basis data
        # 30-day average volume
        result["average_volume"] = self.repository.get_average_volume(code, days=30)

        # Trading value (price × volume)
        if etf.market_price and result["average_volume"]:
            result["trading_value"] = float(etf.market_price) * result["average_volume"]
        else:
            result["trading_value"] = None

        # Return rates and regression rates from PerformanceCache
        perf_data = PerformanceCache.query.filter(
            PerformanceCache.etf_code == code
        ).all()
        regression_rates = {}
        return_1y = None
        return_3y = None
        for perf in perf_data:
            regression_rates[perf.period] = perf.regression_rate
            if perf.period == "1y":
                return_1y = perf.return_rate
            elif perf.period == "3y":
                return_3y = perf.return_rate

        result["return_1y"] = return_1y
        result["return_3y"] = return_3y
        result["regression_rates"] = regression_rates

        return result

    def get_all(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get all ETFs with pagination."""
        etfs = self.repository.search(limit=limit, offset=offset)
        return {
            "items": [etf.to_summary_dict() for etf in etfs],
            "total": len(etfs),
            "limit": limit,
            "offset": offset,
        }

    def get_batch_scores(
        self, codes: List[str], scoring_mode: str = "full"
    ) -> Dict[str, Dict]:
        """Get all 6 perspective scores + axis scores for multiple ETFs.

        Args:
            codes: List of ETF codes
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            Dict mapping ETF code to dict with perspective scores, axis_scores, and score
            Example: {
                "1489": {
                    "balance": 78.5,
                    "dividend": 85.2,
                    ...,
                    "axis_scores": {"dividend_power": 80.0, ...},
                    "score": 78.5
                }
            }
        """
        # Try to get from cache first
        cached_data = self.score_cache_repository.get_all_perspectives_batch(codes)

        result = {}
        missing_codes = []

        for code in codes:
            if code in cached_data and cached_data[code]:
                # Convert cached data to score dict based on scoring_mode
                perspective_scores = {}
                if scoring_mode == "partial":
                    perspective_scores = {
                        perspective: cache.total_score
                        for perspective, cache in cached_data[code].items()
                    }
                else:  # full mode (default)
                    perspective_scores = {
                        perspective: cache.total_score_full
                        if cache.total_score_full is not None
                        else cache.total_score
                        for perspective, cache in cached_data[code].items()
                    }

                # Add axis_scores from balance cache
                balance_cache = cached_data[code].get("balance")
                if balance_cache:
                    axis_scores = {
                        "dividend_power": balance_cache.dividend_power,
                        "cost_efficiency": balance_cache.cost_efficiency,
                        "scale_reliability": balance_cache.scale_reliability,
                        "trading_quality": balance_cache.trading_quality,
                        "return_performance": balance_cache.return_performance,
                    }
                    score = (
                        balance_cache.total_score_full
                        if scoring_mode == "full"
                        and balance_cache.total_score_full is not None
                        else balance_cache.total_score
                    )
                else:
                    axis_scores = None
                    score = None

                result[code] = {
                    **perspective_scores,
                    "axis_scores": axis_scores,
                    "score": score,
                }
            else:
                missing_codes.append(code)

        # Fallback: calculate missing scores on-the-fly
        if missing_codes:
            calculated_scores = self.scoring_service.get_all_scores_batch(missing_codes)
            etfs = [self.repository.get_by_code(code) for code in missing_codes]
            etf_map = {etf.code: etf for etf in etfs if etf}

            for code, scores in calculated_scores.items():
                etf = etf_map.get(code)
                axis_scores = (
                    self.scoring_service.calculate_axis_scores(etf) if etf else None
                )
                result[code] = {
                    **scores,
                    "axis_scores": axis_scores,
                    "score": scores.get("balance"),
                }

        return result

    def _get_scores_for_perspective(
        self, codes: List[str], perspective: str, scoring_mode: str = "full"
    ) -> Dict[str, Dict]:
        """Get scores for a specific perspective.

        Args:
            codes: List of ETF codes
            perspective: Perspective ID (balance, dividend, low-cost, etc.)
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            Dict mapping ETF code to dict with score and axis_scores
        """
        return self.score_cache_repository.get_scores_with_axes(
            codes, perspective, scoring_mode
        )

    def _get_batch_custom_scores(
        self, codes: List[str], scoring_mode: str, custom_weights: Dict
    ) -> Dict[str, Dict]:
        """Calculate custom scores for multiple ETFs.

        Args:
            codes: List of ETF codes
            scoring_mode: Scoring mode - "full" or "partial"
            custom_weights: Custom weights dict

        Returns:
            Dict mapping ETF code to dict with score and axis_scores
        """
        result = {}
        etf_map = self.repository.get_by_codes(codes)

        # Get all ETFs for percentile calculation
        all_etfs = self.repository.search(limit=None, offset=0)

        # Pre-load return rates and average volumes (batch to avoid N+1)
        all_etf_codes = [etf.code for etf in all_etfs]
        self.scoring_service._return_rates_cache = (
            self.repository.get_return_rates_batch(all_etf_codes)
        )
        self.scoring_service._avg_volumes_cache = (
            self.repository.get_average_volumes_batch(all_etf_codes, days=30)
        )

        # Collect percentile data
        self.scoring_service._collect_percentile_data(all_etfs)

        for code in codes:
            etf = etf_map.get(code)
            if not etf:
                continue

            # Calculate custom score
            score = self.scoring_service.calculate_score(
                etf,
                perspective="balance",
                mode=scoring_mode,
                custom_weights=custom_weights,
            )
            axis_scores = self.scoring_service.calculate_axis_scores(etf)

            result[code] = {
                "score": score,
                "axis_scores": axis_scores,
            }

        return result

    def get_momentum_history(self, code: str, limit: int = 30) -> List[dict]:
        """Get momentum history for an ETF.

        Args:
            code: ETF code
            limit: Number of records to return (default: 30)

        Returns:
            List of momentum history dicts
        """
        records = self.metrics_history_repository.get_momentum_history(code, limit)
        return [
            {
                "date": str(record.date),
                "momentum_label": record.momentum_label,
                "regression_rate_1m": record.regression_rate_1m,
                "regression_rate_3m": record.regression_rate_3m,
                "regression_rate_6m": record.regression_rate_6m,
                "regression_rate_1y": record.regression_rate_1y,
                "regression_rate_3y": record.regression_rate_3y,
                "regression_rate_5y": record.regression_rate_5y,
                "regression_rate_10y": record.regression_rate_10y,
                "regression_rate_20y": record.regression_rate_20y,
                "return_rate_1m": record.return_rate_1m,
                "return_rate_3m": record.return_rate_3m,
                "return_rate_6m": record.return_rate_6m,
                "return_rate_1y": record.return_rate_1y,
                "return_rate_3y": record.return_rate_3y,
                "return_rate_5y": record.return_rate_5y,
                "return_rate_10y": record.return_rate_10y,
                "return_rate_20y": record.return_rate_20y,
            }
            for record in records
        ]
