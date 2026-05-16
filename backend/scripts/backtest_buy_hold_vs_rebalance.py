#!/usr/bin/env python3
"""10-year backtest: Buy & Hold vs Quarterly Rebalance.

Compares 8 scenarios across 2 ETF groups, 2 allocation styles, 2 strategies.

Group A (Global): 2559 (All-Country), 1540 (Gold), 200A (Semiconductor)
Group B (Japan + commodity): 2646 (Base Metals), 1629 (Trading Cos),
                              1306 (TOPIX), 1615 (Banks)

Usage:
    python scripts/backtest_buy_hold_vs_rebalance.py
    python scripts/backtest_buy_hold_vs_rebalance.py --single-etf 1306
    python scripts/backtest_buy_hold_vs_rebalance.py --group A --strategy rebalance
"""
import argparse
import csv
import logging
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- env bootstrap (production friendly) ---
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

from src.app import create_app  # noqa: E402
from src.models.price_history import PriceHistory  # noqa: E402
from src.models.stock_split import StockSplit  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backtest_bhvr")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class BacktestConfig:
    """Static configuration for the 8-case backtest."""

    group_a_codes: List[str] = field(
        default_factory=lambda: ["2559", "1540", "200A"]
    )
    group_b_codes: List[str] = field(
        default_factory=lambda: ["1306", "1629", "1615", "2646"]
    )
    core_satellite_a: Dict[str, float] = field(
        default_factory=lambda: {"2559": 0.50, "1540": 0.30, "200A": 0.20}
    )
    core_satellite_b: Dict[str, float] = field(
        default_factory=lambda: {
            "1306": 0.50,
            "1629": 0.20,
            "1615": 0.20,
            "2646": 0.10,
        }
    )
    initial_capital: float = 1_000_000.0
    start_date: date = date(2015, 5, 12)
    end_date: date = date(2026, 5, 12)
    risk_free_rate: float = 0.0
    rebalance_tolerance: float = 1e-4  # 0.01 %
    value_tolerance: float = 5e-3  # 0.5 %

    def all_codes(self) -> List[str]:
        return self.group_a_codes + self.group_b_codes

    def equal_weights(self, codes: List[str]) -> Dict[str, float]:
        """Equal weights with rounding remainder absorbed by last code."""
        n = len(codes)
        base = round(1.0 / n, 6)
        weights = {c: base for c in codes[:-1]}
        weights[codes[-1]] = round(1.0 - sum(weights.values()), 6)
        return weights

    def weights_for(
        self, group: str, allocation: str, codes: Optional[List[str]] = None
    ) -> Dict[str, float]:
        if codes is None:
            codes = self.group_a_codes if group == "A" else self.group_b_codes
        if allocation == "equal":
            return self.equal_weights(codes)
        if allocation == "core_satellite":
            if group == "A":
                return dict(self.core_satellite_a)
            return dict(self.core_satellite_b)
        raise ValueError(f"unknown allocation: {allocation}")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_price_data(
    codes: List[str], start: date, end: date
) -> Dict[str, Dict[date, float]]:
    """Load price history per code, after applying chart-applied splits.

    Returns:
        {code: {date: adjusted_close}} restricted to [start, end].
    """
    result: Dict[str, Dict[date, float]] = {}
    for code in codes:
        recs = (
            PriceHistory.query.filter(PriceHistory.etf_code == code)
            .order_by(PriceHistory.date.asc())
            .all()
        )
        prices = {r.date: float(r.close) for r in recs}
        if not prices:
            logger.warning("no price data for %s", code)
            result[code] = {}
            continue

        splits = (
            StockSplit.query.filter(
                StockSplit.etf_code == code,
                StockSplit.is_chart_applied.is_(True),
            )
            .order_by(StockSplit.split_date.asc())
            .all()
        )
        # apply: pre-split dates divided by cumulative ratio
        for d in list(prices.keys()):
            cumulative = 1.0
            for s in splits:
                if d < s.split_date:
                    cumulative *= float(s.ratio)
            if cumulative != 1.0:
                prices[d] = prices[d] / cumulative

        filtered = {d: p for d, p in prices.items() if start <= d <= end}
        result[code] = filtered
        logger.info(
            "loaded %s: %d days (after %s, before %s, splits=%d)",
            code,
            len(filtered),
            start,
            end,
            len(splits),
        )
    return result


def build_business_calendar(
    price_map: Dict[str, Dict[date, float]],
    start: date,
    end: date,
) -> List[date]:
    """Union of all observed dates across ETFs, sorted."""
    dates = set()
    for d_map in price_map.values():
        dates.update(d_map.keys())
    return sorted(d for d in dates if start <= d <= end)


