"""シミュレーションエンジン。

シグナルリストに従い単一ポジションの売買シミュレーションを実行する。
"""

from dataclasses import dataclass
from datetime import date
from math import floor
from typing import Dict, List, Optional, Tuple

from simulation.strategies.base import Signal  # noqa: F401


@dataclass
class Trade:
    date: date
    action: str  # "buy" or "sell"
    price: float
    quantity: float
    pnl: Optional[float] = None  # sellの時のみ


class SimulationEngine:
    """シグナルベースの売買シミュレーター。"""

    def __init__(self, capital: float = 1_000_000):
        self.initial_capital = capital

    def run(self, signals: List[Signal]) -> Dict:
        """シグナルリストに従い売買を実行し、結果をdictで返す。

        Args:
            signals: 日付順のSignalリスト

        Returns:
            シミュレーション結果dict
        """
        if not signals:
            return self._empty_result()

        trades: List[Trade] = []
        capital = self.initial_capital
        position: Optional[Dict] = None
        peak_value = capital
        max_drawdown = 0.0

        for sig in signals:
            capital, position, peak_value, max_drawdown = self._process_signal(
                sig, capital, position, trades, peak_value, max_drawdown
            )

        result = self._build_result(
            trades, capital, position, signals, peak_value, max_drawdown
        )
        return result

    def _process_signal(
        self,
        sig: Signal,
        capital: float,
        position: Optional[Dict],
        trades: List[Trade],
        peak_value: float,
        max_drawdown: float,
    ) -> Tuple[float, Optional[Dict], float, float]:
        """1つのシグナルを処理する。"""
        if sig.action == "buy" and position is None:
            capital, position = self._execute_buy(
                sig, capital, trades
            )
        elif sig.action == "sell" and position is not None:
            capital, position = self._execute_sell(
                sig, capital, position, trades
            )

        # 資産評価とドローダウン更新
        current_value = self._evaluate(capital, position, sig.price)
        peak_value = max(peak_value, current_value)
        drawdown = _calc_drawdown(current_value, peak_value)
        max_drawdown = max(max_drawdown, drawdown)

        return capital, position, peak_value, max_drawdown

    def _execute_buy(
        self, sig: Signal, capital: float, trades: List[Trade]
    ) -> Tuple[float, Optional[Dict]]:
        """買い注文を実行する。"""
        if sig.price <= 0:
            return capital, None
        quantity = floor(capital / sig.price)
        if quantity <= 0:
            return capital, None
        cost = quantity * sig.price
        capital -= cost
        trades.append(Trade(
            date=sig.date, action="buy",
            price=sig.price, quantity=quantity,
        ))
        return capital, {"price": sig.price, "quantity": quantity}

    def _execute_sell(
        self,
        sig: Signal,
        capital: float,
        position: Dict,
        trades: List[Trade],
    ) -> Tuple[float, None]:
        """売り注文を実行する。"""
        pnl = (sig.price - position["price"]) * position["quantity"]
        proceeds = sig.price * position["quantity"]
        capital += proceeds
        trades.append(Trade(
            date=sig.date, action="sell",
            price=sig.price, quantity=position["quantity"],
            pnl=round(pnl, 2),
        ))
        return capital, None

    @staticmethod
    def _evaluate(
        capital: float, position: Optional[Dict], price: float
    ) -> float:
        """現在の資産評価額を返す。"""
        if position is None:
            return capital
        return capital + position["quantity"] * price

    def _build_result(
        self,
        trades: List[Trade],
        capital: float,
        position: Optional[Dict],
        signals: List[Signal],
        peak_value: float,
        max_drawdown: float,
    ) -> Dict:
        """最終結果dictを組み立てる。"""
        sell_trades = [t for t in trades if t.action == "sell"]
        total_pnl = sum(t.pnl for t in sell_trades if t.pnl is not None)
        win_count = sum(
            1 for t in sell_trades if t.pnl is not None and t.pnl > 0
        )
        trade_count = len(sell_trades)
        win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0.0

        # 未決済ポジション
        open_pos = None
        if position is not None:
            last_price = signals[-1].price
            unrealized = (last_price - position["price"]) * position["quantity"]
            open_pos = {
                "buy_price": position["price"],
                "quantity": position["quantity"],
                "current_price": last_price,
                "unrealized_pnl": round(unrealized, 2),
                "market_value": round(last_price * position["quantity"], 2),
            }

        # 最終資産（未決済含む）
        final_value = self._evaluate(
            capital, position, signals[-1].price
        )
        return_pct = round(
            (final_value - self.initial_capital) / self.initial_capital * 100, 2
        )

        bh_return = _buy_and_hold_return(signals)

        return {
            "trades": trades,
            "total_pnl": round(total_pnl, 2),
            "return_pct": return_pct,
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(max_drawdown, 2),
            "trade_count": trade_count,
            "win_count": win_count,
            "buy_and_hold_return": bh_return,
            "open_position": open_pos,
            "period": {
                "start": signals[0].date,
                "end": signals[-1].date,
            },
        }

    def _empty_result(self) -> Dict:
        """シグナルが空の場合のデフォルト結果。"""
        return {
            "trades": [],
            "total_pnl": 0.0,
            "return_pct": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "trade_count": 0,
            "win_count": 0,
            "buy_and_hold_return": 0.0,
            "open_position": None,
            "period": None,
        }

    @staticmethod
    def print_report(result: Dict, strategy_name: str = "") -> None:
        """結果dictをコンソールに整形出力する。"""
        _print_header(result, strategy_name)
        _print_trades_table(result["trades"])
        _print_open_position(result.get("open_position"))
        _print_summary(result)


