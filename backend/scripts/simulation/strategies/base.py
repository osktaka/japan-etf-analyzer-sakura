from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Signal:
    date: date
    action: str  # "buy", "sell", "hold"
    price: float  # その日の終値


class BaseStrategy(ABC):
    """売買戦略の基底クラス。新しい戦略はこのクラスを継承する。"""

    name: str = "base"

    @abstractmethod
    def generate_signals(self, prices: list) -> list:
        """価格データからシグナルリストを生成する。

        Args:
            prices: list of dict [{"date": date, "close": float}, ...]
                    日付昇順（古い→新しい）

        Returns:
            List[Signal] - 各日付の売買シグナル
        """
        pass