def listing_date_map(price_map: Dict[str, Dict[date, float]]) -> Dict[str, date]:
    listings: Dict[str, date] = {}
    for code, d_map in price_map.items():
        if d_map:
            listings[code] = min(d_map.keys())
    return listings


def compute_quarter_end_dates(calendar: List[date]) -> List[date]:
    """Return last trading day of each quarter (Mar/Jun/Sep/Dec) in calendar."""
    if not calendar:
        return []
    targets = {3, 6, 9, 12}
    result: List[date] = []
    by_ym: Dict[Tuple[int, int], List[date]] = {}
    for d in calendar:
        if d.month in targets:
            by_ym.setdefault((d.year, d.month), []).append(d)
    for key in sorted(by_ym.keys()):
        result.append(max(by_ym[key]))
    return result


def forward_fill_prices(
    price_map: Dict[str, Dict[date, float]], calendar: List[date]
) -> Dict[str, Dict[date, float]]:
    """For each ETF, forward-fill missing dates after listing."""
    filled: Dict[str, Dict[date, float]] = {}
    for code, d_map in price_map.items():
        if not d_map:
            filled[code] = {}
            continue
        listed = min(d_map.keys())
        filled_map: Dict[date, float] = {}
        last_price: Optional[float] = None
        for d in calendar:
            if d < listed:
                continue
            if d in d_map:
                last_price = d_map[d]
            if last_price is not None:
                filled_map[d] = last_price
        filled[code] = filled_map
    return filled


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------


@dataclass
class CaseSpec:
    case_id: str
    group: str  # "A" or "B"
    allocation: str  # "equal" or "core_satellite"
    strategy: str  # "buy_hold" or "rebalance" or "hybrid_b{n}"
    codes: List[str]
    target_weights: Dict[str, float]
    band: Optional[float] = None  # hybrid: |w_i - t_i| threshold; None=disabled
    restore_fraction: float = 0.70  # hybrid: partial-restore factor of band


