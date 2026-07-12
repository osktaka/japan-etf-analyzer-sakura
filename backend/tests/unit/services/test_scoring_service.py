"""Tests for ScoringService."""
from decimal import Decimal

import pytest

from src.models.etf import ETF
from src.services.scoring_service import ScoringService


@pytest.fixture
def service():
    """Create ScoringService instance (no DB access needed for these tests)."""
    return ScoringService()


class TestPercentileScore:
    """Tests for _percentile_score boundary behavior."""

    def test_value_none_returns_none(self, service):
        assert service._percentile_score(None, [1.0, 2.0, 3.0]) is None

    def test_empty_values_returns_none(self, service):
        assert service._percentile_score(10.0, []) is None

    def test_all_none_values_returns_none(self, service):
        assert service._percentile_score(10.0, [None, None]) is None

    def test_filters_none_from_values(self, service):
        # sorted_vals = [10, 20, 30] after filtering Nones
        score = service._percentile_score(20.0, [10.0, None, 20.0, None, 30.0])
        assert score == pytest.approx(0.5)

    def test_single_element_array(self, service):
        # rank=1, len=1 -> score = (1-1)/max(0,1) = 0.0 regardless of position
        assert service._percentile_score(5.0, [5.0]) == pytest.approx(0.0)

    def test_single_element_array_inverted(self, service):
        # inverted flips the degenerate 0.0 to 1.0
        assert service._percentile_score(5.0, [5.0], inverted=True) == pytest.approx(
            1.0
        )

    def test_min_value(self, service):
        assert service._percentile_score(10.0, [10.0, 20.0, 30.0]) == pytest.approx(0.0)

    def test_max_value(self, service):
        assert service._percentile_score(30.0, [10.0, 20.0, 30.0]) == pytest.approx(1.0)

    def test_tie_all_same_value(self, service):
        # rank = count(v <= value) = len -> score = (len-1)/(len-1) = 1.0
        assert service._percentile_score(
            10.0, [10.0, 10.0, 10.0, 10.0]
        ) == pytest.approx(1.0)

    def test_tie_in_middle_of_array(self, service):
        # sorted=[5,10,10,10,20], value=10 -> rank=4 -> score=(4-1)/(5-1)=0.75
        score = service._percentile_score(10.0, [5.0, 10.0, 10.0, 10.0, 20.0])
        assert score == pytest.approx(0.75)

    def test_inverted_low_value_scores_high(self, service):
        # raw score for min value is 0.0 -> inverted becomes 1.0 (best for cost-like metrics)
        score = service._percentile_score(10.0, [10.0, 20.0, 30.0], inverted=True)
        assert score == pytest.approx(1.0)

    def test_inverted_high_value_scores_low(self, service):
        # raw score for max value is 1.0 -> inverted becomes 0.0
        score = service._percentile_score(30.0, [10.0, 20.0, 30.0], inverted=True)
        assert score == pytest.approx(0.0)


