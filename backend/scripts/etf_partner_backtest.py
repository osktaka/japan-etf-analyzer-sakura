#!/usr/bin/env python3
"""Find the best 3rd ETF to add to the core "2559 + 1540".

The core "2559" (MSCI ACWI, listed 2020-01) cannot cover a full 10-year
window, so it is replaced **for the entire analysis by 1554** (上場インデックス
ファンド世界株式 MSCI ACWI; same index, monthly r=0.987, history since 2011).
The real 2559 is never fetched nor used. No splicing/connection is done.

Pipeline:
  1. Fetch split-adjusted daily close via the chart batch API (API-only;
     no DB direct reads — see CLAUDE.md "計算前必須チェック").
  2. Screen candidates: drop leverage/inverse names, pre-filter by the
     return_performance axis score to ~30 names, fetch their full 10y
     series, compute monthly-return correlation vs 1554 & 1540, CAGR,
     vol, Sharpe. Emit two rankings (corr<threshold & composite score),
     take the union.
  3. Build CaseSpec cases directly: singles (1554/1540/each candidate,
     buy&hold), combos (1554+1540, 1554+1540+candidate) each in buy_hold
     and quarter-end rebalance. Equal weights, common 10y window.
  4. Write reports/research/partner_backtest_YYYYMMDD.{json,md}.

Sub-period robustness (--subperiods):
  A single 10y window converges to "the one ETF that won that decade".
  With --subperiods the **same fixed candidate union** (no per-window
  re-screening) is re-backtested over 10 non-overlapping windows at three
  granularities (5y x2, ~3.3y x3, 2y x5). Each window restarts at
  1,000,000 JPY (windows are independent). A per-candidate robustness
  summary (core-beat win rate / mean rank / mean uplift / worst window)
  is written to a **separate** report; the full-10y outputs are untouched.

Usage:
    docker compose exec -T backend python3 scripts/etf_partner_backtest.py
    python3 scripts/etf_partner_backtest.py --top-n 5 --corr-threshold 0.5
    python3 scripts/etf_partner_backtest.py --period 10y --env dev
    python3 scripts/etf_partner_backtest.py --env prod --output-dir /tmp/out
    python3 scripts/etf_partner_backtest.py --top-n 5 --subperiods

CLI options:
    --period          chart period passed to the API (default: 10y)
    --top-n           candidates per ranking method (default: 5)
    --corr-threshold  max correlation for method 1 (default: 0.5)
    --output-dir      output directory (default: <root>/reports/research)
    --env             dev -> http://localhost:8902,
                      prod -> https://kima3.net/japan-etf-analyzer
    --subperiods      additionally run the fixed-union sub-period
                      robustness analysis (separate *_subperiods_* output)
"""
import argparse
import json
import logging
import math
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
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