class PortfolioSimulator:
    """Simulates one case end-to-end and records events."""

    def __init__(
        self,
        config: BacktestConfig,
        spec: CaseSpec,
        prices: Dict[str, Dict[date, float]],
        calendar: List[date],
        listings: Dict[str, date],
        rebalance_dates: List[date],
    ):
        self.config = config
        self.spec = spec
        self.prices = prices
        self.calendar = calendar
        self.listings = listings
        self.rebalance_set = set(rebalance_dates)
        self.cash: float = 0.0
        self.qty: Dict[str, int] = {c: 0 for c in spec.codes}
        self.equity_curve: List[Tuple[date, float]] = []
        self.events: List[Dict] = []
        self.rebalance_count: int = 0
        self.band_rebalance_count: int = 0
        self.listing_event_count: int = 0
        # canonical sequence of rebalance/listing/initial events as (date, type)
        self._assert_failures: List[str] = []

    # -- helpers --------------------------------------------------------

    def _listed_codes(self, today: date) -> List[str]:
        return [
            c
            for c in self.spec.codes
            if c in self.listings and self.listings[c] <= today
        ]

    def _renormalize_weights(self, listed: List[str]) -> Dict[str, float]:
        active = {c: self.spec.target_weights[c] for c in listed}
        total = sum(active.values())
        if total <= 0:
            return {}
        return {c: w / total for c, w in active.items()}

    def _current_value(self, today: date) -> float:
        value = self.cash
        for c, q in self.qty.items():
            if q == 0:
                continue
            p = self.prices.get(c, {}).get(today)
            if p is None:
                continue
            value += q * p
        return value

    def _apply_target(
        self, today: date, event_type: str, weights: Dict[str, float]
    ) -> None:
        """Liquidate-to-cash then allocate to `weights` (assumed sum~1.0).

        Core of rebalance/partial-rebalance: preserves asserts, event log
        and counter increments. `weights` must already be renormalized.
        """
        # assert: target weights sum to 1.0 (renormalization correctness)
        target_sum = sum(weights.values())
        if abs(target_sum - 1.0) > self.config.rebalance_tolerance:
            self._assert_failures.append(
                f"{today} {event_type} target_weight_sum={target_sum:.6f} (!=1.0)"
            )

        value_before = self._current_value(today)
        weights_before = self._weight_snapshot(today, value_before)

        # liquidate everything to cash
        new_cash = self.cash
        for c, q in self.qty.items():
            if q == 0:
                continue
            p = self.prices.get(c, {}).get(today)
            if p is None:
                continue
            new_cash += q * p
            self.qty[c] = 0
        # now allocate to target weights
        for c in self.spec.codes:
            self.qty[c] = 0
        for c, w in weights.items():
            target_yen = new_cash * w
            p = self.prices.get(c, {}).get(today)
            if p is None or p <= 0:
                continue
            q = math.floor(target_yen / p)
            self.qty[c] = q
        # actual cash leftover
        used = sum(self.qty[c] * self.prices[c][today] for c in weights)
        self.cash = new_cash - used

        value_after = self._current_value(today)
        # assert: total value approximately preserved (cost-free assumption)
        if value_before > 0:
            diff = abs(value_after - value_before) / value_before
            if diff > self.config.value_tolerance:
                self._assert_failures.append(
                    f"{today} {event_type} value drift={diff:.4%} "
                    f"before={value_before:.0f} after={value_after:.0f}"
                )

        weights_after = self._weight_snapshot(today, value_after)
        # assert: equity-only weights >= 1.0 - cash_share (sanity check).
        # Due to floor() share-rounding, leftover cash is typically <= max_price/value_after,
        # so equity weights sum to ~0.998..1.000. We don't fail on this — it is
        # the intended numerical noise floor of an integer-share simulator.

        if event_type == "rebalance":
            self.rebalance_count += 1
        elif event_type == "listing":
            self.listing_event_count += 1
        elif event_type == "band":
            self.band_rebalance_count += 1

        self.events.append(
            {
                "date": today.isoformat(),
                "case": self.spec.case_id,
                "event_type": event_type,
                "weights_before": _fmt_weights(weights_before),
                "weights_after": _fmt_weights(weights_after),
                "total_value": round(value_after, 0),
            }
        )

    def _rebalance(self, today: date, event_type: str) -> None:
        """Rebalance to target weights using all listed codes."""
        listed = self._listed_codes(today)
        if not listed:
            return
        weights = self._renormalize_weights(listed)
        self._apply_target(today, event_type, weights)

    def _partial_rebalance(
        self, today: date, band: float, restore_fraction: float
    ) -> None:
        """Threshold-triggered partial rebalance.

        Current weights use equity-only normalization (qty*price /
        Σ(qty*price)) to remove residual-cash bias. If max(|d_i|) > band
        for any listed asset (d_i = current - target), move each asset to
        n_i = t_i + clip(d_i, -band*rf, +band*rf), renormalized over listed
        codes, then apply via _apply_target with event_type "band".
        """
        listed = self._listed_codes(today)
        if not listed:
            return
        targets = self._renormalize_weights(listed)
        if not targets:
            return
        # equity-only current weights (exclude residual cash bias)
        equity_val: Dict[str, float] = {}
        total_equity = 0.0
        for c in listed:
            q = self.qty.get(c, 0)
            if q == 0:
                continue
            p = self.prices.get(c, {}).get(today)
            if p is None:
                continue
            v = q * p
            equity_val[c] = v
            total_equity += v
        if total_equity <= 0:
            return
        cur: Dict[str, float] = {
            c: equity_val.get(c, 0.0) / total_equity for c in listed
        }
        dev = {c: cur[c] - targets[c] for c in listed}
        max_abs_dev = max(abs(d) for d in dev.values())
        if max_abs_dev <= band:
            return
        lo, hi = -band * restore_fraction, band * restore_fraction
        new_w = {
            c: targets[c] + min(max(dev[c], lo), hi) for c in listed
        }
        s = sum(new_w.values())
        if s <= 0:
            return
        new_w = {c: w / s for c, w in new_w.items()}
        self._apply_target(today, "band", new_w)

    def _weight_snapshot(self, today: date, total: float) -> Dict[str, float]:
        if total <= 0:
            return {c: 0.0 for c in self.spec.codes}
        snap: Dict[str, float] = {}
        for c in self.spec.codes:
            p = self.prices.get(c, {}).get(today)
            if p is None or self.qty.get(c, 0) == 0:
                snap[c] = 0.0
            else:
                snap[c] = (self.qty[c] * p) / total
        # cash bucket implicit; we report code weights only
        return snap

    # -- main loop -------------------------------------------------------

    def run(self) -> Dict:
        """Execute the simulation. Returns case result dict."""
        # Determine first effective date (first calendar day on/after start_date
        # where at least one code has a price).
        first_day: Optional[date] = None
        for d in self.calendar:
            if any(
                d in self.prices.get(c, {}) for c in self.spec.codes
            ):
                first_day = d
                break
        if first_day is None:
            raise RuntimeError(f"no tradable day for case {self.spec.case_id}")

        # Initial allocation: cash = capital, then rebalance to listed codes.
        self.cash = self.config.initial_capital
        self._rebalance(first_day, "initial")
        # initial event is not counted as "rebalance_count"; correct here:
        if self.events and self.events[-1]["event_type"] == "initial":
            pass  # already handled (rebalance_count not incremented for initial)

        # We need _rebalance to differentiate initial; fix counter:
        # actually _rebalance increments only for "rebalance" or "listing".
        # "initial" doesn't increment either: good.

        prev_listed = set(self._listed_codes(first_day))
        self.equity_curve.append((first_day, self._current_value(first_day)))

        for d in self.calendar:
            if d <= first_day:
                continue
            # 1. listing event: any code now listed that wasn't before?
            current_listed = set(self._listed_codes(d))
            new_listings = current_listed - prev_listed
            if new_listings:
                self._rebalance(d, "listing")
                prev_listed = current_listed

            # 2. rebalance event (only on quarter ends, only for rebalance strategy)
            if (
                self.spec.strategy == "rebalance"
                and d in self.rebalance_set
                and current_listed
            ):
                # Skip if same date as initial (already balanced)
                if d != first_day:
                    self._rebalance(d, "rebalance")

            # 2b. hybrid strategy: quarter-end => full rebalance,
            #     otherwise threshold-triggered partial rebalance.
            if (
                self.spec.strategy.startswith("hybrid")
                and current_listed
                and d != first_day
            ):
                if d in self.rebalance_set:
                    self._rebalance(d, "rebalance")
                elif self.spec.band is not None:
                    self._partial_rebalance(
                        d, self.spec.band, self.spec.restore_fraction
                    )

            # 3. record equity
            value = self._current_value(d)
            self.equity_curve.append((d, value))

            # 4. coherence check: value == cash + Σ(qty * price)
            check = self.cash + sum(
                self.qty[c] * self.prices.get(c, {}).get(d, 0.0)
                for c in self.spec.codes
            )
            if abs(check - value) > 1e-6:
                self._assert_failures.append(
                    f"{d} value mismatch: {value:.4f} vs check {check:.4f}"
                )

        return {
            "case_id": self.spec.case_id,
            "group": self.spec.group,
            "allocation": self.spec.allocation,
            "strategy": self.spec.strategy,
            "equity_curve": self.equity_curve,
            "events": self.events,
            "rebalance_count": self.rebalance_count,
            "band_rebalance_count": self.band_rebalance_count,
            "listing_event_count": self.listing_event_count,
            "assert_failures": list(self._assert_failures),
        }


