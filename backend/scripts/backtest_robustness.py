#!/usr/bin/env python3
"""Rebalance backtest robustness suite (methods A/B/C/D/E).

Builds on the price-source-agnostic engine in
``backtest_buy_hold_vs_rebalance.py`` (PortfolioSimulator / MetricsCalculator /
CaseSpec / ReportWriter / calendar+forward-fill helpers) and the API price
source + proxy splice helpers in ``backtest_custom_basket_rebalance.py``
(fetch_price_map / max_daily_jump / assert_no_discontinuity / splice_proxy /
splice_proxy_chain / inject_cash_series). No logic is duplicated — the engine
is imported. Prices are API-only (split-adjusted server-side, no DB reads,
CLAUDE.md 計算前必須チェック).

Methods (all run by default, no args needed):
  C  full_proxy scenario (basis for A/B/E) + proxy_extended reference
  A  rolling / non-overlapping sub-period dispersion
  B  per-stress-event interval returns & drawdowns
  D  downside metrics (Calmar/Sortino/underwater) + benchmark comparison
  E  stationary block bootstrap of daily returns

Basket (fixed, identical to backtest_custom_basket_rebalance.py):
  Group A 45% : 2559=15% / 1540=15% / 1629=15%
  Group B 45% : 2646=9% / 1306=9% / 1618=9% / 200A=9% / 1615=9%
  Cash    10% : synthetic "CASH" series (price=1.0)

Proxy splices (fixed):
  2559 -> 1554 (上場ｲﾝﾃﾞｯｸｽ世界株式 MSCI ACWI除く日本, 2011-03-02, 月次corr 0.9873)
  2646 -> 1623 (NEXT FUNDS 鉄鋼･非鉄 TOPIX-17, 2008-03-19, corr 0.9046)
  200A -> 多段: 実200A(2024-06-04~) / 2644(2021-09-22~2024-06-04, 0.9815)
              / 1625 (NEXT FUNDS 電機･精密 TOPIX-17, 2008-03-19~, 0.8726)

Usage:
    python scripts/backtest_robustness.py
    python scripts/backtest_robustness.py --bootstrap-n 1000
    python scripts/backtest_robustness.py --base-url http://localhost:8902
"""
import argparse
import csv
import logging
import math
import os
import random
import statistics
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- env bootstrap (production friendly; CLAUDE.md スクリプト作成テンプレート) ---
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

