#!/usr/bin/env python3
"""Momentum level backtest simulation.

Simulates buy/sell based on momentum level changes for a user's ETFs.

Usage:
    python scripts/backtest_momentum.py [--user USERNAME] [--initial-qty N] [--trade-ratio R]
    python scripts/backtest_momentum.py --etf 1306,1343,2631
    python scripts/backtest_momentum.py --top 10
"""
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(SCRIPT_DIR))
from base_batch import SimpleBatchScript

from src.models.etf_metrics_history import EtfMetricsHistory
from src.models.price_history import PriceHistory
from src.models.score_cache import ScoreCache
from src.models.stock_split import StockSplit
from src.models.trade import Trade
from src.models.user import User
from src.utils.momentum import MOMENTUM_LABELS

OUTPUT_DIR = SCRIPT_DIR / "output"


logger = logging.getLogger(__name__)


class MomentumBacktester:
    """Backtest engine based on momentum level changes."""

    def __init__(self, initial_qty=100, trade_unit_ratio=0.25):
        self.initial_qty = initial_qty
        self.trade_unit = int(initial_qty * trade_unit_ratio)

    def run(self, etf_code, momentum_data, price_data, split_ratio=1.0):
        """Run backtest for a single ETF.

        Args:
            etf_code: ETF code string
            momentum_data: list of (date, momentum_label)
            price_data: dict {date: close_price}
            split_ratio: total split ratio (product of all splits)

        Returns:
            dict with backtest results
        """
        if len(momentum_data) < 2:
            return self._empty_result(etf_code)

        state = self._init_state(momentum_data[0], price_data, split_ratio)
        if state is None:
            return self._empty_result(etf_code)

        trades_log = self._simulate(momentum_data, price_data, state)
        return self._build_result(etf_code, momentum_data, price_data, state, trades_log)

    def _init_state(self, first_record, price_data, split_ratio=1.0):
        """Initialize position state on the first day."""
        first_date, first_label = first_record
        if first_date not in price_data:
            return None
        price = price_data[first_date]
        level_idx = self._label_to_index(first_label)
        return {
            "qty": self.initial_qty,
            "avg_cost": price,
            "realized_pnl": 0.0,
            "initial_cost": self.initial_qty * price,
            "cumulative_invested": self.initial_qty * price,
            "buy_count": 1,
            "sell_count": 0,
            "prev_level_idx": level_idx,
            "first_date": first_date,
            "first_price": price,
            "unadjusted_first_price": price * split_ratio,
        }

    def _simulate(self, momentum_data, price_data, state):
        """Process day-by-day momentum changes."""
        trades_log = []
        for i in range(1, len(momentum_data)):
            date_val, label = momentum_data[i]
            if date_val not in price_data:
                continue
            price = price_data[date_val]
            curr_idx = self._label_to_index(label)
            level_change = curr_idx - state["prev_level_idx"]

            if level_change < 0:
                self._process_buy(state, price, abs(level_change), trades_log, date_val)
            elif level_change > 0:
                self._process_sell(state, price, level_change, trades_log, date_val)

            state["prev_level_idx"] = curr_idx
        return trades_log

    def _process_buy(self, state, price, change_abs, trades_log, date_val):
        """Process a buy signal."""
        buy_qty = change_abs * self.trade_unit
        old_qty = state["qty"]
        if old_qty == 0:
            state["avg_cost"] = price
        else:
            total_cost = old_qty * state["avg_cost"] + buy_qty * price
            state["avg_cost"] = total_cost / (old_qty + buy_qty)
        state["qty"] += buy_qty
        state["initial_cost"] += buy_qty * price
        state["cumulative_invested"] += buy_qty * price
        state["buy_count"] += 1
        trades_log.append(("buy", date_val, buy_qty, price))

    def _process_sell(self, state, price, change, trades_log, date_val):
        """Process a sell signal."""
        sell_qty = min(change * self.trade_unit, state["qty"])
        if sell_qty <= 0:
            return
        state["realized_pnl"] += sell_qty * (price - state["avg_cost"])
        state["qty"] -= sell_qty
        state["initial_cost"] -= sell_qty * state["avg_cost"]
        state["sell_count"] += 1
        trades_log.append(("sell", date_val, sell_qty, price))

    def _build_result(self, etf_code, momentum_data, price_data, state, trades_log):
        """Build result dict from final state."""
        last_date, _ = momentum_data[-1]
        last_price = price_data.get(last_date, 0)
        unrealized = state["qty"] * (last_price - state["avg_cost"])
        total_pnl = state["realized_pnl"] + unrealized
        bh_pnl = self.initial_qty * (last_price - state["first_price"])
        cum_invested = state["cumulative_invested"]

        # 共通分母（分割前の実初期投資額）
        initial_investment = self.initial_qty * state["unadjusted_first_price"]

        return {
            "etf_code": etf_code,
            "period_start": str(state["first_date"]),
            "period_end": str(last_date),
            "first_price": state["first_price"],
            "trading_days": len(momentum_data),
            "buy_count": state["buy_count"],
            "sell_count": state["sell_count"],
            "initial_qty": self.initial_qty,
            "final_qty": state["qty"],
            "initial_investment": round(initial_investment),
            "total_invested": round(cum_invested),
            "realized_pnl": round(state["realized_pnl"]),
            "unrealized_pnl": round(unrealized),
            "total_pnl": round(total_pnl),
            "total_pnl_pct": self._pct(total_pnl, initial_investment),
            "buy_and_hold_pnl": round(bh_pnl),
            "buy_and_hold_pct": self._pct(bh_pnl, initial_investment),
            "excess_return_pct": round(
                self._pct(total_pnl, initial_investment)
                - self._pct(bh_pnl, initial_investment),
                1,
            ),
            "trades": [
                {"type": t, "date": str(d), "qty": q, "price": round(p, 1)}
                for t, d, q, p in trades_log
            ],
        }

    def _pct(self, pnl, base):
        """Calculate percentage."""
        if base == 0:
            return 0.0
        return round(pnl / base * 100, 1)

    def _label_to_index(self, label):
        """Convert momentum label to index."""
        try:
            return MOMENTUM_LABELS.index(label)
        except ValueError:
            logger.warning(
                "Unknown momentum label '%s', falling back to index 4", label
            )
            return 4  # fallback to middle

    def _empty_result(self, etf_code):
        """Return empty result for insufficient data."""
        return {
            "etf_code": etf_code,
            "period_start": "",
            "period_end": "",
            "first_price": 0,
            "trading_days": 0,
            "buy_count": 0,
            "sell_count": 0,
            "initial_qty": self.initial_qty,
            "final_qty": 0,
            "initial_investment": 0,
            "total_invested": 0,
            "realized_pnl": 0,
            "unrealized_pnl": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0.0,
            "buy_and_hold_pnl": 0,
            "buy_and_hold_pct": 0.0,
            "excess_return_pct": 0.0,
            "trades": [],
        }