def _fmt_weights(w: Dict[str, float]) -> str:
    """Compact weight dict serializer."""
    items = sorted(w.items())
    return "; ".join(f"{c}:{v:.4f}" for c, v in items if v > 0)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class MetricsCalculator:
    """Compute total return / CAGR / volatility / Sharpe / MDD."""

    def __init__(self, risk_free_rate: float = 0.0):
        self.rf = risk_free_rate

    def compute(self, equity_curve: List[Tuple[date, float]]) -> Dict:
        if len(equity_curve) < 2:
            return {
                "total_return": 0.0,
                "cagr": 0.0,
                "vol": 0.0,
                "sharpe": 0.0,
                "mdd": 0.0,
                "mdd_peak": "",
                "mdd_trough": "",
                "start_value": 0.0,
                "end_value": 0.0,
            }
        start_val = equity_curve[0][1]
        end_val = equity_curve[-1][1]
        total_return = (end_val / start_val) - 1.0

        days = (equity_curve[-1][0] - equity_curve[0][0]).days
        years = days / 365.25 if days > 0 else 0.0
        cagr = (end_val / start_val) ** (1 / years) - 1 if years > 0 else 0.0

        # daily returns
        rets: List[float] = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1][1]
            curr = equity_curve[i][1]
            if prev > 0:
                rets.append(curr / prev - 1.0)
        if rets:
            mean = sum(rets) / len(rets)
            var = sum((r - mean) ** 2 for r in rets) / max(len(rets) - 1, 1)
            daily_std = math.sqrt(var)
        else:
            daily_std = 0.0
        ann_vol = daily_std * math.sqrt(252)
        sharpe = (cagr - self.rf) / ann_vol if ann_vol > 0 else 0.0

        # max drawdown
        peak = equity_curve[0][1]
        peak_date = equity_curve[0][0]
        mdd = 0.0
        mdd_peak: Optional[date] = None
        mdd_trough: Optional[date] = None
        running_peak = equity_curve[0][1]
        running_peak_date = equity_curve[0][0]
        for d, v in equity_curve:
            if v > running_peak:
                running_peak = v
                running_peak_date = d
            dd = (v - running_peak) / running_peak if running_peak > 0 else 0.0
            if dd < mdd:
                mdd = dd
                mdd_peak = running_peak_date
                mdd_trough = d
        return {
            "total_return": total_return,
            "cagr": cagr,
            "vol": ann_vol,
            "sharpe": sharpe,
            "mdd": mdd,
            "mdd_peak": mdd_peak.isoformat() if mdd_peak else "",
            "mdd_trough": mdd_trough.isoformat() if mdd_trough else "",
            "start_value": start_val,
            "end_value": end_val,
        }


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------