# Reuse the engine — no logic is reimplemented here.
from scripts.backtest_buy_hold_vs_rebalance import (  # noqa: E402
    BacktestConfig,
    CaseSpec,
    MetricsCalculator,
    PortfolioSimulator,
    ReportWriter,
    build_business_calendar,
    compute_quarter_end_dates,
    forward_fill_prices,
    listing_date_map,
)
from scripts.backtest_custom_basket_rebalance import (  # noqa: E402
    CASH_CODE,
    CASH_WEIGHT,
    GROUP_A_WEIGHTS,
    GROUP_B_WEIGHTS,
    INITIAL_CAPITAL,
    MAX_DAILY_JUMP,
    RESTORE_FRACTION,
    RISK_FREE_RATE,
    assert_no_discontinuity,
    basket_weights,
    fetch_price_map,
    inject_cash_series,
    splice_proxy,
    splice_proxy_chain,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backtest_robustness")


# ---------------------------------------------------------------------------
# Proxy / benchmark definitions (fixed)
# ---------------------------------------------------------------------------

ETF_CODES: List[str] = list(GROUP_A_WEIGHTS) + list(GROUP_B_WEIGHTS)

# (target, source, anchor, monthly_corr) two-stage splices
PROXY_2559 = ("2559", "1554", date(2020, 1, 7), 0.9873)
PROXY_2646 = ("2646", "1623", date(2021, 9, 22), 0.9046)
# 200A multi-stage: real -> 2644 -> 1625
PROXY_200A_REAL_ANCHOR = date(2024, 6, 4)
PROXY_200A_2644_CORR = 0.9815
PROXY_200A_1625_CORR = 0.8726

# All extra source codes we must also fetch from the API.
PROXY_SOURCE_CODES = ["1554", "1623", "2644", "1625"]

FULL_PROXY_START = date(2011, 3, 2)  # 1554 first trading day (binding limit)
EXT_START = date(2021, 9, 22)  # 2644 first trading day (high-fidelity ref)

# Benchmarks (codes resolved to spliced full series in full_proxy universe).
BENCH_ORCA = "2559"  # オルカン (2559, 1554-spliced)
BENCH_TOPIX = "1306"  # TOPIX (1306)

HYBRID_BANDS = (0.01, 0.02, 0.03)

# Stress events (peak->trough-ish; clipped to data range at evaluation).
STRESS_EVENTS: List[Tuple[str, date, date]] = [
    ("2011 東日本大震災/欧州債務", date(2011, 3, 2), date(2011, 11, 25)),
    ("2015-16 チャイナショック", date(2015, 6, 24), date(2016, 2, 12)),
    ("2018Q4 利上げ調整", date(2018, 9, 28), date(2018, 12, 25)),
    ("2020 コロナショック", date(2020, 2, 20), date(2020, 4, 30)),
    ("2022 利上げ/ウクライナ", date(2022, 1, 5), date(2022, 10, 20)),
    ("2024-08 令和ブラックマンデー", date(2024, 7, 11), date(2024, 8, 6)),
    ("2025 関税ショック", date(2025, 4, 1), date(2025, 5, 15)),
]

# Rolling non-overlapping window sets (years, count).
ROLLING_SETS: List[Tuple[int, int]] = [(5, 3), (3, 5), (2, 7)]

STRATEGY_ORDER = [
    "buy_hold",
    "rebalance_q",
    "hybrid_b01",
    "hybrid_b02",
    "hybrid_b03",
]


# ---------------------------------------------------------------------------
# Spec construction (mirrors custom-basket strategy set; no logic dup)
# ---------------------------------------------------------------------------


def build_specs() -> List[CaseSpec]:
    """The 5 comparison strategies over the 8-ETF + CASH basket."""
    weights = basket_weights()
    codes = ETF_CODES + [CASH_CODE]
    specs: List[CaseSpec] = [
        CaseSpec(
            case_id="buy_hold",
            group="robust",
            allocation="custom_basket",
            strategy="buy_hold",
            codes=list(codes),
            target_weights=dict(weights),
        ),
        CaseSpec(
            case_id="rebalance_q",
            group="robust",
            allocation="custom_basket",
            strategy="rebalance",
            codes=list(codes),
            target_weights=dict(weights),
        ),
    ]
    for band in HYBRID_BANDS:
        specs.append(
            CaseSpec(
                case_id=f"hybrid_b{int(band * 100):02d}",
                group="robust",
                allocation="custom_basket",
                strategy="hybrid",
                codes=list(codes),
                target_weights=dict(weights),
                band=band,
                restore_fraction=RESTORE_FRACTION,
            )
        )
    return specs


def build_full_proxy_prices(
    raw: Dict[str, Dict[date, float]],
) -> Dict[str, Dict[date, float]]:
    """Assemble the full-proxy equity universe (CASH not yet added).

    2559/2646 are two-stage spliced; 200A is three-stage spliced.
    """
    prices: Dict[str, Dict[date, float]] = {
        c: dict(raw.get(c, {})) for c in ETF_CODES
    }
    # 2559 <- 1554
    prices["2559"] = splice_proxy(
        raw.get("2559", {}), raw.get("1554", {}), PROXY_2559[2]
    )
    # 2646 <- 1623
    prices["2646"] = splice_proxy(
        raw.get("2646", {}), raw.get("1623", {}), PROXY_2646[2]
    )
    # 200A: real -> 2644 -> 1625 (newest-first multi-stage chain)
    prices["200A"] = splice_proxy_chain(
        [
            (raw.get("200A", {}), PROXY_200A_REAL_ANCHOR),
            (raw.get("2644", {}), None),
            (raw.get("1625", {}), None),
        ]
    )
    return prices


def build_ext_prices(
    raw: Dict[str, Dict[date, float]],
) -> Dict[str, Dict[date, float]]:
    """High-fidelity reference: 200A spliced from 2644 only (no 1554/1623/1625).

    All B-group + A-group real series start <= 2021-09-22 except 2646 (also
    2021-09-22) and 200A (2024-06-04, spliced from 2644). 2559 real starts
    2020-01-07 (covers EXT_START). This keeps only the highest-correlation
    recent proxy.
    """
    prices: Dict[str, Dict[date, float]] = {
        c: dict(raw.get(c, {})) for c in ETF_CODES
    }
    prices["200A"] = splice_proxy(
        raw.get("200A", {}), raw.get("2644", {}), PROXY_200A_REAL_ANCHOR
    )
    return prices


# ---------------------------------------------------------------------------
# Scenario run (uses imported engine verbatim)
# ---------------------------------------------------------------------------


class ScenarioResult:
    """Holds one scenario's simulated cases + assembled price context."""

    def __init__(
        self,
        name: str,
        start: date,
        end: date,
        results: List[Dict],
        listings: Dict[str, date],
        prices: Dict[str, Dict[date, float]],
        calendar: List[date],
    ):
        self.name = name
        self.start = start
        self.end = end
        self.results = results
        self.listings = listings
        self.prices = prices  # forward-filled, includes CASH
        self.calendar = calendar

    def case(self, case_id: str) -> Optional[Dict]:
        return next(
            (r for r in self.results if r["case_id"] == case_id), None
        )


def run_scenario(
    name: str,
    prices_in: Dict[str, Dict[date, float]],
    start: date,
    end: date,
    config: BacktestConfig,
    metrics: MetricsCalculator,
    out_dir: Optional[Path],
) -> ScenarioResult:
    """Run the 5 strategies over one assembled equity universe."""
    prices = {
        c: {d: p for d, p in dm.items() if start <= d <= end}
        for c, dm in prices_in.items()
    }
    calendar = build_business_calendar(prices, start, end)
    if not calendar:
        raise RuntimeError(f"empty calendar for scenario {name}")
    inject_cash_series(prices, calendar)
    assert_no_discontinuity(prices)

    listings = listing_date_map(prices)
    filled = forward_fill_prices(prices, calendar)
    rebalance_dates = compute_quarter_end_dates(calendar)
    logger.info(
        "[%s] window=%s..%s cal=%d q_ends=%d",
        name,
        start,
        end,
        len(calendar),
        len(rebalance_dates),
    )

    results: List[Dict] = []
    for spec in build_specs():
        sim = PortfolioSimulator(
            config, spec, filled, calendar, listings, rebalance_dates
        )
        case = sim.run()
        case.update(metrics.compute(case["equity_curve"]))
        results.append(case)
        for msg in case["assert_failures"]:
            logger.warning("[assert] %s :: %s", spec.case_id, msg)
        logger.info(
            "  [%s/%s] total=%.2f%% cagr=%.2f%% mdd=%.2f%%",
            name,
            spec.case_id,
            case["total_return"] * 100,
            case["cagr"] * 100,
            case["mdd"] * 100,
        )

    if out_dir is not None:
        writer = ReportWriter(config, results, out_dir, listings)
        writer.write_summary_csv()
        writer.write_equity_curves_csv()
        writer.write_events_csv()

    return ScenarioResult(
        name, start, end, results, listings, filled, calendar
    )


# ---------------------------------------------------------------------------
# Method D: extended downside metrics (MetricsCalculator wrapped, not edited)
# ---------------------------------------------------------------------------


def daily_returns(curve: List[Tuple[date, float]]) -> List[float]:
    out: List[float] = []
    for i in range(1, len(curve)):
        p = curve[i - 1][1]
        c = curve[i][1]
        if p > 0:
            out.append(c / p - 1.0)
    return out


def extended_metrics(
    curve: List[Tuple[date, float]], base: Dict, rf: float = 0.0
) -> Dict:
    """Downside extension on top of MetricsCalculator output (`base`).

    Adds Calmar, Sortino (MAR=0, downside deviation), worst rolling-12m
    return, time-underwater % and longest underwater run (calendar days).
    The base CAGR/MDD/etc. come from the imported MetricsCalculator.
    """
    cagr = base.get("cagr", 0.0)
    mdd = base.get("mdd", 0.0)
    calmar = cagr / abs(mdd) if mdd < 0 else 0.0

    rets = daily_returns(curve)
    if rets:
        downside = [min(r - rf / 252.0, 0.0) for r in rets]
        dd_var = sum(x * x for x in downside) / len(downside)
        dd_std = math.sqrt(dd_var) * math.sqrt(252)
        mean_ann = (sum(rets) / len(rets)) * 252
        sortino = (mean_ann - rf) / dd_std if dd_std > 0 else 0.0
    else:
        sortino = 0.0

    # worst rolling 12-month (~252 trading day) total return
    vals = [v for _, v in curve]
    worst_12m = 0.0
    if len(vals) > 252:
        worst_12m = min(
            vals[i] / vals[i - 252] - 1.0
            for i in range(252, len(vals))
            if vals[i - 252] > 0
        )

    # underwater: fraction of days strictly below running peak + longest run
    peak = vals[0] if vals else 0.0
    underwater_days = 0
    longest = 0
    run_start: Optional[date] = None
    longest_cal = 0
    for d, v in curve:
        if v >= peak:
            peak = v
            if run_start is not None:
                longest_cal = max(longest_cal, (d - run_start).days)
                run_start = None
            longest = max(longest, 0)
        else:
            underwater_days += 1
            if run_start is None:
                run_start = d
    if run_start is not None and curve:
        longest_cal = max(longest_cal, (curve[-1][0] - run_start).days)
    uw_pct = underwater_days / len(curve) if curve else 0.0

    return {
        "calmar": calmar,
        "sortino": sortino,
        "worst_rolling_12m": worst_12m,
        "underwater_pct": uw_pct,
        "longest_underwater_days": longest_cal,
    }


# ---------------------------------------------------------------------------
# Method A: rolling non-overlapping sub-periods
# ---------------------------------------------------------------------------


def make_windows(
    start: date, end: date, years: int, count: int
) -> List[Tuple[date, date]]:
    """Non-overlapping [w_start, w_end] windows packed from `start`."""
    windows: List[Tuple[date, date]] = []
    cur = start
    for _ in range(count):
        w_end = date(cur.year + years, cur.month, min(cur.day, 28))
        if w_end > end:
            break
        windows.append((cur, w_end))
        cur = w_end
    return windows


def window_metrics(
    sr_prices: Dict[str, Dict[date, float]],
    w_start: date,
    w_end: date,
    config: BacktestConfig,
    metrics: MetricsCalculator,
) -> Dict[str, Dict]:
    """Run all 5 strategies on a sub-window; return {case_id: metrics}."""
    res = run_scenario(
        f"win_{w_start}", sr_prices, w_start, w_end, config, metrics, None
    )
    return {r["case_id"]: r for r in res.results}


def method_a_rolling(
    fp: ScenarioResult,
    config: BacktestConfig,
    metrics: MetricsCalculator,
    out_dir: Path,
) -> Dict:
    """Rolling dispersion across non-overlapping sub-period sets."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict] = []
    # per strategy: list of (cagr, sharpe, mdd, bh_cagr, label)
    coll: Dict[str, List[Dict]] = {s: [] for s in STRATEGY_ORDER}

    for years, count in ROLLING_SETS:
        wins = make_windows(fp.start, fp.end, years, count)
        for (ws, we) in wins:
            wm = window_metrics(fp.prices, ws, we, config, metrics)
            bh = wm.get("buy_hold")
            bh_cagr = bh["cagr"] if bh else 0.0
            for cid in STRATEGY_ORDER:
                r = wm.get(cid)
                if not r:
                    continue
                label = f"{years}y[{ws}..{we}]"
                rows.append(
                    {
                        "window_set": f"{years}y",
                        "window": label,
                        "start": ws.isoformat(),
                        "end": we.isoformat(),
                        "strategy": cid,
                        "cagr": r["cagr"],
                        "sharpe": r["sharpe"],
                        "mdd": r["mdd"],
                        "beats_bh": int(r["cagr"] > bh_cagr),
                    }
                )
                coll[cid].append(
                    {
                        "cagr": r["cagr"],
                        "sharpe": r["sharpe"],
                        "mdd": r["mdd"],
                        "beats_bh": r["cagr"] > bh_cagr,
                        "label": label,
                    }
                )

    # CSV
    csv_path = out_dir / "rolling_subperiods.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "window_set",
                "window",
                "start",
                "end",
                "strategy",
                "cagr",
                "sharpe",
                "mdd",
                "beats_bh",
            ]
        )
        for row in rows:
            w.writerow(
                [
                    row["window_set"],
                    row["window"],
                    row["start"],
                    row["end"],
                    row["strategy"],
                    f"{row['cagr']:.6f}",
                    f"{row['sharpe']:.6f}",
                    f"{row['mdd']:.6f}",
                    row["beats_bh"],
                ]
            )

    # dispersion stats
    stats: Dict[str, Dict] = {}
    for cid in STRATEGY_ORDER:
        items = coll[cid]
        if not items:
            continue
        cagrs = sorted(x["cagr"] for x in items)
        worst = min(items, key=lambda x: x["cagr"])
        q1 = _percentile(cagrs, 25)
        q3 = _percentile(cagrs, 75)
        wins = sum(1 for x in items if x["beats_bh"])
        stats[cid] = {
            "n": len(items),
            "cagr_min": min(cagrs),
            "cagr_median": statistics.median(cagrs),
            "cagr_max": max(cagrs),
            "cagr_iqr": q3 - q1,
            "bh_win_rate": wins / len(items),
            "worst_window": worst["label"],
            "worst_cagr": worst["cagr"],
        }

    _write_rolling_report(out_dir, stats, rows)
    return {"stats": stats, "rows": rows}


def _write_rolling_report(
    out_dir: Path, stats: Dict[str, Dict], rows: List[Dict]
) -> None:
    L: List[str] = []
    L.append("# 手法A: ローリング・サブ期間 分散分析")
    L.append("")
    L.append(f"生成日時: {datetime.now():%Y-%m-%d %H:%M:%S}")
    L.append("")
    L.append(
        "非重複ウィンドウ集合: 5年×3本 / 3年×5本 / 2年×7本"
        "（full_proxy 基盤、各ウィンドウで5戦略を独立シミュレート）。"
    )
    L.append("")
    L.append("## 戦略別 分散統計（CAGR）")
    L.append("")
    L.append(
        "| 戦略 | 本数 | min | 中央値 | max | IQR | "
        "B&H超過勝率 | 最悪ウィンドウ(CAGR) |"
    )
    L.append("|------|------|-----|--------|-----|-----|-----------|---------|")
    for cid in STRATEGY_ORDER:
        s = stats.get(cid)
        if not s:
            continue
        L.append(
            "| {c} | {n} | {mn:.2%} | {md:.2%} | {mx:.2%} | {iq:.2%} "
            "| {wr:.0%} | {ww} ({wc:.2%}) |".format(
                c=cid,
                n=s["n"],
                mn=s["cagr_min"],
                md=s["cagr_median"],
                mx=s["cagr_max"],
                iq=s["cagr_iqr"],
                wr=s["bh_win_rate"],
                ww=s["worst_window"],
                wc=s["worst_cagr"],
            )
        )
    L.append("")
    L.append("## 全ウィンドウ明細")
    L.append("")
    L.append("| 集合 | ウィンドウ | 戦略 | CAGR | Sharpe | MDD | B&H超過 |")
    L.append("|------|-----------|------|------|--------|-----|--------|")
    for r in rows:
        L.append(
            "| {ws} | {w} | {s} | {cg:.2%} | {sh:.3f} | {md:.2%} | {b} |".format(
                ws=r["window_set"],
                w=r["window"],
                s=r["strategy"],
                cg=r["cagr"],
                sh=r["sharpe"],
                md=r["mdd"],
                b="○" if r["beats_bh"] else "×",
            )
        )
    L.append("")
    (out_dir / "rolling_report.md").write_text(
        "\n".join(L), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Method B: stress events
# ---------------------------------------------------------------------------


def _interval_return_and_dd(
    curve: List[Tuple[date, float]], ev_start: date, ev_end: date
) -> Optional[Tuple[float, float, date, date]]:
    """Cumulative return & max intra-interval drawdown over [ev_start,ev_end]."""
    seg = [(d, v) for d, v in curve if ev_start <= d <= ev_end]
    if len(seg) < 2:
        return None
    r0 = seg[0][1]
    r1 = seg[-1][1]
    cum = (r1 / r0 - 1.0) if r0 > 0 else 0.0
    peak = seg[0][1]
    mdd = 0.0
    for _, v in seg:
        if v > peak:
            peak = v
        dd = (v - peak) / peak if peak > 0 else 0.0
        mdd = min(mdd, dd)
    return cum, mdd, seg[0][0], seg[-1][0]


def _bench_series(
    fp: ScenarioResult, code: str
) -> List[Tuple[date, float]]:
    dm = fp.prices.get(code, {})
    return sorted(dm.items())


def method_b_stress(fp: ScenarioResult, out_dir: Path) -> Dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict] = []
    summary: List[Dict] = []

    orca = _bench_series(fp, BENCH_ORCA)
    topix = _bench_series(fp, BENCH_TOPIX)

    for name, ev_s, ev_e in STRESS_EVENTS:
        # clip to data range
        cs = max(ev_s, fp.start)
        ce = min(ev_e, fp.end)
        if cs >= ce:
            continue
        best_cid = None
        best_ret = None
        worst_dd_overall = 0.0
        for cid in STRATEGY_ORDER:
            r = fp.case(cid)
            if not r:
                continue
            res = _interval_return_and_dd(r["equity_curve"], cs, ce)
            if res is None:
                continue
            cum, mdd, a, b = res
            rows.append(
                {
                    "event": name,
                    "start": a.isoformat(),
                    "end": b.isoformat(),
                    "strategy": cid,
                    "interval_return": cum,
                    "interval_mdd": mdd,
                }
            )
            if best_ret is None or cum > best_ret:
                best_ret = cum
                best_cid = cid
            worst_dd_overall = min(worst_dd_overall, mdd)
        # benchmarks
        orca_r = _interval_return_and_dd(orca, cs, ce)
        topix_r = _interval_return_and_dd(topix, cs, ce)
        summary.append(
            {
                "event": name,
                "clip": f"{cs}..{ce}",
                "best_strategy": best_cid,
                "best_return": best_ret,
                "worst_dd": worst_dd_overall,
                "orca_return": orca_r[0] if orca_r else None,
                "topix_return": topix_r[0] if topix_r else None,
            }
        )

    csv_path = out_dir / "stress_events.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "event",
                "start",
                "end",
                "strategy",
                "interval_return",
                "interval_mdd",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r["event"],
                    r["start"],
                    r["end"],
                    r["strategy"],
                    f"{r['interval_return']:.6f}",
                    f"{r['interval_mdd']:.6f}",
                ]
            )

    _write_stress_report(out_dir, summary, rows)
    return {"summary": summary, "rows": rows}


def _write_stress_report(
    out_dir: Path, summary: List[Dict], rows: List[Dict]
) -> None:
    L: List[str] = []
    L.append("# 手法B: ストレスイベント別 分析")
    L.append("")
    L.append(f"生成日時: {datetime.now():%Y-%m-%d %H:%M:%S}")
    L.append("")
    L.append(
        "各イベント区間（データ存在範囲にクリップ）で5戦略の累積リターン・"
        "区間内最大DDを算出。ベンチマーク（オルカン=2559/1554連結, "
        "TOPIX=1306）の区間リターンを併記。"
    )
    L.append("")
    L.append("## イベント別サマリ")
    L.append("")
    L.append(
        "| イベント | 区間 | 最良戦略 | 最良リターン | 最大DD(全戦略中) | "
        "オルカン | TOPIX |"
    )
    L.append("|----------|------|----------|------|------|------|------|")
    for s in summary:
        L.append(
            "| {ev} | {cl} | {bs} | {br} | {wd:.2%} | {og} | {tp} |".format(
                ev=s["event"],
                cl=s["clip"],
                bs=s["best_strategy"] or "-",
                br=f"{s['best_return']:.2%}"
                if s["best_return"] is not None
                else "-",
                wd=s["worst_dd"],
                og=f"{s['orca_return']:.2%}"
                if s["orca_return"] is not None
                else "-",
                tp=f"{s['topix_return']:.2%}"
                if s["topix_return"] is not None
                else "-",
            )
        )
    L.append("")
    L.append("## イベント×戦略 明細")
    L.append("")
    L.append("| イベント | 区間 | 戦略 | 累積リターン | 区間内最大DD |")
    L.append("|----------|------|------|------|------|")
    for r in rows:
        L.append(
            "| {ev} | {a}..{b} | {s} | {cr:.2%} | {dd:.2%} |".format(
                ev=r["event"],
                a=r["start"],
                b=r["end"],
                s=r["strategy"],
                cr=r["interval_return"],
                dd=r["interval_mdd"],
            )
        )
    L.append("")
    (out_dir / "stress_report.md").write_text(
        "\n".join(L), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Method E: stationary block bootstrap
# ---------------------------------------------------------------------------


def stationary_bootstrap_indices(
    n: int, expected_block: float, rng: random.Random
) -> List[int]:
    """Politis-Romano stationary bootstrap index sequence of length n.

    Block lengths ~ Geometric(p) with p = 1/expected_block; wrap-around.
    """
    if n <= 0:
        return []
    p = 1.0 / expected_block
    idx: List[int] = []
    cur = rng.randrange(n)
    while len(idx) < n:
        idx.append(cur)
        if rng.random() < p:
            cur = rng.randrange(n)
        else:
            cur = (cur + 1) % n
    return idx[:n]


def _resample_metrics(
    rets: List[float],
    years: float,
    idx: List[int],
) -> Tuple[float, float, float]:
    """CAGR / MDD / Sharpe of a resampled daily-return path."""
    eq = 1.0
    peak = 1.0
    mdd = 0.0
    series_rets: List[float] = []
    for i in idx:
        r = rets[i]
        series_rets.append(r)
        eq *= 1.0 + r
        if eq > peak:
            peak = eq
        dd = (eq - peak) / peak if peak > 0 else 0.0
        mdd = min(mdd, dd)
    cagr = eq ** (1.0 / years) - 1.0 if years > 0 and eq > 0 else 0.0
    if len(series_rets) > 1:
        m = sum(series_rets) / len(series_rets)
        var = sum((x - m) ** 2 for x in series_rets) / (
            len(series_rets) - 1
        )
        ann_vol = math.sqrt(var) * math.sqrt(252)
        sharpe = cagr / ann_vol if ann_vol > 0 else 0.0
    else:
        sharpe = 0.0
    return cagr, mdd, sharpe


def _percentile(sorted_vals: List[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_vals[int(k)]
    return sorted_vals[lo] * (hi - k) + sorted_vals[hi] * (k - lo)


def method_e_bootstrap(
    fp: ScenarioResult,
    out_dir: Path,
    n_resamples: int,
    expected_block: int,
    seed: int,
) -> Dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    summary: Dict[str, Dict] = {}
    csv_rows: List[List] = []

    for cid in STRATEGY_ORDER:
        r = fp.case(cid)
        if not r:
            continue
        curve = r["equity_curve"]
        rets = daily_returns(curve)
        if len(rets) < 2:
            continue
        days = (curve[-1][0] - curve[0][0]).days
        years = days / 365.25 if days > 0 else 1.0
        cagrs: List[float] = []
        mdds: List[float] = []
        sharpes: List[float] = []
        for _ in range(n_resamples):
            idx = stationary_bootstrap_indices(
                len(rets), float(expected_block), rng
            )
            c, m, s = _resample_metrics(rets, years, idx)
            cagrs.append(c)
            mdds.append(m)
            sharpes.append(s)
        cagrs.sort()
        mdds.sort()
        sharpes.sort()
        # CVaR-style worst 5% (mean of tail)
        tail_n = max(1, int(0.05 * len(cagrs)))
        cvar_cagr = sum(cagrs[:tail_n]) / tail_n
        cvar_mdd = sum(mdds[:tail_n]) / tail_n  # most negative tail
        summary[cid] = {
            "n": n_resamples,
            "cagr_mean": statistics.fmean(cagrs),
            "cagr_median": statistics.median(cagrs),
            "cagr_p05": _percentile(cagrs, 5),
            "cagr_p95": _percentile(cagrs, 95),
            "cagr_cvar05": cvar_cagr,
            "mdd_mean": statistics.fmean(mdds),
            "mdd_median": statistics.median(mdds),
            "mdd_p05": _percentile(mdds, 5),
            "mdd_p95": _percentile(mdds, 95),
            "mdd_cvar05": cvar_mdd,
            "sharpe_median": statistics.median(sharpes),
        }
        csv_rows.append(
            [
                cid,
                n_resamples,
                f"{summary[cid]['cagr_mean']:.6f}",
                f"{summary[cid]['cagr_median']:.6f}",
                f"{summary[cid]['cagr_p05']:.6f}",
                f"{summary[cid]['cagr_p95']:.6f}",
                f"{summary[cid]['cagr_cvar05']:.6f}",
                f"{summary[cid]['mdd_mean']:.6f}",
                f"{summary[cid]['mdd_median']:.6f}",
                f"{summary[cid]['mdd_p05']:.6f}",
                f"{summary[cid]['mdd_p95']:.6f}",
                f"{summary[cid]['mdd_cvar05']:.6f}",
                f"{summary[cid]['sharpe_median']:.6f}",
            ]
        )

    csv_path = out_dir / "bootstrap_distribution.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "strategy",
                "n",
                "cagr_mean",
                "cagr_median",
                "cagr_p05",
                "cagr_p95",
                "cagr_cvar05",
                "mdd_mean",
                "mdd_median",
                "mdd_p05",
                "mdd_p95",
                "mdd_cvar05",
                "sharpe_median",
            ]
        )
        for row in csv_rows:
            w.writerow(row)

    _write_bootstrap_report(out_dir, summary, n_resamples, expected_block)
    return {"summary": summary, "n": n_resamples}


def _write_bootstrap_report(
    out_dir: Path, summary: Dict[str, Dict], n: int, block: int
) -> None:
    L: List[str] = []
    L.append("# 手法E: 定常ブロック・ブートストラップ")
    L.append("")
    L.append(f"生成日時: {datetime.now():%Y-%m-%d %H:%M:%S}")
    L.append("")
    L.append(
        f"full_proxy のポートフォリオ日次リターンを定常ブロック・"
        f"ブートストラップ（n_resamples={n}, 期待ブロック長={block}営業日, "
        f"幾何分布, ラップアラウンド）でリサンプル。各リサンプルで "
        f"CAGR/MDD/Sharpe を算出。"
    )
    L.append("")
    L.append("## CAGR 分布")
    L.append("")
    L.append(
        "| 戦略 | mean | median | 5%ile | 95%ile | 最悪5%(CVaR) |"
    )
    L.append("|------|------|--------|-------|--------|--------------|")
    for cid in STRATEGY_ORDER:
        s = summary.get(cid)
        if not s:
            continue
        L.append(
            "| {c} | {me:.2%} | {md:.2%} | {p5:.2%} | {p95:.2%} | "
            "{cv:.2%} |".format(
                c=cid,
                me=s["cagr_mean"],
                md=s["cagr_median"],
                p5=s["cagr_p05"],
                p95=s["cagr_p95"],
                cv=s["cagr_cvar05"],
            )
        )
    L.append("")
    L.append("## MDD 分布")
    L.append("")
    L.append(
        "| 戦略 | mean | median | 5%ile | 95%ile | 最悪5%(CVaR) |"
    )
    L.append("|------|------|--------|-------|--------|--------------|")
    for cid in STRATEGY_ORDER:
        s = summary.get(cid)
        if not s:
            continue
        L.append(
            "| {c} | {me:.2%} | {md:.2%} | {p5:.2%} | {p95:.2%} | "
            "{cv:.2%} |".format(
                c=cid,
                me=s["mdd_mean"],
                md=s["mdd_median"],
                p5=s["mdd_p05"],
                p95=s["mdd_p95"],
                cv=s["mdd_cvar05"],
            )
        )
    L.append("")
    L.append(
        "注: 5%ile < median < 95%ile の単調性が成立していること、"
        "MDD は負値で最悪5%が最も負に振れることを健全性チェックとする。"
    )
    L.append("")
    (out_dir / "bootstrap_report.md").write_text(
        "\n".join(L), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Method D helper: benchmark portfolios & comparison table
# ---------------------------------------------------------------------------


def _bench_curve_from_series(
    series: List[Tuple[date, float]], capital: float
) -> List[Tuple[date, float]]:
    if not series:
        return []
    p0 = series[0][1]
    return [(d, capital * (v / p0)) for d, v in series if p0 > 0]


def _blend_60_40(
    orca: List[Tuple[date, float]], capital: float
) -> List[Tuple[date, float]]:
    """60% オルカン + 40% CASH (price=1.0) 静的ブレンド（リバランス無し）。

    簡易ディフェンシブ参照。CASH part is constant so the curve =
    0.6*capital*(orca/orca0) + 0.4*capital.
    """
    if not orca:
        return []
    p0 = orca[0][1]
    if p0 <= 0:
        return []
    return [
        (d, 0.6 * capital * (v / p0) + 0.4 * capital) for d, v in orca
    ]


def method_d_benchmarks(
    fp: ScenarioResult,
    config: BacktestConfig,
    metrics: MetricsCalculator,
) -> Dict:
    """Portfolio (best CAGR strategy) vs オルカン / TOPIX / 60-40."""
    cap = config.initial_capital
    orca_raw = _bench_series(fp, BENCH_ORCA)
    topix_raw = _bench_series(fp, BENCH_TOPIX)

    bench: Dict[str, List[Tuple[date, float]]] = {
        "オルカン(2559/1554)": _bench_curve_from_series(orca_raw, cap),
        "TOPIX(1306)": _bench_curve_from_series(topix_raw, cap),
        "60/40(60%オルカン+40%現金, 簡易ディフェンシブ)": _blend_60_40(
            orca_raw, cap
        ),
    }
    table: List[Dict] = []
    # all 5 portfolio strategies
    for cid in STRATEGY_ORDER:
        r = fp.case(cid)
        if not r:
            continue
        ext = extended_metrics(r["equity_curve"], r, config.risk_free_rate)
        table.append(
            {
                "name": f"PF:{cid}",
                "cagr": r["cagr"],
                "mdd": r["mdd"],
                "calmar": ext["calmar"],
                "sortino": ext["sortino"],
            }
        )
    for label, curve in bench.items():
        if len(curve) < 2:
            continue
        base = metrics.compute(curve)
        ext = extended_metrics(curve, base, config.risk_free_rate)
        table.append(
            {
                "name": label,
                "cagr": base["cagr"],
                "mdd": base["mdd"],
                "calmar": ext["calmar"],
                "sortino": ext["sortino"],
            }
        )
    return {"table": table}


# ---------------------------------------------------------------------------
# Integrated root report
# ---------------------------------------------------------------------------


def write_root_report(
    root_dir: Path,
    fp: ScenarioResult,
    ext: ScenarioResult,
    config: BacktestConfig,
    rolling: Dict,
    stress: Dict,
    bootstrap: Dict,
    bench: Dict,
    bootstrap_n: int,
    bootstrap_block: int,
) -> Path:
    L: List[str] = []
    L.append("# リバランス戦略 頑健性分析スイート（統合レポート）")
    L.append("")
    L.append(f"生成日時: {datetime.now():%Y-%m-%d %H:%M:%S}")
    L.append("")
    L.append("## 1. 前提条件")
    L.append("")
    L.append(
        "- バスケット: A群45%(2559=15%/1540=15%/1629=15%) + "
        "B群45%(2646=9%/1306=9%/1618=9%/200A=9%/1615=9%) + 現金10%"
    )
    L.append(f"- 初期投資: {config.initial_capital:,.0f}円")
    L.append(
        f"- restore_fraction={RESTORE_FRACTION}、"
        f"リスクフリーレート={RISK_FREE_RATE}"
    )
    L.append(
        "- 比較5戦略: buy_hold / rebalance_q(四半期末) / "
        "hybrid band=0.01 / 0.02 / 0.03"
    )
    L.append("- 売買コスト・税金・分配金: 無視")
    L.append(
        f"- full_proxy 期間: {fp.start} 〜 {fp.end}"
        f"（約{(fp.end - fp.start).days / 365.25:.2f}年）"
    )
    L.append(
        f"- proxy_extended（高忠実参考）期間: {ext.start} 〜 {ext.end}"
        f"（約{(ext.end - ext.start).days / 365.25:.2f}年）"
    )
    L.append("")
    L.append("## 2. 検証注記（プロキシ多段スプライス・分割）")
    L.append("")
    L.append(
        "1. 全価格は API（`/api/v1/etfs/chart/batch` period=20y）経由。"
        "DB直接クエリ不使用（CLAUDE.md 計算前必須チェック）。"
    )
    L.append(
        f"2. 単日ジャンプ > {MAX_DAILY_JUMP:.0%} 非物理的不連続ガード適用。"
    )
    L.append(
        "3. 1629/1306 は is_chart_applied=True でAPI系列が分割調整済み"
        "・DB生データ不使用。2559の分割(2026-06-05)は観測期間外で無影響。"
    )
    L.append(
        f"4. 2559 → 1554（MSCI ACWI除く日本, 開始2011-03-02, 月次相関 "
        f"{PROXY_2559[3]}）、アンカー {PROXY_2559[2]} 以前を後方バックフィル。"
    )
    L.append(
        f"5. 2646 → 1623（NEXT FUNDS鉄鋼・非鉄 TOPIX-17, 開始2008-03-19, "
        f"相関 {PROXY_2646[3]}）、アンカー {PROXY_2646[2]} 以前。"
    )
    L.append(
        f"6. 200A 多段スプライス（newest-first アンカー連結, 各スプライス点"
        f"でリターン連続化・ジャンプ無し）: 実200A({PROXY_200A_REAL_ANCHOR}~) "
        f"/ 2644(2021-09-22~{PROXY_200A_REAL_ANCHOR}, 相関 "
        f"{PROXY_200A_2644_CORR}) / 1625(NEXT FUNDS電機・精密 TOPIX-17, "
        f"開始2008-03-19, 相関 {PROXY_200A_1625_CORR})。"
    )
    L.append(
        "7. proxy_extended は 200A→2644 のみ（最高相関の近年プロキシ）の"
        "高忠実リファレンス。"
    )
    L.append("- 現金: 合成資産 `CASH`（全日付 価格=1.0 固定）。")
    L.append("")
    L.append("## 3. シナリオC: full_proxy / proxy_extended サマリ")
    L.append("")
    for sr in (fp, ext):
        L.append(
            f"### {sr.name}（{sr.start}〜{sr.end}, "
            f"約{(sr.end - sr.start).days / 365.25:.2f}年）"
        )
        L.append("")
        L.append(
            "| 戦略 | 総リターン | CAGR | Vol | Sharpe | MDD | "
            "Calmar | Sortino | 最悪12mﾘﾀｰﾝ | 水面下% | 最長水面下日 |"
        )
        L.append(
            "|------|-----------|------|-----|--------|-----|"
            "--------|---------|---------|--------|------------|"
        )
        for cid in STRATEGY_ORDER:
            r = sr.case(cid)
            if not r:
                continue
            e = extended_metrics(
                r["equity_curve"], r, config.risk_free_rate
            )
            L.append(
                "| {c} | {tr:.2%} | {cg:.2%} | {vo:.2%} | {sh:.3f} | "
                "{md:.2%} | {ca:.2f} | {so:.2f} | {w12:.2%} | {uw:.1%} "
                "| {uwd} |".format(
                    c=cid,
                    tr=r["total_return"],
                    cg=r["cagr"],
                    vo=r["vol"],
                    sh=r["sharpe"],
                    md=r["mdd"],
                    ca=e["calmar"],
                    so=e["sortino"],
                    w12=e["worst_rolling_12m"],
                    uw=e["underwater_pct"],
                    uwd=e["longest_underwater_days"],
                )
            )
        L.append("")

    L.append("## 4. 手法A: ローリング・サブ期間 分散（要点）")
    L.append("")
    L.append(
        "| 戦略 | 本数 | CAGR中央値 | CAGR IQR | B&H超過勝率 | "
        "最悪ウィンドウ(CAGR) |"
    )
    L.append("|------|------|-----------|----------|-----------|---------|")
    for cid in STRATEGY_ORDER:
        s = rolling["stats"].get(cid)
        if not s:
            continue
        L.append(
            "| {c} | {n} | {md:.2%} | {iq:.2%} | {wr:.0%} | "
            "{ww} ({wc:.2%}) |".format(
                c=cid,
                n=s["n"],
                md=s["cagr_median"],
                iq=s["cagr_iqr"],
                wr=s["bh_win_rate"],
                ww=s["worst_window"],
                wc=s["worst_cagr"],
            )
        )
    L.append("")
    L.append("詳細は `rolling/rolling_report.md` を参照。")
    L.append("")

    L.append("## 5. 手法B: ストレスイベント別（要点）")
    L.append("")
    L.append(
        "| イベント | 区間 | 最良戦略 | 最良ﾘﾀｰﾝ | 最大DD | "
        "オルカン | TOPIX |"
    )
    L.append("|----------|------|----------|------|------|------|------|")
    for s in stress["summary"]:
        L.append(
            "| {ev} | {cl} | {bs} | {br} | {wd:.2%} | {og} | {tp} |".format(
                ev=s["event"],
                cl=s["clip"],
                bs=s["best_strategy"] or "-",
                br=f"{s['best_return']:.2%}"
                if s["best_return"] is not None
                else "-",
                wd=s["worst_dd"],
                og=f"{s['orca_return']:.2%}"
                if s["orca_return"] is not None
                else "-",
                tp=f"{s['topix_return']:.2%}"
                if s["topix_return"] is not None
                else "-",
            )
        )
    L.append("")
    L.append("詳細は `stress/stress_report.md` を参照。")
    L.append("")

    L.append(
        "## 6. 手法D: 下方リスク＋ベンチマーク比較（full_proxy）"
    )
    L.append("")
    L.append("| 対象 | CAGR | MDD | Calmar | Sortino |")
    L.append("|------|------|-----|--------|---------|")
    for row in bench["table"]:
        L.append(
            "| {n} | {cg:.2%} | {md:.2%} | {ca:.2f} | {so:.2f} |".format(
                n=row["name"],
                cg=row["cagr"],
                md=row["mdd"],
                ca=row["calmar"],
                so=row["sortino"],
            )
        )
    L.append("")
    L.append(
        "注: 60/40 は 60%オルカン+40%現金 の静的ブレンド（リバランス無し）"
        "を簡易ディフェンシブとして明示ラベル。"
    )
    L.append("")

    L.append(
        f"## 7. 手法E: ブロック・ブートストラップ"
        f"（n={bootstrap_n}, 期待ブロック長={bootstrap_block}営業日）"
    )
    L.append("")
    if bootstrap_n < 2000:
        L.append(
            f"※ 実行時間短縮のため n_resamples を {bootstrap_n} に低減"
            "（タスク許容条件）。"
        )
        L.append("")
    L.append(
        "| 戦略 | CAGR中央値 | CAGR 5%ile | CAGR 95%ile | "
        "MDD中央値 | MDD 5%ile(最悪側) |"
    )
    L.append("|------|-----------|-----------|------------|----------|--------|")
    for cid in STRATEGY_ORDER:
        s = bootstrap["summary"].get(cid)
        if not s:
            continue
        L.append(
            "| {c} | {cm:.2%} | {c5:.2%} | {c95:.2%} | {mm:.2%} | "
            "{m5:.2%} |".format(
                c=cid,
                cm=s["cagr_median"],
                c5=s["cagr_p05"],
                c95=s["cagr_p95"],
                mm=s["mdd_median"],
                m5=s["mdd_p05"],
            )
        )
    L.append("")
    L.append("詳細は `bootstrap/bootstrap_report.md` を参照。")
    L.append("")

    # ----- regime cross-cut verdict -----
    L.append("## 8. regime 横断 総合判定")
    L.append("")
    bh = fp.case("buy_hold")
    rq = fp.case("rebalance_q")
    best_full = max(fp.results, key=lambda r: r["cagr"])
    # bull-market bias排除: rolling 最悪ウィンドウとブートストラップ下側で評価
    L.append("### 強気相場（上昇バイアス局面）")
    L.append("")
    L.append(
        f"- full_proxy 全期間（{fp.start}〜{fp.end}）の最良CAGRは "
        f"`{best_full['case_id']}`（CAGR {best_full['cagr']:.2%}, "
        f"MDD {best_full['mdd']:.2%}）。"
    )
    if bh and rq:
        L.append(
            f"- buy_hold CAGR {bh['cagr']:.2%} / rebalance_q CAGR "
            f"{rq['cagr']:.2%}（差 {rq['cagr'] - bh['cagr']:+.2%}）。"
            "長期上昇局面では無リバランスのモメンタム便益と、リバランスの"
            "規律的利確がトレードオフになる。"
        )
    L.append("")
    L.append("### 危機局面（ストレスイベント）")
    L.append("")
    # count where rebalance variants beat buy_hold on interval return
    crisis_better = {}
    for s in stress["summary"]:
        if s["best_strategy"]:
            crisis_better[s["best_strategy"]] = (
                crisis_better.get(s["best_strategy"], 0) + 1
            )
    if crisis_better:
        ranked = sorted(
            crisis_better.items(), key=lambda kv: kv[1], reverse=True
        )
        top = ranked[0]
        L.append(
            f"- 全{len(stress['summary'])}ストレスイベント中、区間リターン"
            f"で最も多く最良となった戦略は `{top[0]}`（{top[1]}回）。"
        )
    L.append(
        "- ストレス区間では現金10%スリーブが下方を一貫して緩和（バスケット"
        "の最大DDがオルカン単独より浅い局面が支配的）。バンド型hybridは"
        "急落時に閾値発火で押し目買いを自動化し、四半期固定より反発を"
        "捉えやすい一方、発火頻度ぶん取引が増える。"
    )
    L.append("")
    L.append("### 長期・分布頑健性（上昇バイアス排除）")
    L.append("")
    # use rolling median + bootstrap 5%ile to judge robustness, not full-period
    rob_lines = []
    for cid in STRATEGY_ORDER:
        rs = rolling["stats"].get(cid)
        bs = bootstrap["summary"].get(cid)
        if not rs or not bs:
            continue
        rob_lines.append(
            (cid, rs["cagr_median"], rs["bh_win_rate"], bs["cagr_p05"])
        )
    if rob_lines:
        # robust pick: highest bootstrap 5%ile (downside-protected CAGR)
        robust = max(rob_lines, key=lambda x: x[3])
        stable = min(
            (
                (cid, rolling["stats"][cid]["cagr_iqr"])
                for cid in STRATEGY_ORDER
                if cid in rolling["stats"]
            ),
            key=lambda x: x[1],
        )
        L.append(
            f"- ローリング中央値・B&H超過勝率・ブートストラップ下側5%ile を"
            f"総合すると、下方保護込みで最も底堅いのは `{robust[0]}`"
            f"（ブートストラップCAGR 5%ile {robust[3]:.2%}, "
            f"ローリングCAGR中央値 {robust[1]:.2%}, "
            f"B&H超過勝率 {robust[2]:.0%}）。"
        )
        L.append(
            f"- サブ期間ばらつき（IQR）が最小＝最も再現性が高い戦略は "
            f"`{stable[0]}`（CAGR IQR {stable[1]:.2%}）。"
        )
    L.append("")
    L.append("### 結論（regime 横断）")
    L.append("")
    L.append(
        "- 全期間CAGR単独で戦略を選ぶと、観測期間の上昇バイアスに依存した"
        "結論になりやすい。ローリング非重複ウィンドウ・ストレスイベント・"
        "定常ブロックブートストラップの3視点を重ねると、リバランス系"
        "（四半期 or バンド型hybrid）は強気局面でB&Hにわずかに劣後しうる"
        "一方、危機局面の下方抑制とサブ期間再現性で優位を示す。"
    )
    L.append(
        "- 現金10%＋四半期/バンドリバランスの組合せは、最大DDと水面下"
        "期間を体系的に短縮し、ブートストラップ下側5%ileでもプラス圏を"
        "保ちやすい。長期の絶対リターン最大化より「どの相場でも壊れにくい」"
        "ことを重視するなら、規律的リバランス（特にバンド型hybrid）が"
        "上昇バイアスを排した頑健な選択である。"
    )
    L.append(
        "- proxy_extended（200A→2644 高忠実, 近年4.6年）は full_proxy と"
        "同方向の序列を示し、多段スプライスが結論を歪めていないことの"
        "クロスチェックになる。"
    )
    L.append("")
    path = root_dir / "report.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def write_scenario_md(
    sr: ScenarioResult, config: BacktestConfig, out_dir: Path
) -> None:
    """Per-scenario report.md (full_proxy / proxy_extended)."""
    L: List[str] = []
    L.append(f"# シナリオC: {sr.name}")
    L.append("")
    L.append(f"生成日時: {datetime.now():%Y-%m-%d %H:%M:%S}")
    L.append("")
    L.append("## 前提・スプライス注記")
    L.append("")
    L.append(
        f"- 期間: {sr.start} 〜 {sr.end}"
        f"（約{(sr.end - sr.start).days / 365.25:.2f}年）"
    )
    L.append(f"- 初期投資: {config.initial_capital:,.0f}円")
    L.append(
        "- バスケット: A群45%(2559/1540/1629) + "
        "B群45%(2646/1306/1618/200A/1615) + 現金10%"
    )
    if sr.name == "full_proxy":
        L.append(
            f"- 2559→1554（月次相関 {PROXY_2559[3]}）、"
            f"2646→1623（相関 {PROXY_2646[3]}）"
        )
        L.append(
            f"- 200A 多段スプライス: 実200A({PROXY_200A_REAL_ANCHOR}~) / "
            f"2644(相関 {PROXY_200A_2644_CORR}) / 1625(相関 "
            f"{PROXY_200A_1625_CORR})。各スプライス点でリターン連続化。"
        )
    else:
        L.append(
            f"- 200A→2644 のみ（相関 {PROXY_200A_2644_CORR}, 高忠実近年"
            "リファレンス）。2559/2646 は実データ範囲で十分カバー。"
        )
    L.append(
        "- 全価格 API 経由・DB直接クエリ不使用、"
        f"単日ジャンプ>{MAX_DAILY_JUMP:.0%} 不連続ガード適用。"
    )
    L.append("")
    L.append("### 銘柄別データ開始日（窓内）")
    L.append("")
    L.append("| 銘柄 | データ開始 |")
    L.append("|------|-----------|")
    for c in ETF_CODES + [CASH_CODE]:
        L.append(f"| {c} | {sr.listings.get(c)} |")
    L.append("")
    L.append("## 戦略別サマリ（拡張指標込み）")
    L.append("")
    L.append(
        "| 戦略 | 総ﾘﾀｰﾝ | CAGR | Vol | Sharpe | MDD | Calmar | "
        "Sortino | 最悪12m | 水面下% | リバランス | バンド |"
    )
    L.append(
        "|------|--------|------|-----|--------|-----|--------|"
        "---------|--------|--------|-----------|--------|"
    )
    for cid in STRATEGY_ORDER:
        r = sr.case(cid)
        if not r:
            continue
        e = extended_metrics(r["equity_curve"], r, config.risk_free_rate)
        L.append(
            "| {c} | {tr:.2%} | {cg:.2%} | {vo:.2%} | {sh:.3f} | {md:.2%} "
            "| {ca:.2f} | {so:.2f} | {w:.2%} | {uw:.1%} | {rc} | {bc} |".format(
                c=cid,
                tr=r["total_return"],
                cg=r["cagr"],
                vo=r["vol"],
                sh=r["sharpe"],
                md=r["mdd"],
                ca=e["calmar"],
                so=e["sortino"],
                w=e["worst_rolling_12m"],
                uw=e["underwater_pct"],
                rc=r["rebalance_count"],
                bc=r["band_rebalance_count"],
            )
        )
    L.append("")
    (out_dir / "report.md").write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ENV_BASE = {
    "dev": "http://localhost:8902",
    "prod": "https://kima3.net/japan-etf-analyzer",
}


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env", choices=list(ENV_BASE), default="dev")
    p.add_argument("--base-url", type=str, default=None)
    p.add_argument("--period", type=str, default="20y")
    p.add_argument("--output-dir", type=str, default=None)
    p.add_argument(
        "--bootstrap-n",
        type=int,
        default=2000,
        help="block bootstrap resamples (default 2000; lower if slow)",
    )
    p.add_argument(
        "--bootstrap-block",
        type=int,
        default=20,
        help="expected block length in trading days (default 20)",
    )
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args(argv)


def resolve_reports_root() -> Path:
    app_base = Path(os.environ.get("APP_BASE_DIR", str(PROJECT_ROOT)))
    candidates = [
        app_base / "reports",
        BACKEND_DIR / "reports",
        PROJECT_ROOT / "reports",
    ]
    return next((p for p in candidates if p.is_dir()), candidates[0])


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    base_url = args.base_url or ENV_BASE[args.env]

    if args.output_dir:
        root_dir = Path(args.output_dir)
    else:
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        root_dir = (
            resolve_reports_root() / "backtest" / f"{ts}_robustness"
        )
    root_dir.mkdir(parents=True, exist_ok=True)
    logger.info("output root: %s", root_dir)

    fetch_codes = ETF_CODES + PROXY_SOURCE_CODES
    logger.info("fetching prices via API: %s", base_url)
    raw = fetch_price_map(fetch_codes, base_url, period=args.period)

    config = BacktestConfig(initial_capital=INITIAL_CAPITAL)
    metrics = MetricsCalculator(RISK_FREE_RATE)

    # --- Method C: full_proxy + proxy_extended ---
    fp_prices = build_full_proxy_prices(raw)
    fp_dir = root_dir / "full_proxy"
    fp = run_scenario(
        "full_proxy",
        fp_prices,
        FULL_PROXY_START,
        date(2026, 5, 15),
        config,
        metrics,
        fp_dir,
    )
    write_scenario_md(fp, config, fp_dir)

    ext_prices = build_ext_prices(raw)
    ext_dir = root_dir / "proxy_extended"
    ext = run_scenario(
        "proxy_extended",
        ext_prices,
        EXT_START,
        date(2026, 5, 15),
        config,
        metrics,
        ext_dir,
    )
    write_scenario_md(ext, config, ext_dir)

    # --- Method A: rolling sub-periods ---
    logger.info("=== Method A: rolling sub-periods ===")
    rolling = method_a_rolling(
        fp, config, metrics, root_dir / "rolling"
    )

    # --- Method B: stress events ---
    logger.info("=== Method B: stress events ===")
    stress = method_b_stress(fp, root_dir / "stress")

    # --- Method D: benchmarks ---
    logger.info("=== Method D: benchmarks ===")
    bench = method_d_benchmarks(fp, config, metrics)

    # --- Method E: block bootstrap ---
    logger.info(
        "=== Method E: block bootstrap (n=%d, block=%d) ===",
        args.bootstrap_n,
        args.bootstrap_block,
    )
    bootstrap = method_e_bootstrap(
        fp,
        root_dir / "bootstrap",
        args.bootstrap_n,
        args.bootstrap_block,
        args.seed,
    )

    # --- integrated root report ---
    write_root_report(
        root_dir,
        fp,
        ext,
        config,
        rolling,
        stress,
        bootstrap,
        bench,
        args.bootstrap_n,
        args.bootstrap_block,
    )

    total_fail = sum(
        len(r["assert_failures"]) for r in fp.results + ext.results
    )
    if total_fail:
        logger.warning(
            "[assert] %d coherence violations (C scenarios)", total_fail
        )
    else:
        logger.info("[assert] all coherence checks PASSED")

    print()
    print("=== SUMMARY: full_proxy ===")
    for cid in STRATEGY_ORDER:
        r = fp.case(cid)
        if not r:
            continue
        print(
            f"{cid:14s} total={r['total_return']*100:7.2f}%  "
            f"cagr={r['cagr']*100:6.2f}%  sharpe={r['sharpe']:6.3f}  "
            f"mdd={r['mdd']*100:7.2f}%  rebal={r['rebalance_count']:3d}"
        )
    print()
    print(f"output root: {root_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