# --- モジュールレベルヘルパー ---


def _calc_drawdown(current: float, peak: float) -> float:
    """ピーク値からの下落率(%)を返す。"""
    if peak <= 0:
        return 0.0
    return (peak - current) / peak * 100


def _buy_and_hold_return(signals: List[Signal]) -> float:
    """最初の価格で買い、最後の価格で売った場合のリターン(%)。"""
    if len(signals) < 2:
        return 0.0
    first = signals[0].price
    last = signals[-1].price
    if first == 0:
        return 0.0
    return round((last - first) / first * 100, 2)


def _print_header(result: Dict, strategy_name: str) -> None:
    """レポートヘッダーを出力する。"""
    print("=" * 70)
    title = f"Simulation Report: {strategy_name}" if strategy_name else "Simulation Report"
    print(title)
    print("=" * 70)
    period = result.get("period")
    if period:
        print(f"Period: {period['start']} ~ {period['end']}")
    print()


def _print_trades_table(trades: List[Trade]) -> None:
    """取引一覧テーブルを出力する。"""
    if not trades:
        print("No trades executed.")
        print()
        return

    print(f"{'Date':<12} {'Action':<6} {'Price':>10} {'Qty':>8} {'PnL':>12}")
    print("-" * 50)
    for t in trades:
        pnl_str = f"{t.pnl:>+12,.2f}" if t.pnl is not None else " " * 12
        print(
            f"{str(t.date):<12} {t.action:<6} "
            f"{t.price:>10,.2f} {t.quantity:>8,.0f} {pnl_str}"
        )
    print()


def _print_open_position(open_pos: Optional[Dict]) -> None:
    """未決済ポジション情報を出力する。"""
    if open_pos is None:
        return
    print("[ Open Position ]")
    print(f"  Buy Price:      {open_pos['buy_price']:>12,.2f}")
    print(f"  Quantity:       {open_pos['quantity']:>12,.0f}")
    print(f"  Current Price:  {open_pos['current_price']:>12,.2f}")
    print(f"  Market Value:   {open_pos['market_value']:>12,.2f}")
    print(f"  Unrealized PnL: {open_pos['unrealized_pnl']:>+12,.2f}")
    print()


def _print_summary(result: Dict) -> None:
    """サマリーセクションを出力する。"""
    print("-" * 50)
    print("[ Summary ]")
    print(f"  Total PnL:       {result['total_pnl']:>+12,.2f}")
    print(f"  Return:          {result['return_pct']:>+11.2f}%")
    print(f"  Trades:          {result['trade_count']:>12d}")
    print(f"  Wins:            {result['win_count']:>12d}")
    print(f"  Win Rate:        {result['win_rate']:>11.2f}%")
    print(f"  Max Drawdown:    {result['max_drawdown']:>11.2f}%")
    print(f"  Buy & Hold:      {result['buy_and_hold_return']:>+11.2f}%")
    if result.get("open_position"):
        pnl = result["open_position"]["unrealized_pnl"]
        print(f"  Unrealized PnL:  {pnl:>+12,.2f}")
    print("=" * 70)