class ScenarioRunner:
    """Builds and runs all selected cases."""

    def __init__(
        self,
        config: BacktestConfig,
        prices: Dict[str, Dict[date, float]],
        calendar: List[date],
        listings: Dict[str, date],
        rebalance_dates: List[date],
    ):
        self.config = config
        self.prices = prices
        self.calendar = calendar
        self.listings = listings
        self.rebalance_dates = rebalance_dates
        self.metrics = MetricsCalculator(config.risk_free_rate)

    def build_specs(
        self,
        groups: List[str],
        allocations: List[str],
        strategies: List[str],
        single_etf: Optional[str] = None,
    ) -> List[CaseSpec]:
        if single_etf:
            # validate
            if single_etf not in self.prices or not self.prices[single_etf]:
                raise ValueError(f"no price data for {single_etf}")
            spec = CaseSpec(
                case_id=f"{single_etf}_single_bh",
                group="A" if single_etf in self.config.group_a_codes else "B",
                allocation="single",
                strategy="buy_hold",
                codes=[single_etf],
                target_weights={single_etf: 1.0},
            )
            return [spec]

        specs: List[CaseSpec] = []
        for g in groups:
            codes = (
                self.config.group_a_codes
                if g == "A"
                else self.config.group_b_codes
            )
            for alloc in allocations:
                weights = self.config.weights_for(g, alloc, codes)
                for strat in strategies:
                    case_id = f"{g}_{alloc}_{strat}"
                    specs.append(
                        CaseSpec(
                            case_id=case_id,
                            group=g,
                            allocation=alloc,
                            strategy=strat,
                            codes=list(codes),
                            target_weights=weights,
                        )
                    )
        return specs

    def run_all(self, specs: List[CaseSpec]) -> List[Dict]:
        results: List[Dict] = []
        for spec in specs:
            logger.info("running case: %s", spec.case_id)
            sim = PortfolioSimulator(
                self.config,
                spec,
                self.prices,
                self.calendar,
                self.listings,
                self.rebalance_dates,
            )
            case = sim.run()
            metrics = self.metrics.compute(case["equity_curve"])
            case.update(metrics)
            results.append(case)
            if case["assert_failures"]:
                for msg in case["assert_failures"]:
                    logger.warning("[assert] %s :: %s", spec.case_id, msg)
            logger.info(
                "  done %s: total_return=%.2f%% cagr=%.2f%% mdd=%.2f%% "
                "events=%d rebalances=%d",
                spec.case_id,
                metrics["total_return"] * 100,
                metrics["cagr"] * 100,
                metrics["mdd"] * 100,
                case["listing_event_count"],
                case["rebalance_count"],
            )
        return results


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


