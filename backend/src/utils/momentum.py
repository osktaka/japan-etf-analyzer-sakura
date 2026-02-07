"""Momentum (trend) label utilities."""

from typing import Optional

RATIO_UPPER = 1.45
RATIO_LOWER = 0.55

MOMENTUM_LABELS = [
    "上昇加速",
    "上昇維持",
    "上昇減速",
    "反転上昇",
    "失速",
    "下降減速",
    "下降維持",
    "下降加速",
]


def classify_momentum(annual_1m: float, annual_3m: float) -> str:
    """Classify momentum from annualized 1M/3M values."""
    if annual_1m > 0 and annual_3m > 0:
        ratio = annual_1m / annual_3m
        if ratio > RATIO_UPPER:
            return "上昇加速"
        if ratio < RATIO_LOWER:
            return "上昇減速"
        return "上昇維持"
    if annual_1m > 0 and annual_3m <= 0:
        return "反転上昇"
    if annual_1m <= 0 and annual_3m > 0:
        return "失速"

    # annual_1m <= 0 and annual_3m <= 0
    if annual_3m == 0:
        return "下降維持" if annual_1m == 0 else "下降加速"
    ratio = annual_1m / annual_3m
    if ratio > RATIO_UPPER:
        return "下降加速"
    if ratio < RATIO_LOWER:
        return "下降減速"
    return "下降維持"


def get_momentum_label(
    rate_1m: Optional[float], rate_3m: Optional[float]
) -> Optional[str]:
    """Get momentum label from raw regression rates.

    Annualizes internally (1M*12, 3M*4).
    """
    if rate_1m is None or rate_3m is None:
        return None
    return classify_momentum(rate_1m * 12, rate_3m * 4)