# Reuse simulator/metrics/calendar helpers from the existing backtest.
# NOTE: load_price_data (DB direct read) is intentionally NOT imported.
from scripts.backtest_buy_hold_vs_rebalance import (  # noqa: E402
    BacktestConfig,
    CaseSpec,
    MetricsCalculator,
    PortfolioSimulator,
    build_business_calendar,
    compute_quarter_end_dates,
    forward_fill_prices,
    listing_date_map,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("etf_partner_backtest")

# Core: "2559" is replaced by 1554 (proxy) for the whole analysis.
CORE_PROXY = "1554"  # stands in for 2559 (MSCI ACWI)
CORE_GOLD = "1540"
CORE_CODES = [CORE_PROXY, CORE_GOLD]

# Fixed 4-asset core variant (not a screening candidate): the 2-asset core
# plus 商社・卸売(1629) and 純銀(1542). Equal-weighted (25% each). Added as a
# normal case to full-10y and every sub-period window, but NEVER treated as a
# screening candidate (the per-candidate core-beat win-rate stays 2-asset).
CORE4_TRADE = "1629"  # 商社・卸売 (TOPIX-17)
CORE4_SILVER = "1542"  # 純銀上場信託
CORE4_CODES = [CORE_PROXY, CORE_GOLD, CORE4_TRADE, CORE4_SILVER]

EXCLUDE_KEYWORDS = ["レバレッジ", "インバース", "ダブル", "ベア", "2倍", "-2倍"]

# Data-integrity guard: a single-day absolute return above this is treated
# as a non-physical listing-unit/currency discontinuity (not a real market
# move) and the whole series is excluded from screening/backtest.
MAX_DAILY_JUMP = 0.60

ENV_BASE = {
    "dev": "http://localhost:8902",
    "prod": "https://kima3.net/japan-etf-analyzer",
}


# ---------------------------------------------------------------------------
# Step 1: API price adapter (single data source)
# ---------------------------------------------------------------------------


def _http_get_json(url: str, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_price_map(
    codes: List[str], base_url: str, period: str = "10y"
) -> Dict[str, Dict[date, float]]:
    """Fetch split-adjusted daily close per code via the chart batch API.

    Returns {code: {date: close}} (API-only, never touches the DB).
    """
    result: Dict[str, Dict[date, float]] = {}
    uniq = sorted(set(codes))
    for i in range(0, len(uniq), 50):
        chunk = uniq[i : i + 50]
        url = (
            f"{base_url}/api/v1/etfs/chart/batch"
            f"?codes={','.join(chunk)}&period={period}"
        )
        payload = _http_get_json(url)
        data = payload.get("data", {})
        for code in chunk:
            series = (data.get(code) or {}).get("data") or []
            day_map: Dict[date, float] = {}
            for row in series:
                close = row.get("close")
                if close is None:
                    continue
                day_map[date.fromisoformat(row["date"])] = float(close)
            result[code] = day_map
            logger.info("fetched %s: %d days", code, len(day_map))
    return result


# ---------------------------------------------------------------------------
# Step 2: candidate screening (correlation + return, two methods)
# ---------------------------------------------------------------------------


def fetch_universe(base_url: str) -> List[Dict]:
    """Fetch the full ETF list (paginated, limit/offset)."""
    etfs: List[Dict] = []
    offset = 0
    while True:
        url = f"{base_url}/api/v1/etfs?limit=100&offset={offset}"
        payload = _http_get_json(url)
        batch = payload.get("data", [])
        etfs.extend(batch)
        total = payload.get("meta", {}).get("total", len(etfs))
        offset += len(batch)
        if not batch or offset >= total:
            break
    logger.info("universe: %d ETFs", len(etfs))
    return etfs


def prefilter_candidates(etfs: List[Dict], limit: int = 30) -> List[Dict]:
    """Drop leverage/inverse names, rank by return_performance, take top N."""
    kept = [
        e
        for e in etfs
        if not any(k in (e.get("name") or "") for k in EXCLUDE_KEYWORDS)
        and e.get("code") not in CORE_CODES
    ]
    def _ret_score(e: Dict) -> float:
        v = (e.get("axis_scores") or {}).get("return_performance")
        return float(v) if v is not None else 0.0

    kept.sort(key=_ret_score, reverse=True)
    top = kept[:limit]
    logger.info("prefilter: %d candidates (top %d by return)", len(top), limit)
    return top


def _monthly_returns(
    day_map: Dict[date, float]
) -> Dict[Tuple[int, int], float]:
    """Month-end close -> month-over-month return keyed by (year, month)."""
    last_close: Dict[Tuple[int, int], Tuple[date, float]] = {}
    for d, p in sorted(day_map.items()):
        key = (d.year, d.month)
        prev = last_close.get(key)
        if prev is None or d > prev[0]:
            last_close[key] = (d, p)
    months = sorted(last_close.keys())
    rets: Dict[Tuple[int, int], float] = {}
    for i in range(1, len(months)):
        p0 = last_close[months[i - 1]][1]
        p1 = last_close[months[i]][1]
        if p0 > 0:
            rets[months[i]] = p1 / p0 - 1.0
    return rets


def max_daily_jump(day_map: Dict[date, float]) -> float:
    """Largest |consecutive-day return| in a series (0.0 if <2 points).

    Used as a data-integrity sanity check: API/ChartService normally returns
    split-adjusted closes, but some ETN-type instruments (WisdomTree/SPDR)
    carry listing-unit / currency-base discontinuities the adjuster does not
    smooth, yielding non-physical jumps (e.g. 109 -> 12820 in one day). Such
    series must not enter screening/backtest (CLAUDE.md 計算前必須チェック).
    """
    items = sorted(day_map.items())
    worst = 0.0
    for i in range(1, len(items)):
        p0 = items[i - 1][1]
        p1 = items[i][1]
        if p0 > 0:
            worst = max(worst, abs(p1 / p0 - 1.0))
    return worst


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if vx == 0 or vy == 0:
        return 0.0
    return cov / (vx * vy)


def _aligned(
    a: Dict[Tuple[int, int], float], b: Dict[Tuple[int, int], float]
) -> Tuple[List[float], List[float]]:
    keys = sorted(set(a) & set(b))
    return [a[k] for k in keys], [b[k] for k in keys]


def _stats_from_monthly(rets: Dict[Tuple[int, int], float]) -> Dict:
    """CAGR / annualized vol / Sharpe from a monthly-return series."""
    vals = [rets[k] for k in sorted(rets)]
    n = len(vals)
    if n < 2:
        return {"cagr": 0.0, "vol": 0.0, "sharpe": 0.0, "months": n}
    growth = 1.0
    for r in vals:
        growth *= 1.0 + r
    years = n / 12.0
    cagr = growth ** (1.0 / years) - 1.0 if years > 0 else 0.0
    mean = sum(vals) / n
    var = sum((r - mean) ** 2 for r in vals) / max(n - 1, 1)
    vol = math.sqrt(var) * math.sqrt(12)
    sharpe = cagr / vol if vol > 0 else 0.0
    return {"cagr": cagr, "vol": vol, "sharpe": sharpe, "months": n}


def screen_candidates(
    candidates: List[Dict],
    price_map: Dict[str, Dict[date, float]],
    name_map: Dict[str, str],
    corr_threshold: float,
    top_n: int,
) -> Dict:
    """Compute correlation/return stats; emit two rankings + the union."""
    for core in CORE_CODES:
        cj = max_daily_jump(price_map.get(core, {}))
        if cj > MAX_DAILY_JUMP:
            raise RuntimeError(
                f"core series {core} has a non-physical discontinuity "
                f"(max_daily_jump={cj:.4f}); aborting to avoid a "
                f"misleading report (CLAUDE.md 計算前必須チェック)"
            )
    core_proxy_m = _monthly_returns(price_map.get(CORE_PROXY, {}))
    core_gold_m = _monthly_returns(price_map.get(CORE_GOLD, {}))

    # Keep the unified backtest window ~10y: require candidates to share a
    # long common window with the core (short-history ETFs excluded here).
    min_common_months = 100
    rows: List[Dict] = []
    excluded_short: List[Dict] = []
    excluded_bad_data: List[Dict] = []
    for c in candidates:
        code = c["code"]
        dm = price_map.get(code, {})
        jump = max_daily_jump(dm)
        if jump > MAX_DAILY_JUMP:
            excluded_bad_data.append(
                {
                    "code": code,
                    "name": name_map.get(code, ""),
                    "max_daily_jump": round(jump, 4),
                    "reason": f"max_daily_jump>{MAX_DAILY_JUMP}",
                }
            )
            continue
        m = _monthly_returns(dm)
        xs1, ys1 = _aligned(m, core_proxy_m)
        xs2, ys2 = _aligned(m, core_gold_m)
        if len(xs1) < min_common_months:
            excluded_short.append(
                {
                    "code": code,
                    "name": name_map.get(code, ""),
                    "common_months": len(xs1),
                    "reason": f"common_months<{min_common_months}",
                }
            )
            continue
        st = _stats_from_monthly(m)
        rows.append(
            {
                "code": code,
                "name": name_map.get(code, ""),
                "corr_1554": round(_pearson(xs1, ys1), 4),
                "corr_1540": round(_pearson(xs2, ys2), 4),
                "cagr": round(st["cagr"], 6),
                "vol": round(st["vol"], 6),
                "sharpe": round(st["sharpe"], 6),
                "common_months": len(xs1),
            }
        )

    # Method 1: correlation < threshold (vs core proxy) then CAGR desc.
    m1 = sorted(
        [r for r in rows if abs(r["corr_1554"]) < corr_threshold],
        key=lambda r: r["cagr"],
        reverse=True,
    )[:top_n]

    # Method 2: composite = low-correlation 50% + Sharpe-normalized 50%.
    sharpes = [r["sharpe"] for r in rows] or [0.0]
    s_min, s_max = min(sharpes), max(sharpes)
    span = (s_max - s_min) or 1.0
    for r in rows:
        low_corr = 1.0 - min(abs(r["corr_1554"]), 1.0)
        s_norm = (r["sharpe"] - s_min) / span
        r["composite"] = round(0.5 * low_corr + 0.5 * s_norm, 4)
    m2 = sorted(rows, key=lambda r: r["composite"], reverse=True)[:top_n]

    union_codes: List[str] = []
    for r in m1 + m2:
        if r["code"] not in union_codes:
            union_codes.append(r["code"])
    union_codes = union_codes[:8]
    logger.info(
        "screen: method1=%d method2=%d union=%d",
        len(m1),
        len(m2),
        len(union_codes),
    )
    return {
        "all_rows": rows,
        "method1_corr": m1,
        "method2_composite": m2,
        "union_codes": union_codes,
        "corr_threshold": corr_threshold,
        "excluded_short_history": excluded_short,
        "excluded_bad_data": excluded_bad_data,
        "max_daily_jump_limit": MAX_DAILY_JUMP,
        "min_common_months": min_common_months,
    }


# ---------------------------------------------------------------------------
# Step 3: scenario construction & backtest
# ---------------------------------------------------------------------------


def _equal_weights(codes: List[str]) -> Dict[str, float]:
    base = round(1.0 / len(codes), 6)
    w = {c: base for c in codes[:-1]}
    w[codes[-1]] = round(1.0 - sum(w.values()), 6)
    return w


def build_specs(union_codes: List[str]) -> List[CaseSpec]:
    """Singles (buy_hold) + combos (buy_hold & quarter-end rebalance)."""
    specs: List[CaseSpec] = []
    # Singles: core proxy, gold, each candidate (buy & hold only).
    for code in [CORE_PROXY, CORE_GOLD] + union_codes:
        specs.append(
            CaseSpec(
                case_id=f"single_{code}_bh",
                group="single",
                allocation="single",
                strategy="buy_hold",
                codes=[code],
                target_weights={code: 1.0},
            )
        )
    # Combo base: 1554 + 1540 ; per-candidate ; fixed 4-asset core variant.
    combos: List[Tuple[str, List[str]]] = [("core", list(CORE_CODES))]
    for code in union_codes:
        combos.append((f"core+{code}", CORE_CODES + [code]))
    combos.append(("core4", list(CORE4_CODES)))  # 25% each, fixed variant
    for label, codes in combos:
        weights = _equal_weights(codes)
        for strat in ("buy_hold", "rebalance"):
            specs.append(
                CaseSpec(
                    case_id=f"combo_{label}_{strat}",
                    group="combo",
                    allocation="equal",
                    strategy=strat,
                    codes=list(codes),
                    target_weights=dict(weights),
                )
            )
    return specs


def run_backtests(
    specs: List[CaseSpec],
    price_map: Dict[str, Dict[date, float]],
    config: BacktestConfig,
    window: Tuple[date, date],
) -> List[Dict]:
    """Run each spec over the common 10y window; attach metrics."""
    start, end = window
    clipped = {
        code: {d: p for d, p in dm.items() if start <= d <= end}
        for code, dm in price_map.items()
    }
    calendar = build_business_calendar(clipped, start, end)
    listings = listing_date_map(clipped)
    prices = forward_fill_prices(clipped, calendar)
    rebalance_dates = compute_quarter_end_dates(calendar)
    metrics = MetricsCalculator(config.risk_free_rate)

    results: List[Dict] = []
    for spec in specs:
        sim = PortfolioSimulator(
            config, spec, prices, calendar, listings, rebalance_dates
        )
        case = sim.run()
        case.update(metrics.compute(case["equity_curve"]))
        case["effective_period"] = [
            case["equity_curve"][0][0].isoformat(),
            case["equity_curve"][-1][0].isoformat(),
        ]
        case["equity_curve"] = [
            [d.isoformat(), round(v, 2)] for d, v in case["equity_curve"]
        ]
        case.pop("events", None)
        results.append(case)
        logger.info(
            "  %s: total=%.2f%% cagr=%.2f%% sharpe=%.3f mdd=%.2f%%",
            spec.case_id,
            case["total_return"] * 100,
            case["cagr"] * 100,
            case["sharpe"],
            case["mdd"] * 100,
        )
    return results


def common_window(
    price_map: Dict[str, Dict[date, float]], codes: List[str]
) -> Tuple[date, date]:
    """Latest first-date / earliest last-date across the given codes."""
    starts, ends = [], []
    for c in codes:
        dm = price_map.get(c)
        if dm:
            starts.append(min(dm))
            ends.append(max(dm))
    return max(starts), min(ends)


# ---------------------------------------------------------------------------
# Step 4: report output (research convention)
# ---------------------------------------------------------------------------


def _rank_table(rows: List[Dict]) -> List[str]:
    out = [
        "| 順位 | コード | 名称 | ρ(vs1554) | ρ(vs1540) | CAGR | ボラ | "
        "シャープ | 複合 | 共通月数 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        out.append(
            f"| {i} | {r['code']} | {r['name'][:24]} | "
            f"{r['corr_1554']:.3f} | {r['corr_1540']:.3f} | "
            f"{r['cagr']:.2%} | {r['vol']:.2%} | {r['sharpe']:.3f} | "
            f"{r.get('composite', 0.0):.3f} | {r['common_months']} |"
        )
    return out


# Core-structure variants compared in the dedicated section. Labels are
# fixed (YAGNI: 4 structures are enough; no generic N-core abstraction).
CORE_VARIANTS: List[Tuple[str, str]] = [
    ("combo_core", "2資産コア(1554+1540)"),
    (f"combo_core+{CORE4_TRADE}", f"コア+{CORE4_TRADE}(3資産)"),
    (f"combo_core+{CORE4_SILVER}", f"コア+{CORE4_SILVER}(3資産)"),
    ("combo_core4", "4資産コア(1554+1540+1629+1542)"),
]


def build_variant_summary(cases: List[Dict]) -> Dict:
    """Per-variant per-strategy metrics + a core4-vs-2asset verdict block."""
    by_id = {c["case_id"]: c for c in cases}
    variants: Dict[str, Dict] = {}
    for prefix, label in CORE_VARIANTS:
        per_strat: Dict[str, Dict] = {}
        for strat in ("buy_hold", "rebalance"):
            c = by_id.get(f"{prefix}_{strat}")
            if c is None:
                continue
            per_strat[strat] = {
                "case_id": c["case_id"],
                "total_return": c["total_return"],
                "cagr": c["cagr"],
                "vol": c["vol"],
                "sharpe": c["sharpe"],
                "mdd": c["mdd"],
            }
        variants[prefix] = {"label": label, "strategies": per_strat}
    base = by_id.get("combo_core_rebalance")
    c4 = by_id.get("combo_core4_rebalance")
    verdict: Dict = {}
    if base and c4:
        verdict = {
            "core2_rebalance_sharpe": base["sharpe"],
            "core4_rebalance_sharpe": c4["sharpe"],
            "sharpe_uplift": round(c4["sharpe"] - base["sharpe"], 6),
            "vol_delta": round(c4["vol"] - base["vol"], 6),
            "mdd_delta": round(c4["mdd"] - base["mdd"], 6),
            "cagr_delta": round(c4["cagr"] - base["cagr"], 6),
            "core4_improves_risk_adjusted": c4["sharpe"] > base["sharpe"],
        }
    return {"variants": variants, "core4_vs_core2_rebalance": verdict}


def _variant_section_lines(summary: Dict) -> List[str]:
    """MD lines for the 'コア構成バリアント比較' section (full-10y)."""
    lines = [
        "## 4. コア構成バリアント比較（2/3/4資産コア × B&H/リバランス）",
        "",
        "| 構成 | 戦略 | 総リターン | CAGR | 年率Vol | Sharpe | MDD |",
        "|---|---|---|---|---|---|---|",
    ]
    for prefix, _ in CORE_VARIANTS:
        v = summary["variants"].get(prefix, {})
        label = v.get("label", prefix)
        for strat in ("buy_hold", "rebalance"):
            m = v.get("strategies", {}).get(strat)
            if not m:
                continue
            lines.append(
                f"| {label} | {strat} | {m['total_return']:.2%} | "
                f"{m['cagr']:.2%} | {m['vol']:.2%} | {m['sharpe']:.3f} | "
                f"{m['mdd']:.2%} |"
            )
    lines.append("")
    vd = summary.get("core4_vs_core2_rebalance") or {}
    if vd:
        improved = vd["core4_improves_risk_adjusted"]
        lines.append(
            f"**所見**: 4資産コア（リバランス）は 2資産コア比で Sharpe "
            f"{vd['sharpe_uplift']:+.3f}（{vd['core4_rebalance_sharpe']:.3f} "
            f"vs {vd['core2_rebalance_sharpe']:.3f}）、Vol "
            f"{vd['vol_delta']:+.2%}、MDD {vd['mdd_delta']:+.2%}、CAGR "
            f"{vd['cagr_delta']:+.2%}。リスク調整後リターンは"
            f"{'改善' if improved else '改善せず'}。"
        )
    else:
        lines.append("**所見**: 比較対象ケースが算出できませんでした。")
    lines.append("")
    return lines


def write_reports(
    screen: Dict,
    results: List[Dict],
    window: Tuple[date, date],
    output_dir: Path,
    config: BacktestConfig,
) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    win = [window[0].isoformat(), window[1].isoformat()]

    json_doc = {
        "generated_at": datetime.now().isoformat(),
        "core_proxy_note": "コアの2559は1554（MSCI ACWI 同一指数, r=0.987）で全期間代替。実2559は未使用。",
        "core_codes": CORE_CODES,
        "effective_period": win,
        "initial_capital": config.initial_capital,
        "screening": screen,
        "cases": results,
        "core_variant_summary": build_variant_summary(results),
    }
    json_path = output_dir / f"partner_backtest_{today}.json"
    json_path.write_text(
        json.dumps(json_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    best = max(
        (r for r in results if r["group"] == "combo" and "core+" in r["case_id"]),
        key=lambda r: r["sharpe"],
        default=None,
    )
    lines: List[str] = []
    lines.append("# 2559+1540 コア 最適第3 ETF バックテスト")
    lines.append("")
    lines.append(f"**生成日時**: {datetime.now().isoformat()}  ")
    lines.append(
        "**重要（データ代替）**: コアの **2559 は本分析を通じて 1554"
        "（上場インデックスファンド世界株式 MSCI ACWI、同一指数・月次相関 "
        "r=0.987・履歴2011〜）で全期間代替**。実 2559 は取得・使用していない"
        "（接続・スプライスなし）。  "
    )
    lines.append("**対象コア**: 1554（=2559代理） + 1540（純金）  ")
    lines.append(f"**有効期間（全ケース共通）**: {win[0]} 〜 {win[1]}  ")
    lines.append(
        f"**初期投資**: {config.initial_capital:,.0f}円 / 売買コスト・税・"
        "分配金は無視 / rf=0%  "
    )
    lines.append("")
    lines.append("## 1. 候補スクリーニング（2方式）")
    lines.append("")
    lines.append(
        f"### 方式1: 相関<{screen['corr_threshold']}（vs 1554）かつ CAGR 降順 上位"
    )
    lines.append("")
    lines.extend(_rank_table(screen["method1_corr"]))
    lines.append("")
    lines.append("### 方式2: 複合スコア（低相関50% + シャープ正規化50%）上位")
    lines.append("")
    lines.extend(_rank_table(screen["method2_composite"]))
    lines.append("")
    lines.append(
        f"**和集合（重複排除, バックテスト対象）**: "
        f"{', '.join(screen['union_codes'])}"
    )
    lines.append("")
    short = screen.get("excluded_short_history", [])
    if short:
        lines.append(
            f"**共通期間が短く除外（共通月数<{screen['min_common_months']}）**: "
            + ", ".join(
                f"{s['code']}({s['common_months']}ヶ月)" for s in short
            )
        )
        lines.append("")
    bad = screen.get("excluded_bad_data", [])
    if bad:
        lines.append(
            "**データ不整合で除外（API系列に非物理的な単日急変＝上場単位/"
            f"通貨基準の不連続, 日次変動>{screen.get('max_daily_jump_limit')}）"
            "**: "
            + ", ".join(
                f"{b['code']}(最大単日{b['max_daily_jump']:.0%})" for b in bad
            )
        )
        lines.append("")
    lines.append("## 2. バックテスト結果（単体 vs 組合せ × B&H vs リバランス）")
    lines.append("")
    lines.append(
        "| ケース | 種別 | 戦略 | 総リターン | CAGR | 年率Vol | Sharpe | "
        "MDD | 有効期間 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r['case_id']} | {r['group']} | {r['strategy']} | "
            f"{r['total_return']:.2%} | {r['cagr']:.2%} | {r['vol']:.2%} | "
            f"{r['sharpe']:.3f} | {r['mdd']:.2%} | "
            f"{r['effective_period'][0]}〜{r['effective_period'][1]} |"
        )
    lines.append("")
    lines.append("## 3. 最適第3候補の結論")
    lines.append("")
    if best:
        cand = best["case_id"].split("core+")[1].split("_")[0]
        lines.append(
            f"組合せ（1554+1540+候補）の中で Sharpe 最良は "
            f"**{best['case_id']}**（追加候補 = **{cand}**）: "
            f"CAGR {best['cagr']:.2%}, Sharpe {best['sharpe']:.3f}, "
            f"MDD {best['mdd']:.2%}, 総リターン {best['total_return']:.2%}。"
        )
        core_combo = next(
            (
                r
                for r in results
                if r["case_id"] == f"combo_core_{best['strategy']}"
            ),
            None,
        )
        if core_combo:
            lines.append("")
            lines.append(
                f"コアのみ（1554+1540, {best['strategy']}）= Sharpe "
                f"{core_combo['sharpe']:.3f} / CAGR {core_combo['cagr']:.2%} "
                f"に対し、第3候補 {cand} の追加で Sharpe "
                f"{best['sharpe'] - core_combo['sharpe']:+.3f} / CAGR "
                f"{best['cagr'] - core_combo['cagr']:+.2%} の変化。"
            )
    else:
        lines.append("（有効な組合せケースが算出できませんでした）")
    lines.append("")
    lines.extend(_variant_section_lines(build_variant_summary(results)))
    lines.append("## 5. 免責")
    lines.append("")
    lines.append(
        "本結果は過去データに基づく機械的検証であり将来を保証しない。"
        "売買コスト・税・分配金・スリッページを無視した単純化モデル。"
        "コアの 2559 は 1554 で代替しているため、実 2559 の経費率・乖離"
        "とは厳密には一致しない点に留意。"
    )
    lines.append("")
    md_path = output_dir / f"partner_backtest_{today}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


# ---------------------------------------------------------------------------
# Step 5: sub-period robustness (fixed candidate union, no re-screening)
# ---------------------------------------------------------------------------

# Granularity split counts over the effective 10y window. Non-overlapping,
# contiguous; boundaries are snapped to the nearest existing business day.
SUBPERIOD_GRANULARITIES: List[Tuple[str, int]] = [
    ("5y", 2),  # ~5-year x2
    ("3.3y", 3),  # decade in thirds (~3.3y x3)
    ("2y", 5),  # ~2-year x5
]
# Case-count coherence: build_specs emits, for a window with `u` usable
# candidates, (2 core + u candidate) singles + (1 core + u core+cand + 1
# core4) combos x 2 strategies. A fully covered window (u = len(union),
# i.e. all 6) yields 24 (= full-10y: 22 + 2 fixed 4-asset core cases).
SINGLE_CORE_COUNT = 2  # 1554 (=2559 proxy) + 1540, buy&hold only
COMBO_FIXED_COUNT = 2  # combo_core + combo_core4
STRATEGIES_PER_COMBO = 2  # buy_hold + rebalance


def expected_case_count(usable_count: int) -> int:
    """Cases build_specs(usable) must yield for `usable_count` candidates."""
    singles = SINGLE_CORE_COUNT + usable_count
    combos = COMBO_FIXED_COUNT + usable_count
    return singles + combos * STRATEGIES_PER_COMBO


def _snap_to_calendar(target: date, calendar: List[date]) -> date:
    """Nearest business day in `calendar` to `target` (ties -> earlier)."""
    return min(calendar, key=lambda d: (abs((d - target).days), d))


def _split_window(
    start: date, end: date, n: int, calendar: List[date]
) -> List[Tuple[date, date]]:
    """Split [start, end] into n contiguous calendar-snapped sub-windows.

    Interior boundaries are snapped to the nearest business day so that
    every window edge is a real trading day; windows are half-open in
    spirit but represented inclusively (run_backtests clips start<=d<=end).
    """
    total_days = (end - start).days
    edges: List[date] = [start]
    for i in range(1, n):
        raw = start.fromordinal(start.toordinal() + total_days * i // n)
        edges.append(_snap_to_calendar(raw, calendar))
    edges.append(end)
    return [(edges[i], edges[i + 1]) for i in range(n)]


def build_subperiod_windows(
    calendar: List[date], eff_start: date, eff_end: date
) -> List[Dict]:
    """All sub-period windows across the configured granularities."""
    windows: List[Dict] = []
    for label, n in SUBPERIOD_GRANULARITIES:
        for idx, (ws, we) in enumerate(
            _split_window(eff_start, eff_end, n, calendar), 1
        ):
            windows.append(
                {
                    "granularity": label,
                    "index": idx,
                    "window_id": f"{label}_{idx}",
                    "start": ws,
                    "end": we,
                }
            )
    return windows


def _window_codes_available(
    price_map: Dict[str, Dict[date, float]],
    code: str,
    start: date,
    end: date,
) -> bool:
    """True if `code` has >=2 prices and a clean series inside [start, end]."""
    sub = {d: p for d, p in price_map.get(code, {}).items() if start <= d <= end}
    if len(sub) < 2:
        return False
    return max_daily_jump(sub) <= MAX_DAILY_JUMP


def run_subperiod_backtests(
    union_codes: List[str],
    price_map: Dict[str, Dict[date, float]],
    config: BacktestConfig,
    windows: List[Dict],
) -> List[Dict]:
    """Re-run the fixed case set per window; record skips with reasons."""
    out: List[Dict] = []
    for w in windows:
        start, end = w["start"], w["end"]
        skipped: List[Dict] = []
        usable: List[str] = []
        for code in union_codes:
            if _window_codes_available(price_map, code, start, end):
                usable.append(code)
            else:
                skipped.append(
                    {
                        "code": code,
                        "reason": "no/short or bad-data series in window",
                    }
                )
        specs = build_specs(usable)
        cases = run_backtests(specs, price_map, config, (start, end))
        expected = expected_case_count(len(usable))
        out.append(
            {
                "window_id": w["window_id"],
                "granularity": w["granularity"],
                "index": w["index"],
                "window": [start.isoformat(), end.isoformat()],
                "skipped_candidates": skipped,
                "expected_case_count": expected,
                "case_count_ok": len(cases) == expected,
                "cases": cases,
            }
        )
    return out


def _cases_by_id(cases: List[Dict]) -> Dict[str, Dict]:
    return {c["case_id"]: c for c in cases}


def _candidate_window_metrics(
    union_codes: List[str], windows_result: List[Dict]
) -> Dict[str, List[Dict]]:
    """Per candidate, per window: uplift vs core + Sharpe rank (rebalance)."""
    per_cand: Dict[str, List[Dict]] = {c: [] for c in union_codes}
    for wr in windows_result:
        by_id = _cases_by_id(wr["cases"])
        core = by_id.get("combo_core_rebalance")
        if core is None:
            continue
        # rank candidates present in this window by combo Sharpe (rebalance)
        present = [
            (c, by_id[f"combo_core+{c}_rebalance"])
            for c in union_codes
            if f"combo_core+{c}_rebalance" in by_id
        ]
        ranked = sorted(present, key=lambda t: t[1]["sharpe"], reverse=True)
        rank_of = {c: i + 1 for i, (c, _) in enumerate(ranked)}
        for code, cmb in present:
            per_cand[code].append(
                {
                    "window_id": wr["window_id"],
                    "granularity": wr["granularity"],
                    "sharpe": cmb["sharpe"],
                    "cagr": cmb["cagr"],
                    "core_sharpe": core["sharpe"],
                    "core_cagr": core["cagr"],
                    "sharpe_uplift": cmb["sharpe"] - core["sharpe"],
                    "cagr_uplift": cmb["cagr"] - core["cagr"],
                    "beats_core_sharpe": cmb["sharpe"] > core["sharpe"],
                    "beats_core_cagr": cmb["cagr"] > core["cagr"],
                    "rank": rank_of[code],
                }
            )
    return per_cand


def _median(xs: List[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _summarize_records(recs: List[Dict]) -> Dict:
    """Aggregate one candidate's per-window records into a summary block."""
    n = len(recs)
    if n == 0:
        return {"valid_windows": 0}
    sup = [r["sharpe_uplift"] for r in recs]
    cup = [r["cagr_uplift"] for r in recs]
    wins_s = sum(1 for r in recs if r["beats_core_sharpe"])
    wins_c = sum(1 for r in recs if r["beats_core_cagr"])
    ranks = [r["rank"] for r in recs]
    worst_idx = min(range(n), key=lambda i: sup[i])
    return {
        "valid_windows": n,
        "core_beat_winrate_sharpe": round(wins_s / n, 4),
        "core_beat_winrate_cagr": round(wins_c / n, 4),
        "mean_sharpe_uplift": round(sum(sup) / n, 6),
        "median_sharpe_uplift": round(_median(sup), 6),
        "mean_cagr_uplift": round(sum(cup) / n, 6),
        "median_cagr_uplift": round(_median(cup), 6),
        "worst_window_id": recs[worst_idx]["window_id"],
        "worst_sharpe_uplift": round(sup[worst_idx], 6),
        "mean_rank": round(sum(ranks) / n, 4),
    }


def build_robustness_summary(
    union_codes: List[str], windows_result: List[Dict]
) -> Dict:
    """Overall + per-granularity per-candidate robustness aggregation."""
    per_cand = _candidate_window_metrics(union_codes, windows_result)
    overall: Dict[str, Dict] = {}
    by_gran: Dict[str, Dict[str, Dict]] = {
        g: {} for g, _ in SUBPERIOD_GRANULARITIES
    }
    for code in union_codes:
        recs = per_cand[code]
        overall[code] = _summarize_records(recs)
        for g, _ in SUBPERIOD_GRANULARITIES:
            by_gran[g][code] = _summarize_records(
                [r for r in recs if r["granularity"] == g]
            )
    ranked = sorted(
        (c for c in union_codes if overall[c].get("valid_windows", 0) > 0),
        key=lambda c: (
            -overall[c]["core_beat_winrate_sharpe"],
            -overall[c]["mean_sharpe_uplift"],
        ),
    )
    return {
        "primary_metric": "rebalance Sharpe vs combo_core_rebalance",
        "ranking_best_to_worst": ranked,
        "overall": overall,
        "by_granularity": by_gran,
        "per_window_records": per_cand,
    }


def _window_best_candidate(wr: Dict, union_codes: List[str]) -> Optional[Dict]:
    by_id = _cases_by_id(wr["cases"])
    cands = [
        (c, by_id[f"combo_core+{c}_rebalance"])
        for c in union_codes
        if f"combo_core+{c}_rebalance" in by_id
    ]
    if not cands:
        return None
    code, cmb = max(cands, key=lambda t: t[1]["sharpe"])
    core = by_id.get("combo_core_rebalance")
    return {
        "code": code,
        "sharpe": cmb["sharpe"],
        "cagr": cmb["cagr"],
        "core_sharpe": core["sharpe"] if core else None,
    }


# Sub-period core-structure variants (rebalance Sharpe compared per window
# vs the 2-asset core). Independent of the candidate robustness summary.
SUBPERIOD_VARIANTS: List[Tuple[str, str]] = [
    ("combo_core_rebalance", "2資産コア"),
    (f"combo_core+{CORE4_TRADE}_rebalance", f"コア+{CORE4_TRADE}"),
    (f"combo_core+{CORE4_SILVER}_rebalance", f"コア+{CORE4_SILVER}"),
    ("combo_core4_rebalance", "4資産コア"),
]


def _variant_window_rows(windows_result: List[Dict]) -> List[Dict]:
    """Per window: each variant's rebalance Sharpe + core4-vs-core2 flag."""
    rows: List[Dict] = []
    for wr in windows_result:
        by_id = _cases_by_id(wr["cases"])
        base = by_id.get("combo_core_rebalance")
        c4 = by_id.get("combo_core4_rebalance")
        sharpes = {
            cid: (by_id[cid]["sharpe"] if cid in by_id else None)
            for cid, _ in SUBPERIOD_VARIANTS
        }
        beats = (
            base is not None
            and c4 is not None
            and c4["sharpe"] > base["sharpe"]
        )
        rows.append(
            {
                "window_id": wr["window_id"],
                "granularity": wr["granularity"],
                "window": wr["window"],
                "sharpes": sharpes,
                "core4_sharpe": c4["sharpe"] if c4 else None,
                "core2_sharpe": base["sharpe"] if base else None,
                "core4_uplift": (
                    round(c4["sharpe"] - base["sharpe"], 6)
                    if base and c4
                    else None
                ),
                "core4_beats_core2": beats,
            }
        )
    return rows


def build_variant_robustness(windows_result: List[Dict]) -> Dict:
    """Win rate / mean / worst uplift of 4-asset vs 2-asset core (rebal)."""
    rows = _variant_window_rows(windows_result)
    valid = [r for r in rows if r["core4_uplift"] is not None]
    by_gran: Dict[str, Dict] = {}
    for g, _ in SUBPERIOD_GRANULARITIES:
        gr = [r for r in valid if r["granularity"] == g]
        if gr:
            wins = sum(1 for r in gr if r["core4_beats_core2"])
            by_gran[g] = {
                "windows": len(gr),
                "core4_winrate": round(wins / len(gr), 4),
                "mean_uplift": round(
                    sum(r["core4_uplift"] for r in gr) / len(gr), 6
                ),
            }
    summary: Dict = {
        "primary_metric": "rebalance Sharpe: combo_core4 vs combo_core",
        "valid_windows": len(valid),
        "per_window": rows,
        "by_granularity": by_gran,
    }
    if valid:
        ups = [r["core4_uplift"] for r in valid]
        wins = sum(1 for r in valid if r["core4_beats_core2"])
        worst = min(valid, key=lambda r: r["core4_uplift"])
        summary.update(
            {
                "core4_winrate": round(wins / len(valid), 4),
                "mean_uplift": round(sum(ups) / len(valid), 6),
                "worst_window_id": worst["window_id"],
                "worst_uplift": round(worst["core4_uplift"], 6),
            }
        )
    return summary


def _variant_subperiod_lines(vsum: Dict) -> List[str]:
    """MD lines: 'コア構成バリアント比較' for the sub-period report."""
    lines = [
        "## 6. コア構成バリアント比較（4資産コア vs 2資産コア, リバランス）",
        "",
    ]
    if vsum.get("valid_windows", 0):
        lines.append(
            f"**4資産コアが2資産コアの Sharpe を上回った勝率**: "
            f"{vsum['core4_winrate']:.0%}（{vsum['valid_windows']}窓中）、"
            f"平均アップリフト {vsum['mean_uplift']:+.3f}、最悪窓 "
            f"{vsum['worst_window_id']}（{vsum['worst_uplift']:+.3f}）。"
        )
        lines.append("")
        lines.append("### 粒度別小計")
        lines.append("")
        lines.append("| 粒度 | 窓数 | 4資産コア超え勝率 | 平均アップリフト |")
        lines.append("|---|---|---|---|")
        for g, _ in SUBPERIOD_GRANULARITIES:
            gs = vsum["by_granularity"].get(g)
            if gs:
                lines.append(
                    f"| {g} | {gs['windows']} | "
                    f"{gs['core4_winrate']:.0%} | "
                    f"{gs['mean_uplift']:+.3f} |"
                )
    else:
        lines.append("（比較可能な窓がありませんでした）")
    lines.append("")
    lines.append("### 窓別 4構成 Sharpe（リバランス）")
    lines.append("")
    lines.append(
        "| 窓ID | 期間 | "
        + " | ".join(lbl for _, lbl in SUBPERIOD_VARIANTS)
        + " |"
    )
    lines.append("|---" * (2 + len(SUBPERIOD_VARIANTS)) + "|")
    for r in vsum.get("per_window", []):
        cells = []
        for cid, _ in SUBPERIOD_VARIANTS:
            v = r["sharpes"].get(cid)
            cells.append(f"{v:.3f}" if v is not None else "-")
        period = f"{r['window'][0]}〜{r['window'][1]}"
        lines.append(
            f"| {r['window_id']} | {period} | " + " | ".join(cells) + " |"
        )
    lines.append("")
    return lines


def write_subperiod_reports(
    union_codes: List[str],
    windows: List[Dict],
    windows_result: List[Dict],
    summary: Dict,
    output_dir: Path,
    config: BacktestConfig,
    eff_period: Tuple[date, date],
) -> Tuple[Path, Path]:
    """Write *_subperiods_* JSON + MD without touching full-10y outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    total_failures = sum(
        len(c.get("assert_failures", []))
        for wr in windows_result
        for c in wr["cases"]
    )
    json_doc = {
        "generated_at": datetime.now().isoformat(),
        "analysis": "sub-period robustness (fixed candidate union)",
        "core_codes": CORE_CODES,
        "fixed_union_codes": union_codes,
        "fixed_union_note": (
            "候補集合は full-10y スクリーニングの和集合で固定。"
            "窓ごとの再スクリーニングは行わない（窓間で候補が変わると"
            "比較不能になるため）。"
        ),
        "effective_period": [
            eff_period[0].isoformat(),
            eff_period[1].isoformat(),
        ],
        "initial_capital": config.initial_capital,
        "window_definitions": [
            {
                "window_id": w["window_id"],
                "granularity": w["granularity"],
                "index": w["index"],
                "start": w["start"].isoformat(),
                "end": w["end"].isoformat(),
            }
            for w in windows
        ],
        "windows": windows_result,
        "robustness_summary": summary,
        "core_variant_robustness": build_variant_robustness(windows_result),
        "coherence_total_failures": total_failures,
        "case_count_mismatch_windows": [
            wr["window_id"]
            for wr in windows_result
            if not wr.get("case_count_ok", True)
        ],
    }
    json_path = output_dir / f"partner_backtest_subperiods_{today}.json"
    json_path.write_text(
        json.dumps(json_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path = output_dir / f"partner_backtest_subperiods_{today}.md"
    md_path.write_text(
        "\n".join(
            _subperiod_md_lines(
                union_codes, windows, windows_result, summary,
                config, eff_period,
            )
        ),
        encoding="utf-8",
    )
    return json_path, md_path


def _robustness_table(union_codes: List[str], summary: Dict) -> List[str]:
    out = [
        "| コード | 有効窓 | コア超え勝率(S) | コア超え勝率(C) | "
        "平均順位 | 平均Sアップリフト | 最悪窓Sアップリフト | 最悪窓 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for code in summary["ranking_best_to_worst"]:
        s = summary["overall"][code]
        out.append(
            f"| {code} | {s['valid_windows']} | "
            f"{s['core_beat_winrate_sharpe']:.0%} | "
            f"{s['core_beat_winrate_cagr']:.0%} | "
            f"{s['mean_rank']:.2f} | "
            f"{s['mean_sharpe_uplift']:+.3f} | "
            f"{s['worst_sharpe_uplift']:+.3f} | {s['worst_window_id']} |"
        )
    return out


def _subperiod_md_lines(
    union_codes: List[str],
    windows: List[Dict],
    windows_result: List[Dict],
    summary: Dict,
    config: BacktestConfig,
    eff_period: Tuple[date, date],
) -> List[str]:
    lines: List[str] = []
    lines.append("# 第3 ETF サブ期間頑健性分析（候補固定・非重複多粒度）")
    lines.append("")
    lines.append(f"**生成日時**: {datetime.now().isoformat()}  ")
    lines.append(
        "**目的**: 過去10年単一窓は『その期間で最強の銘柄』に収束する。"
        "非重複の多粒度サブ期間で同一ケース集合を再計算し、候補ごとに"
        "『どの局面でも安定してコアを超えるか』を評価する。  "
    )
    lines.append(
        "**候補固定（重要）**: 候補集合は full-10y スクリーニングの和集合 "
        f"**{', '.join(union_codes)}** に固定。窓ごとの再スクリーニングは"
        "行わない（窓間で候補が変わると比較不能になるため）。  "
    )
    lines.append(
        f"**有効期間**: {eff_period[0].isoformat()} 〜 "
        f"{eff_period[1].isoformat()}。各窓は窓開始日に "
        f"{config.initial_capital:,.0f}円で再スタート（窓間で資産を"
        "持ち越さない＝各窓独立）。  "
    )
    lines.append("")
    lines.append("## 1. 窓定義（非重複・3粒度・計10窓）")
    lines.append("")
    lines.append("| 窓ID | 粒度 | 開始（営業日スナップ） | 終了 |")
    lines.append("|---|---|---|---|")
    for w in windows:
        lines.append(
            f"| {w['window_id']} | {w['granularity']} | "
            f"{w['start'].isoformat()} | {w['end'].isoformat()} |"
        )
    lines.append("")
    lines.append(
        "## 2. 頑健性サマリ（主指標=リバランス Sharpe vs コア）"
    )
    lines.append("")
    lines.extend(_robustness_table(union_codes, summary))
    lines.append("")
    lines.append("## 3. 粒度別小計（コア超え勝率S / 平均順位）")
    lines.append("")
    lines.append(
        "| コード | "
        + " | ".join(f"{g}" for g, _ in SUBPERIOD_GRANULARITIES)
        + " |"
    )
    lines.append("|---" * (1 + len(SUBPERIOD_GRANULARITIES)) + "|")
    for code in union_codes:
        cells = [code]
        for g, _ in SUBPERIOD_GRANULARITIES:
            gs = summary["by_granularity"][g][code]
            if gs.get("valid_windows", 0):
                cells.append(
                    f"{gs['core_beat_winrate_sharpe']:.0%} / "
                    f"{gs['mean_rank']:.1f}"
                )
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## 4. 窓別ハイライト（各窓のベスト候補, リバランス）")
    lines.append("")
    lines.append(
        "| 窓ID | 期間 | ベスト候補 | 候補Sharpe | コアSharpe |"
    )
    lines.append("|---|---|---|---|---|")
    for wr in windows_result:
        best = _window_best_candidate(wr, union_codes)
        period = f"{wr['window'][0]}〜{wr['window'][1]}"
        if best is None:
            lines.append(f"| {wr['window_id']} | {period} | - | - | - |")
            continue
        cs = best["core_sharpe"]
        cs_txt = f"{cs:.3f}" if cs is not None else "-"
        lines.append(
            f"| {wr['window_id']} | {period} | {best['code']} | "
            f"{best['sharpe']:.3f} | {cs_txt} |"
        )
    lines.append("")
    lines.append("## 5. 解釈の注意")
    lines.append("")
    lines.append(
        "- 短い窓ほどサンプルが少なくノイズが大きい（2y窓の単発結果は"
        "過大解釈しないこと）。  "
    )
    lines.append(
        "- 局面差が大きい: 2020年コロナ急落、2022年金利上昇、資源・"
        "金高など、窓ごとに支配的なマクロ要因が異なる。  "
    )
    lines.append(
        "- 頑健候補とは『単一窓の最大リターン』ではなく『多くの局面で"
        "安定してコアを超え、最悪窓でも崩れにくい』候補を指す。  "
    )
    lines.append("")
    lines.extend(
        _variant_subperiod_lines(build_variant_robustness(windows_result))
    )
    lines.append("## 7. 免責")
    lines.append("")
    lines.append(
        "本結果は過去データに基づく機械的検証であり将来を保証しない。"
        "売買コスト・税・分配金・スリッページを無視した単純化モデル。"
        "コアの 2559 は 1554 で代替しているため、実 2559 の経費率・乖離"
        "とは厳密には一致しない点に留意。"
    )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--period", default="10y")
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--corr-threshold", type=float, default=0.5)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--env", choices=["dev", "prod"], default="dev")
    p.add_argument(
        "--subperiods",
        action="store_true",
        help="also run the fixed-union sub-period robustness analysis",
    )
    return p.parse_args(argv)


def resolve_output_dir(arg: Optional[str]) -> Path:
    if arg:
        return Path(arg)
    app_base = Path(os.environ.get("APP_BASE_DIR", str(PROJECT_ROOT)))
    for root in (app_base, BACKEND_DIR, PROJECT_ROOT):
        if (root / "reports").is_dir():
            return root / "reports" / "research"
    return app_base / "reports" / "research"


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    base_url = ENV_BASE[args.env]
    config = BacktestConfig()
    output_dir = resolve_output_dir(args.output_dir)
    logger.info("env=%s base=%s output_dir=%s", args.env, base_url, output_dir)

    # Step 2a: universe + prefilter (cheap list call).
    universe = fetch_universe(base_url)
    name_map = {e["code"]: e.get("name", "") for e in universe}
    name_map.setdefault(CORE_PROXY, "上場インデックスファンド世界株式(MSCI ACWI)")
    candidates = prefilter_candidates(universe, limit=30)
    cand_codes = [c["code"] for c in candidates]

    # Step 1: fetch full series for core (incl. 4-asset variant codes) +
    # prefiltered candidates. CORE4_CODES are always fetched so the fixed
    # 4-asset variant is computable regardless of screening / --top-n.
    price_map = fetch_price_map(
        CORE4_CODES + cand_codes, base_url, period=args.period
    )

    # Step 2b: screen.
    screen = screen_candidates(
        candidates, price_map, name_map, args.corr_threshold, args.top_n
    )

    # Step 3: common 10y window across core (incl. 4-asset variant) +
    # selected candidates. CORE4_CODES included so the variant shares the
    # exact same window as every other case (no separate window).
    win_codes = CORE4_CODES + screen["union_codes"]
    window = common_window(price_map, win_codes)
    logger.info("common window: %s 〜 %s", window[0], window[1])
    specs = build_specs(screen["union_codes"])
    results = run_backtests(specs, price_map, config, window)

    # Step 4: reports.
    json_path, md_path = write_reports(
        screen, results, window, output_dir, config
    )
    logger.info("=== outputs ===")
    logger.info("  JSON: %s", json_path)
    logger.info("  MD:   %s", md_path)

    # Step 5: optional sub-period robustness (fixed candidate union).
    if args.subperiods:
        union = screen["union_codes"]
        full_clip = {
            code: {
                d: p
                for d, p in dm.items()
                if window[0] <= d <= window[1]
            }
            for code, dm in price_map.items()
        }
        full_cal = build_business_calendar(full_clip, window[0], window[1])
        sp_windows = build_subperiod_windows(full_cal, window[0], window[1])
        logger.info(
            "sub-period: %d windows over %s〜%s (fixed union=%s)",
            len(sp_windows),
            window[0],
            window[1],
            ",".join(union),
        )
        sp_results = run_subperiod_backtests(
            union, price_map, config, sp_windows
        )
        sp_summary = build_robustness_summary(union, sp_results)
        sp_json, sp_md = write_subperiod_reports(
            union, sp_windows, sp_results, sp_summary,
            output_dir, config, window,
        )
        sp_failures = sum(
            len(c.get("assert_failures", []))
            for wr in sp_results
            for c in wr["cases"]
        )
        bad_count_windows = [
            wr["window_id"]
            for wr in sp_results
            if not wr.get("case_count_ok", True)
        ]
        if sp_failures or bad_count_windows:
            logger.warning(
                "[assert] sub-period: %d equity-coherence violations; "
                "case-count mismatch windows=%s",
                sp_failures,
                bad_count_windows or "none",
            )
        else:
            logger.info("[assert] sub-period coherence checks PASSED")
        logger.info("=== sub-period outputs ===")
        logger.info("  JSON: %s", sp_json)
        logger.info("  MD:   %s", sp_md)

    # Spot verification: compare a 1554 price point with the raw API.
    raw = _http_get_json(
        f"{base_url}/api/v1/etfs/chart/batch?codes=1554&period={args.period}"
    )
    series = (raw["data"].get("1554") or {}).get("data") or []
    if series:
        s0 = series[0]
        used = price_map.get("1554", {}).get(date.fromisoformat(s0["date"]))
        logger.info(
            "[spot] 1554 %s API close=%.2f / used=%.2f -> %s",
            s0["date"],
            float(s0["close"]),
            used if used is not None else float("nan"),
            "MATCH" if used == float(s0["close"]) else "MISMATCH",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
