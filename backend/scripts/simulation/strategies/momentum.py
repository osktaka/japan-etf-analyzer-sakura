"""モメンタム（勢い）ベースの売買戦略。"""

from typing import List, Optional, Tuple

from src.utils.momentum import get_momentum_label

from simulation.regression import calculate_regression_return
from simulation.strategies.base import BaseStrategy, Signal

DEFAULT_WINDOW_1M = 30
DEFAULT_WINDOW_3M = 90

DEFAULT_BUY_LABELS = frozenset({"上昇加速", "反転上昇"})
DEFAULT_SELL_LABELS = frozenset({"失速", "下降減速", "下降維持", "下降加速"})


class MomentumStrategy(BaseStrategy):
    """モメンタム（勢い）ベースの売買戦略。

    2つのバリアント:
    - label: 勢いラベルでシグナル判定
    - threshold: 回帰上昇率の閾値でシグナル判定
    """

    name = "momentum"

    def __init__(
        self,
        variant: str = "label",
        buy_threshold: float = 10.0,
        sell_threshold: float = 0.0,
        buy_labels: Optional[frozenset] = None,
        sell_labels: Optional[frozenset] = None,
        window_1m: int = DEFAULT_WINDOW_1M,
        window_3m: int = DEFAULT_WINDOW_3M,
    ):
        self.variant = variant
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.buy_labels = buy_labels or DEFAULT_BUY_LABELS
        self.sell_labels = sell_labels or DEFAULT_SELL_LABELS
        self.window_1m = window_1m
        self.window_3m = window_3m
        self.warmup_days = max(window_1m, window_3m)

    def generate_signals(self, prices: list) -> list:
        """価格データからモメンタムベースのシグナルを生成。

        Args:
            prices: [{"date": date, "close": float}, ...] 日付昇順

        Returns:
            List[Signal] - 各日付の売買シグナル
        """
        signals: List[Signal] = []

        for i, price in enumerate(prices):
            if i < self.warmup_days:
                signals.append(Signal(
                    date=price["date"], action="hold", price=price["close"],
                ))
                continue

            rate_1m, rate_3m = self._calc_rates(prices, i)
            action = self._decide_action(rate_1m, rate_3m)
            signals.append(Signal(
                date=price["date"], action=action, price=price["close"],
            ))

        return signals

    def _calc_rates(
        self, prices: list, i: int,
    ) -> Tuple[Optional[float], Optional[float]]:
        """指定インデックス時点の1ヶ月・3ヶ月回帰リターンを算出。"""
        start_1m = max(0, i - self.window_1m + 1)
        closes_1m = [p["close"] for p in prices[start_1m : i + 1]]
        rate_1m = calculate_regression_return(closes_1m, self.window_1m)

        start_3m = max(0, i - self.window_3m + 1)
        closes_3m = [p["close"] for p in prices[start_3m : i + 1]]
        rate_3m = calculate_regression_return(closes_3m, self.window_3m)

        return rate_1m, rate_3m

    def _decide_action(
        self, rate_1m: Optional[float], rate_3m: Optional[float],
    ) -> str:
        """バリアントに応じて売買アクションを決定。"""
        if self.variant == "label":
            return self._decide_by_label(rate_1m, rate_3m)
        return self._decide_by_threshold(rate_1m)

    def _decide_by_label(
        self, rate_1m: Optional[float], rate_3m: Optional[float],
    ) -> str:
        """勢いラベルでシグナル判定。"""
        label = get_momentum_label(rate_1m, rate_3m)
        if label is None:
            return "hold"
        if label in self.buy_labels:
            return "buy"
        if label in self.sell_labels:
            return "sell"
        return "hold"

    def _decide_by_threshold(self, rate_1m: Optional[float]) -> str:
        """回帰上昇率の閾値でシグナル判定。"""
        if rate_1m is None:
            return "hold"
        annual_1m = rate_1m * 12
        if annual_1m > self.buy_threshold:
            return "buy"
        if annual_1m < self.sell_threshold:
            return "sell"
        return "hold"