class BacktestMomentumBatch(SimpleBatchScript):
    """Momentum level backtest simulation batch."""

    batch_name = "backtest_momentum"
    description = "Momentum level backtest simulation"

    def add_custom_arguments(self, parser):
        """Add backtest-specific arguments."""
        parser.add_argument(
            "--initial-qty",
            type=int,
            default=100,
            help="Initial quantity per ETF (default: 100)",
        )
        parser.add_argument(
            "--trade-ratio",
            type=float,
            default=0.25,
            help="Trade unit ratio (default: 0.25)",
        )
        parser.add_argument(
            "--etf",
            type=str,
            default=None,
            help="Comma-separated ETF codes (e.g., 1306,1343,2631)",
        )
        parser.add_argument(
            "--top",
            type=int,
            default=None,
            help="Use top N ETFs by recommendation score",
        )
        parser.add_argument(
            "--user",
            type=str,
            default="demo",
            help="Target username (default: demo)",
        )
        parser.add_argument(
            "--start",
            type=str,
            default=None,
            help="Backtest start date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--end",
            type=str,
            default=None,
            help="Backtest end date (YYYY-MM-DD)",
        )

    def execute(self):
        """Run backtest for target ETFs."""
        if self.args.etf:
            etf_codes = sorted(self.args.etf.split(","))
        elif self.args.top:
            etf_codes = self._get_top_etf_codes(self.args.top)
        else:
            etf_codes = self._get_user_etf_codes()

        if not etf_codes:
            if self.args.etf:
                self.logger.error("No ETF codes specified")
            elif self.args.top:
                self.logger.error("No ETFs found with sufficient momentum data")
            else:
                self.logger.error(f"No ETFs found for user '{self.args.user}'")
            return 1

        self.logger.info(f"Target ETFs: {etf_codes}")
        backtester = MomentumBacktester(
            initial_qty=self.args.initial_qty,
            trade_unit_ratio=self.args.trade_ratio,
        )
        results = self._run_all(backtester, etf_codes)
        self._print_results(results, backtester)
        self._save_json(results)
        return 0

    def _get_user_etf_codes(self):
        """Get target user's ETF codes."""
        user = User.query.filter_by(username=self.args.user).first()
        if not user:
            return []
        rows = (
            Trade.query.filter_by(user_id=user.id)
            .with_entities(Trade.etf_code)
            .distinct()
            .all()
        )
        return sorted([r.etf_code for r in rows])

    def _get_top_etf_codes(self, top_n):
        """Get top N ETFs by recommendation score with sufficient momentum data.

        Selection criteria:
        1. Must have momentum_label data in etf_metrics_history
        2. Ranked by ScoreCache total_score (balance perspective)
        3. Falls back to momentum data count if no score data
        """
        from sqlalchemy import func

        # Get ETFs with momentum data and their record counts
        momentum_counts = (
            EtfMetricsHistory.query.filter(
                EtfMetricsHistory.momentum_label.isnot(None),
            )
            .with_entities(
                EtfMetricsHistory.etf_code,
                func.count(EtfMetricsHistory.id).label("cnt"),
            )
            .group_by(EtfMetricsHistory.etf_code)
            .having(func.count(EtfMetricsHistory.id) >= 20)
            .all()
        )
        if not momentum_counts:
            return []

        eligible_codes = {r.etf_code for r in momentum_counts}
        count_map = {r.etf_code: r.cnt for r in momentum_counts}

        # Try ScoreCache (balance perspective) for ranking
        scores = (
            ScoreCache.query.filter(
                ScoreCache.etf_code.in_(eligible_codes),
                ScoreCache.perspective == "balance",
                ScoreCache.total_score.isnot(None),
            )
            .order_by(ScoreCache.total_score.desc())
            .all()
        )

        if scores:
            ranked = [s.etf_code for s in scores][:top_n]
            self.logger.info(
                f"Selected top {len(ranked)} ETFs by recommendation score"
            )
            return sorted(ranked)

        # Fallback: rank by momentum data count
        ranked = sorted(
            eligible_codes, key=lambda c: count_map[c], reverse=True
        )[:top_n]
        self.logger.info(
            f"Selected top {len(ranked)} ETFs by momentum data count "
            "(no score data available)"
        )
        return sorted(ranked)

    def _run_all(self, backtester, etf_codes):
        """Run backtest for all ETFs."""
        results = []
        for code in etf_codes:
            self.logger.info(f"Processing {code}...")
            momentum_data = self._fetch_momentum(code)
            price_data, split_ratio = self._fetch_prices(code)
            result = backtester.run(code, momentum_data, price_data, split_ratio)
            results.append(result)
            self.logger.info(
                f"  {code}: {result['trading_days']} days, "
                f"PnL={result['total_pnl']:+,}"
            )
        return results

    def _fetch_momentum(self, etf_code):
        """Fetch momentum history for an ETF."""
        query = EtfMetricsHistory.query.filter(
            EtfMetricsHistory.etf_code == etf_code,
            EtfMetricsHistory.momentum_label.isnot(None),
        )
        if self.args.start:
            start_date = date.fromisoformat(self.args.start)
            query = query.filter(EtfMetricsHistory.date >= start_date)
        if self.args.end:
            end_date = date.fromisoformat(self.args.end)
            query = query.filter(EtfMetricsHistory.date <= end_date)
        records = query.order_by(EtfMetricsHistory.date.asc()).all()
        return [(r.date, r.momentum_label) for r in records]

    def _fetch_prices(self, etf_code):
        """Fetch price history as {date: close} dict with split adjustment.

        Split adjustment is applied to the full date range first,
        then the date filter is applied to preserve accuracy.

        Returns:
            tuple of (prices dict, total_split_ratio)
        """
        records = (
            PriceHistory.query.filter(PriceHistory.etf_code == etf_code)
            .order_by(PriceHistory.date.asc())
            .all()
        )
        prices = {r.date: float(r.close) for r in records}
        adjusted_prices, split_ratio = self._apply_split_adjustment(
            etf_code, prices
        )

        # Apply date filter after split adjustment
        if self.args.start:
            start_date = date.fromisoformat(self.args.start)
            adjusted_prices = {
                d: p for d, p in adjusted_prices.items() if d >= start_date
            }
        if self.args.end:
            end_date = date.fromisoformat(self.args.end)
            adjusted_prices = {
                d: p for d, p in adjusted_prices.items() if d <= end_date
            }

        return adjusted_prices, split_ratio

    def _apply_split_adjustment(self, etf_code, prices):
        """Apply stock split adjustments to price data.

        Divides pre-split prices by the split ratio so that all
        prices are on a consistent post-split basis.

        Returns:
            tuple of (adjusted prices dict, total_split_ratio)
        """
        splits = (
            StockSplit.query.filter(StockSplit.etf_code == etf_code)
            .order_by(StockSplit.split_date.asc())
            .all()
        )
        if not splits:
            return prices, 1.0

        total_split_ratio = 1.0
        for split in splits:
            ratio = float(split.ratio)
            total_split_ratio *= ratio
            for date_key in prices:
                if date_key < split.split_date:
                    prices[date_key] /= ratio

        return prices, total_split_ratio

    def _print_results(self, results, backtester):
        """Print formatted results to console."""
        trade_unit = backtester.trade_unit
        print()
        print("=" * 40)
        print("モメンタムレベル バックテスト結果")
        print("=" * 40)
        print(
            f"初期条件: 各銘柄{backtester.initial_qty}株、"
            f"レベル1段={trade_unit}株"
        )
        etf_codes = [r["etf_code"] for r in results]
        if self.args.etf:
            print(f"対象銘柄: {', '.join(etf_codes)}（手動指定）")
        elif self.args.top:
            print(f"対象銘柄: スコア上位{self.args.top}銘柄")
        else:
            print(f"対象銘柄: {self.args.user}ユーザー保有銘柄")
        if self.args.start or self.args.end:
            start_str = self.args.start or "（データ開始）"
            end_str = self.args.end or "（データ終了）"
            print(f"指定期間: {start_str} ~ {end_str}")

        for r in results:
            self._print_etf_result(r)

        self._print_summary(results, backtester)

    def _print_etf_result(self, r):
        """Print single ETF result."""
        print(f"\n--- {r['etf_code']} ---")
        print(
            f"期間: {r['period_start']} ~ {r['period_end']} "
            f"({r['trading_days']}営業日)"
        )
        print(f"初期投資額: {r['initial_investment']:,}円")
        print(f"売買回数: 買い {r['buy_count']}回 / 売り {r['sell_count']}回")
        print(f"保有数: {r['initial_qty']}株 -> {r['final_qty']}株")
        print(f"確定損益: {r['realized_pnl']:+,}円")
        print(f"評価損益: {r['unrealized_pnl']:+,}円")
        print(
            f"合計損益: {r['total_pnl']:+,}円 "
            f"({r['total_pnl_pct']:+.1f}%)"
        )
        print(
            f"Buy&Hold: {r['buy_and_hold_pnl']:+,}円 "
            f"({r['buy_and_hold_pct']:+.1f}%)"
        )
        print(f"超過リターン: {r['excess_return_pct']:+.1f}%")

    def _print_summary(self, results, backtester):
        """Print overall summary."""
        total_pnl = sum(r["total_pnl"] for r in results)
        total_bh = sum(r["buy_and_hold_pnl"] for r in results)
        total_initial = sum(r["initial_investment"] for r in results)
        pnl_pct = round(total_pnl / total_initial * 100, 1) if total_initial else 0
        bh_pct = round(total_bh / total_initial * 100, 1) if total_initial else 0

        print(f"\n--- 全体サマリー ---")
        print(f"初期投資額合計: {total_initial:,}円")
        print(f"合計損益: {total_pnl:+,}円 ({pnl_pct:+.1f}%)")
        print(f"Buy&Hold合計: {total_bh:+,}円 ({bh_pct:+.1f}%)")
        print(f"超過リターン: {pnl_pct - bh_pct:+.1f}%")

    def _save_json(self, results):
        """Save results to JSON file."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = OUTPUT_DIR / f"backtest_momentum_{timestamp}.json"

        # Remove trades detail for summary JSON
        output = {
            "generated_at": datetime.now().isoformat(),
            "results": results,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Results saved to {filepath}")


if __name__ == "__main__":
    sys.exit(BacktestMomentumBatch().run())