class TestCalculateScore:
    """Tests for calculate_score partial/full mode switching and custom_weights."""

    def _make_etf(
        self,
        dividend_yield=None,
        expense_ratio=None,
        total_assets=None,
        market_price=None,
        deviation_rate=None,
    ):
        return ETF(
            code="1234",
            name="Test ETF",
            dividend_yield=(
                Decimal(str(dividend_yield)) if dividend_yield is not None else None
            ),
            expense_ratio=(
                Decimal(str(expense_ratio)) if expense_ratio is not None else None
            ),
            total_assets=(
                Decimal(str(total_assets)) if total_assets is not None else None
            ),
            market_price=(
                Decimal(str(market_price)) if market_price is not None else None
            ),
            deviation_rate=(
                Decimal(str(deviation_rate)) if deviation_rate is not None else None
            ),
        )

    def test_unknown_perspective_without_custom_weights_returns_zero(self, service):
        etf = self._make_etf(dividend_yield=2.0)
        assert service.calculate_score(etf, "not-a-real-perspective") == 0.0

    def test_partial_mode_below_min_required_axes_returns_zero(self, service):
        # Only 2 axes supplied via custom_weights -> available_axes(2) < MIN_REQUIRED_AXES(3)
        etf = self._make_etf(dividend_yield=2.0, expense_ratio=0.1)
        service._dividend_yields = [1.0, 2.0, 3.0]
        service._expense_ratios = [0.1, 0.2, 0.3]

        score = service.calculate_score(
            etf,
            perspective="balance",
            mode="partial",
            custom_weights={"dividend_power": 0.5, "cost_efficiency": 0.5},
        )
        assert score == 0.0

    def test_partial_mode_with_exactly_min_required_axes(self, service):
        # 3 axes available (== MIN_REQUIRED_AXES) -> score is computed, not zeroed out
        etf = self._make_etf(dividend_yield=2.0, expense_ratio=0.1, total_assets=300)
        service._dividend_yields = [1.0, 2.0, 3.0]
        service._expense_ratios = [0.1, 0.2, 0.3]
        service._total_assets = [100.0, 200.0, 300.0]

        score = service.calculate_score(
            etf,
            perspective="balance",
            mode="partial",
            custom_weights={
                "dividend_power": 0.3,
                "cost_efficiency": 0.3,
                "scale_reliability": 0.4,
            },
        )
        # dividend: percentile(2.0, [1,2,3]) = 0.5
        # cost (inverted): percentile(0.1, [0.1,0.2,0.3]) raw=0.0 -> inverted=1.0
        # scale: percentile(300, [100,200,300]) = 1.0
        # weighted = 0.5*0.3 + 1.0*0.3 + 1.0*0.4 = 0.85 -> *100
        assert score == pytest.approx(85.0)

    def test_full_mode_includes_missing_axis_weight_partial_would_zero_out(
        self, service
    ):
        # scale_reliability data missing -> available_axes drops to 2
        etf = self._make_etf(dividend_yield=2.0, expense_ratio=0.1, total_assets=None)
        service._dividend_yields = [1.0, 2.0, 3.0]
        service._expense_ratios = [0.1, 0.2, 0.3]
        service._total_assets = [100.0, 200.0, 300.0]

        custom_weights = {
            "dividend_power": 0.3,
            "cost_efficiency": 0.3,
            "scale_reliability": 0.4,
        }

        partial_score = service.calculate_score(
            etf, perspective="balance", mode="partial", custom_weights=custom_weights
        )
        full_score = service.calculate_score(
            etf, perspective="balance", mode="full", custom_weights=custom_weights
        )

        # partial: available_axes(2) < MIN_REQUIRED_AXES(3) -> zeroed out
        assert partial_score == 0.0
        # full: missing axis counts as 0 points but its weight stays in the denominator
        # weighted = 0.5*0.3 + 1.0*0.3 = 0.45, total_weight = 0.3+0.3+0.4 = 1.0 -> *100
        assert full_score == pytest.approx(45.0)

    def test_custom_weights_overrides_perspective_weights(self, service):
        # Even an unknown perspective name is accepted when custom_weights is provided
        etf = self._make_etf(dividend_yield=2.0, expense_ratio=0.1, total_assets=300)
        service._dividend_yields = [1.0, 2.0, 3.0]
        service._expense_ratios = [0.1, 0.2, 0.3]
        service._total_assets = [100.0, 200.0, 300.0]

        score = service.calculate_score(
            etf,
            perspective="does-not-exist",
            mode="partial",
            custom_weights={
                "dividend_power": 0.3,
                "cost_efficiency": 0.3,
                "scale_reliability": 0.4,
            },
        )
        assert score == pytest.approx(85.0)

    def test_perspective_default_weights_partial_mode_three_of_five_axes(self, service):
        # trading_quality/return_performance stay unavailable (no repo hit needed):
        # deviation_rate=None + caches pre-populated with an unrelated code so the
        # "cache empty -> fall back to repository" branch is never taken.
        etf = self._make_etf(
            dividend_yield=2.0, expense_ratio=0.1, total_assets=300, deviation_rate=None
        )
        service._dividend_yields = [1.0, 2.0, 3.0]
        service._expense_ratios = [0.1, 0.2, 0.3]
        service._total_assets = [100.0, 200.0, 300.0]
        service._avg_volumes_cache = {"other-code": 100.0}
        service._return_rates_cache = {"other-code": {"1y": 0.1, "3y": 0.2}}

        score = service.calculate_score(etf, perspective="balance", mode="partial")

        # balance weights are all 0.2; only dividend/cost/scale axes have data.
        # weighted = 0.5*0.2 + 1.0*0.2 + 1.0*0.2 = 0.5, total_weight = 0.6 -> *100
        assert score == pytest.approx(83.3333333, rel=1e-6)