class ReportWriter:
    def __init__(
        self,
        config: BacktestConfig,
        results: List[Dict],
        output_dir: Path,
        listings: Dict[str, date],
    ):
        self.config = config
        self.results = results
        self.output_dir = output_dir
        self.listings = listings
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_summary_csv(self) -> Path:
        path = self.output_dir / "summary.csv"
        fields = [
            "case_id",
            "group",
            "allocation",
            "strategy",
            "total_return",
            "cagr",
            "vol",
            "sharpe",
            "mdd",
            "mdd_period",
            "rebalance_count",
            "listing_event_count",
            "start_value",
            "end_value",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(fields)
            for r in self.results:
                w.writerow(
                    [
                        r["case_id"],
                        r["group"],
                        r["allocation"],
                        r["strategy"],
                        f"{r['total_return']:.6f}",
                        f"{r['cagr']:.6f}",
                        f"{r['vol']:.6f}",
                        f"{r['sharpe']:.6f}",
                        f"{r['mdd']:.6f}",
                        f"{r['mdd_peak']}_to_{r['mdd_trough']}",
                        r["rebalance_count"],
                        r["listing_event_count"],
                        f"{r['start_value']:.0f}",
                        f"{r['end_value']:.0f}",
                    ]
                )
        return path

    def write_equity_curves_csv(self) -> Path:
        path = self.output_dir / "equity_curves.csv"
        # build matrix: union dates × cases
        all_dates: set = set()
        per_case: Dict[str, Dict[date, float]] = {}
        for r in self.results:
            m = {d: v for d, v in r["equity_curve"]}
            per_case[r["case_id"]] = m
            all_dates.update(m.keys())
        sorted_dates = sorted(all_dates)
        case_ids = [r["case_id"] for r in self.results]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date"] + case_ids)
            for d in sorted_dates:
                row = [d.isoformat()]
                for cid in case_ids:
                    v = per_case[cid].get(d)
                    row.append(f"{v:.2f}" if v is not None else "")
                w.writerow(row)
        return path

    def write_events_csv(self) -> Path:
        path = self.output_dir / "events.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "date",
                    "case",
                    "event_type",
                    "weights_before",
                    "weights_after",
                    "total_value",
                ]
            )
            for r in self.results:
                for e in r["events"]:
                    w.writerow(
                        [
                            e["date"],
                            e["case"],
                            e["event_type"],
                            e["weights_before"],
                            e["weights_after"],
                            e["total_value"],
                        ]
                    )
        return path

    def try_write_chart(self) -> Optional[Path]:
        try:
            import matplotlib  # type: ignore

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt  # type: ignore
        except Exception as e:
            logger.warning("matplotlib not available: %s — skipping chart", e)
            return None

        groups = {"A": [], "B": []}
        for r in self.results:
            if r["group"] in groups:
                groups[r["group"]].append(r)

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        for ax, (gname, group_results) in zip(axes, groups.items()):
            if not group_results:
                ax.set_title(f"Group {gname} (no data)")
                continue
            for r in group_results:
                dates = [d for d, _ in r["equity_curve"]]
                values = [v for _, v in r["equity_curve"]]
                ax.plot(dates, values, label=r["case_id"], linewidth=1.0)
            ax.set_title(f"Group {gname}: Equity Curves")
            ax.set_xlabel("date")
            ax.set_ylabel("portfolio value (JPY)")
            ax.legend(loc="upper left", fontsize=8)
            ax.grid(alpha=0.3)
        fig.tight_layout()
        path = self.output_dir / "equity_chart.png"
        fig.savefig(path, dpi=120)
        plt.close(fig)
        return path

    def write_report_md(self) -> Path:
        path = self.output_dir / "report.md"
        lines: List[str] = []
        lines.append("# 過去10年バックテスト: B&H vs 四半期リバランス")
        lines.append("")
        lines.append(
            f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append("")
        # Context
        lines.append("## 1. Context（背景・問い）")
        lines.append("")
        lines.append(
            "7銘柄ETFの長期保有戦略の優劣を実データで定量検証する。"
        )
        lines.append("")
        lines.append("1. 均等配分 と コア・サテライト型 のどちらが優位か")
        lines.append("2. バイ&ホールド と 四半期リバランス でリスク・リターンがどう変わるか")
        lines.append("")
        lines.append("## 2. 前提条件")
        lines.append("")
        lines.append(
            f"- 期間: {self.config.start_date} 〜 {self.config.end_date}"
        )
        lines.append(
            f"- 初期投資: {self.config.initial_capital:,.0f}円"
        )
        lines.append("- 売買コスト・税金・分配金: 無視")
        lines.append("- リスクフリーレート: 0%")
        lines.append("- 株式分割: `is_chart_applied=True` のみ補正")
        lines.append("- 上場前期間: 上場済み銘柄で比率再正規化、新規上場日に組入")
        lines.append("")
        lines.append("### 銘柄一覧と上場日")
        lines.append("")
        lines.append("| グループ | 銘柄 | 上場日（DB初出） |")
        lines.append("|----------|------|------------------|")
        for c in self.config.group_a_codes:
            ld = self.listings.get(c)
            lines.append(f"| A | {c} | {ld} |")
        for c in self.config.group_b_codes:
            ld = self.listings.get(c)
            lines.append(f"| B | {c} | {ld} |")
        lines.append("")

        # Per-group summary
        for gname in ("A", "B"):
            group_results = [
                r for r in self.results if r.get("group") == gname
            ]
            if not group_results:
                continue
            lines.append(f"## 3.{gname} {gname}群サマリ")
            lines.append("")
            lines.append(
                "| ケース | 配分 | 戦略 | 総リターン | CAGR | 年率Vol | Sharpe | MDD | リバランス回数 |"
            )
            lines.append(
                "|--------|------|------|-----------|------|---------|--------|-----|---------------|"
            )
            for r in group_results:
                lines.append(
                    "| {cid} | {al} | {st} | {tr:.2%} | {cg:.2%} | {vo:.2%} | {sh:.3f} | {md:.2%} | {rc} |".format(
                        cid=r["case_id"],
                        al=r["allocation"],
                        st=r["strategy"],
                        tr=r["total_return"],
                        cg=r["cagr"],
                        vo=r["vol"],
                        sh=r["sharpe"],
                        md=r["mdd"],
                        rc=r["rebalance_count"],
                    )
                )
            lines.append("")

        # Best / worst
        ranked = sorted(
            self.results, key=lambda r: r["total_return"], reverse=True
        )
        if ranked:
            best = ranked[0]
            worst = ranked[-1]
            lines.append("## 4. 最良 / 最悪ケース")
            lines.append("")
            lines.append(
                f"- 最良: **{best['case_id']}** (総リターン {best['total_return']:.2%}, "
                f"CAGR {best['cagr']:.2%}, Sharpe {best['sharpe']:.3f})"
            )
            lines.append(
                f"- 最悪: **{worst['case_id']}** (総リターン {worst['total_return']:.2%}, "
                f"CAGR {worst['cagr']:.2%}, Sharpe {worst['sharpe']:.3f})"
            )
            lines.append("")

        # Rebalance effect
        lines.append("## 5. リバランス効果の有無")
        lines.append("")
        lines.append(
            "同じ配分での Buy&Hold と Rebalance の差を見る:"
        )
        lines.append("")
        lines.append("| 群 | 配分 | B&H総リターン | Rebalance総リターン | 差分 | B&H Sharpe | Rebalance Sharpe |")
        lines.append("|---|------|---------------|---------------------|------|-----------|------------------|")
        for g in ("A", "B"):
            for alloc in ("equal", "core_satellite"):
                bh = next(
                    (
                        r
                        for r in self.results
                        if r.get("group") == g
                        and r.get("allocation") == alloc
                        and r.get("strategy") == "buy_hold"
                    ),
                    None,
                )
                rb = next(
                    (
                        r
                        for r in self.results
                        if r.get("group") == g
                        and r.get("allocation") == alloc
                        and r.get("strategy") == "rebalance"
                    ),
                    None,
                )
                if bh and rb:
                    lines.append(
                        "| {g} | {al} | {bh:.2%} | {rb:.2%} | {df:+.2%} | {bs:.3f} | {rs:.3f} |".format(
                            g=g,
                            al=alloc,
                            bh=bh["total_return"],
                            rb=rb["total_return"],
                            df=rb["total_return"] - bh["total_return"],
                            bs=bh["sharpe"],
                            rs=rb["sharpe"],
                        )
                    )
        lines.append("")

        # Market events consideration
        lines.append("## 6. 市場イベント考察")
        lines.append("")
        events_check = [
            (date(2020, 3, 19), "コロナショック底値圏"),
            (date(2022, 12, 20), "日銀YCC修正"),
            (date(2024, 8, 5), "令和ブラックマンデー"),
        ]
        for ev_date, ev_label in events_check:
            lines.append(f"### {ev_label}（{ev_date}）")
            lines.append("")
            lines.append("| ケース | 評価額 | 前営業日比 |")
            lines.append("|--------|--------|-----------|")
            for r in self.results:
                curve = r["equity_curve"]
                # find first day >= ev_date
                cur = next(((d, v) for d, v in curve if d >= ev_date), None)
                if cur is None:
                    continue
                # find prev day < ev_date
                prev_pairs = [(d, v) for d, v in curve if d < ev_date]
                prev = prev_pairs[-1] if prev_pairs else None
                cd, cv = cur
                if prev:
                    pd_, pv = prev
                    change = (cv - pv) / pv if pv > 0 else 0.0
                    lines.append(
                        f"| {r['case_id']} | {cv:,.0f} ({cd}) | {change:+.2%} |"
                    )
                else:
                    lines.append(f"| {r['case_id']} | {cv:,.0f} ({cd}) | (起点) |")
            lines.append("")

        # Listing events overview
        lines.append("## 7. 上場イベント記録")
        lines.append("")
        lines.append("| 銘柄 | 上場日 | 該当ケース数 |")
        lines.append("|------|--------|---------------|")
        listings_seen: Dict[str, int] = {}
        for r in self.results:
            for e in r["events"]:
                if e["event_type"] != "listing":
                    continue
                d = e["date"]
                # crude: count distinct cases per date
                listings_seen[d] = listings_seen.get(d, 0) + 1
        for d_str in sorted(listings_seen.keys()):
            lines.append(f"| (各群対象) | {d_str} | {listings_seen[d_str]} |")
        lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--group", choices=["A", "B", "both"], default="both")
    p.add_argument(
        "--allocation",
        choices=["equal", "core_satellite", "both"],
        default="both",
    )
    p.add_argument(
        "--strategy",
        choices=["buy_hold", "rebalance", "both"],
        default="both",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="output directory (default: reports/backtest/{ts}_buy_hold_vs_rebalance)",
    )
    p.add_argument(
        "--single-etf",
        type=str,
        default=None,
        help="run a single-ETF B&H backtest (validation)",
    )
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    config = BacktestConfig()

    # output dir.
    # Docker dev: ./reports is mounted at /app/reports (BACKEND_DIR/reports).
    # Production: ~/www/japan-etf-analyzer/reports lives next to backend/.
    # APP_BASE_DIR points to the right root in both cases when set, but
    # defaults to PROJECT_ROOT (= BACKEND_DIR.parent) above. We pick the
    # first reports/ that already exists, preferring the application root.
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        app_base = Path(os.environ.get("APP_BASE_DIR", str(PROJECT_ROOT)))
        candidate_roots = [
            app_base / "reports",
            BACKEND_DIR / "reports",
            PROJECT_ROOT / "reports",
        ]
        reports_root = next(
            (p for p in candidate_roots if p.is_dir()),
            candidate_roots[0],
        )
        output_dir = reports_root / "backtest" / f"{ts}_buy_hold_vs_rebalance"
    logger.info("output_dir: %s", output_dir)

    app = create_app()
    with app.app_context():
        all_codes = config.all_codes()
        raw_prices = load_price_data(all_codes, config.start_date, config.end_date)

    # build calendar from raw observed dates (union)
    calendar = build_business_calendar(
        raw_prices, config.start_date, config.end_date
    )
    listings = listing_date_map(raw_prices)
    prices = forward_fill_prices(raw_prices, calendar)
    rebalance_dates = compute_quarter_end_dates(calendar)
    logger.info(
        "calendar=%d days, quarter_ends=%d, listings=%s",
        len(calendar),
        len(rebalance_dates),
        {k: v.isoformat() for k, v in listings.items()},
    )

    runner = ScenarioRunner(
        config, prices, calendar, listings, rebalance_dates
    )

    # build specs
    if args.single_etf:
        specs = runner.build_specs(
            groups=[],
            allocations=[],
            strategies=[],
            single_etf=args.single_etf,
        )
    else:
        groups = ["A", "B"] if args.group == "both" else [args.group]
        allocs = (
            ["equal", "core_satellite"]
            if args.allocation == "both"
            else [args.allocation]
        )
        strats = (
            ["buy_hold", "rebalance"]
            if args.strategy == "both"
            else [args.strategy]
        )
        specs = runner.build_specs(groups, allocs, strats)

    results = runner.run_all(specs)

    # write outputs
    writer = ReportWriter(config, results, output_dir, listings)
    summary_path = writer.write_summary_csv()
    eq_path = writer.write_equity_curves_csv()
    ev_path = writer.write_events_csv()
    chart_path = writer.try_write_chart()
    report_path = writer.write_report_md()

    logger.info("=== outputs ===")
    logger.info("  summary.csv: %s", summary_path)
    logger.info("  equity_curves.csv: %s", eq_path)
    logger.info("  events.csv: %s", ev_path)
    if chart_path:
        logger.info("  equity_chart.png: %s", chart_path)
    else:
        logger.info("  equity_chart.png: SKIPPED (matplotlib unavailable)")
    logger.info("  report.md: %s", report_path)

    # global assertion summary
    total_failures = sum(len(r["assert_failures"]) for r in results)
    if total_failures:
        logger.warning(
            "[assert] total %d coherence violations across cases",
            total_failures,
        )
    else:
        logger.info("[assert] all coherence checks PASSED")

    # also print summary table to stdout for easy inspection
    print()
    print("=== SUMMARY ===")
    for r in results:
        print(
            f"{r['case_id']:30s} total={r['total_return']*100:7.2f}%  "
            f"cagr={r['cagr']*100:6.2f}%  vol={r['vol']*100:5.2f}%  "
            f"sharpe={r['sharpe']:6.3f}  mdd={r['mdd']*100:7.2f}%  "
            f"rebal={r['rebalance_count']:3d}  listings={r['listing_event_count']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
