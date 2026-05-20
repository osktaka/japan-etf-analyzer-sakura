#!/usr/bin/env python3
"""Rebalance-frequency comparison backtest (4 plans x 2 scenarios).

Basket = the *test user's actual holdings* = 戦略書案B
(``docs/12_personal_strategy.md`` frontmatter ``target_holdings``, SSOT,
2026-05-18 改訂):

  Group A (45%): 1655=15%, 314A=15%, 1629=15%
  Group B (40%): 1615=10%, 2646=10%, 1618=10%, 200A=10%
  Cash:    15%  (synthetic "CASH" code, price=1.0)

Compares how often you should rebalance:

  - none : never rebalance (buy & hold the initial allocation)
  - 3mo  : every quarter-end   (last trading day of Mar/Jun/Sep/Dec)
  - 6mo  : every half-year-end (last trading day of Jun/Dec)
  - 12mo : every year-end      (last trading day of Dec)

Auto-proxy back-fill (the core of this script)
---------------------------------------------
Short-history equity ETFs (real history < ~3y / 750 trading days at the
scenario window start, e.g. 314A listed 2025-01-16, 200A listed
2024-06-04) are extended backward with a *data-driven* proxy: among ETFs
sharing the target's category (fallback: all categories) that have ≥3y of
pre-anchor history and ≥250-day overlap with the target, the one whose
*daily-return Pearson correlation* with the target is **highest** is chosen
and spliced via the existing :func:`splice_proxy` (continuity-preserving).
No proxy code is hard-coded — it is selected from the data each run.

Reuses the price-source-agnostic engine from
``backtest_buy_hold_vs_rebalance.py`` (PortfolioSimulator / MetricsCalculator
/ CaseSpec / calendar helpers) and the API-only price plumbing from
``backtest_custom_basket_rebalance.py`` (fetch_price_map / splice_proxy /
inject_cash_series / assert_no_discontinuity / max_daily_jump). Only the
*rebalance schedule* differs per plan: each plan runs its own
``PortfolioSimulator`` with strategy="rebalance" and a plan-specific
``rebalance_dates`` list (none = empty).

Scenarios (both run by default):
  primary   : 2021-09-22 .. latest, short-history codes proxy-backfilled
  secondary : staggered (longest available real history, no proxy splice)

Usage:
    python scripts/backtest_rebalance_frequency.py
    python scripts/backtest_rebalance_frequency.py --scenario primary
    python scripts/backtest_rebalance_frequency.py --base-url http://localhost:8902
"""
import argparse
import csv
import json
import logging
import math
import os
import sys
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

# Reuse the engine + API price plumbing — no logic is duplicated here.
from scripts.backtest_buy_hold_vs_rebalance import (  # noqa: E402
    BacktestConfig,
    CaseSpec,
    MetricsCalculator,
    PortfolioSimulator,
    build_business_calendar,
    forward_fill_prices,
    listing_date_map,
)
from scripts.backtest_custom_basket_rebalance import (  # noqa: E402
    CASH_CODE,
    ENV_BASE,
    INITIAL_CAPITAL,
    MAX_DAILY_JUMP,
    RISK_FREE_RATE,
    assert_no_discontinuity,
    fetch_price_map,
    inject_cash_series,
    splice_proxy,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backtest_rebalance_freq")


# ---------------------------------------------------------------------------
# Basket configuration — 戦略書案B (test user actual holdings, SSOT)
# ---------------------------------------------------------------------------

GROUP_A_WEIGHTS: Dict[str, float] = {"1655": 0.15, "314A": 0.15, "1629": 0.15}
GROUP_B_WEIGHTS: Dict[str, float] = {
    "1615": 0.10,
    "2646": 0.10,
    "1618": 0.10,
    "200A": 0.10,
}
CASH_WEIGHT = 0.15

# Equity ETF codes (CASH excluded) in stable order.
ETF_CODES: List[str] = list(GROUP_A_WEIGHTS) + list(GROUP_B_WEIGHTS)


def basket_weights() -> Dict[str, float]:
    """Full target weights including the synthetic cash sleeve (sums to 1.0)."""
    w: Dict[str, float] = {}
    w.update(GROUP_A_WEIGHTS)
    w.update(GROUP_B_WEIGHTS)
    w[CASH_CODE] = CASH_WEIGHT
    return w


# Short-history threshold: < ~3y of real trading history at the window
# start makes a code a proxy-backfill candidate.
SHORT_HISTORY_DAYS = 750
MIN_PROXY_PREHISTORY_DAYS = 365 * 3  # proxy must predate target by ≥3y
MIN_OVERLAP_DAYS = 250  # corr must be measured over ≥250 shared days

PRIMARY_START = date(2021, 9, 22)

# Month-sets for the periodic full-rebalance schedule shared by both the
# periodic-only ("rebalance") plans and the hybrid (periodic + ±band) plans.
PLAN_MONTHS: Dict[str, set] = {
    "none": set(),
    "3mo": {3, 6, 9, 12},
    "6mo": {6, 12},
    "12mo": {12},
    "band_only": set(),  # no periodic full rebalance — ±band trigger only
    "3mo_band": {3, 6, 9, 12},
    "6mo_band": {6, 12},
    "12mo_band": {12},
}

# Hybrid plans reuse the existing engine's "hybrid" strategy with the
# user-confirmed band=±3% / restore_fraction=30% (carry-over compressed to
# band*0.30 = ±0.9pp). No new rebalance logic is implemented here.
HYBRID_PLANS = ("band_only", "3mo_band", "6mo_band", "12mo_band")
HYBRID_BAND = 0.03
HYBRID_RESTORE_FRACTION = 0.30

PLAN_ORDER = (
    "none",
    "3mo",
    "6mo",
    "12mo",
    "band_only",
    "3mo_band",
    "6mo_band",
    "12mo_band",
)
SCENARIOS = ("primary", "secondary")


def compute_period_end_dates(
    calendar: List[date], months: set
) -> List[date]:
    """Last trading day of each (year, month) where month is in ``months``.

    Empty ``months`` (the "none" plan) yields an empty list, i.e. the
    simulator never rebalances.
    """
    if not calendar or not months:
        return []
    by_ym: Dict[Tuple[int, int], List[date]] = {}
    for d in calendar:
        if d.month in months:
            by_ym.setdefault((d.year, d.month), []).append(d)
    return [max(by_ym[key]) for key in sorted(by_ym.keys())]


# ---------------------------------------------------------------------------
# Auto-proxy selection (data-driven; no hard-coded proxy codes)
# ---------------------------------------------------------------------------


def trim_to_clean_tail(
    day_map: Dict[date, float]
) -> Tuple[Dict[date, float], Optional[date]]:
    """Drop everything up to & incl. the last non-physical single-day jump.

    Some chart-API series carry an unadjusted split discontinuity because
    ``is_chart_applied=False`` server-side (e.g. 1655: 10:1 on 2022-02-08).
    Using such a series would corrupt the backtest, and the existing
    ``assert_no_discontinuity`` guard would abort the run. Rather than
    silently keep corrupt prefix data, we keep only the *continuous tail*
    after the last jump > ``MAX_DAILY_JUMP``; the resulting effective start
    feeds the normal short-history/auto-proxy machinery downstream. Returns
    ``(clean_map, last_jump_date_or_None)``.
    """
    items = sorted(day_map.items())
    cut = 0
    for i in range(1, len(items)):
        p0, p1 = items[i - 1][1], items[i][1]
        if p0 > 0 and abs(p1 / p0 - 1.0) > MAX_DAILY_JUMP:
            cut = i
    if cut == 0:
        return dict(day_map), None
    return dict(items[cut:]), items[cut][0]


def _http_get_json(url: str, timeout: int = 180) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_etf_meta(code: str, base_url: str) -> Tuple[Optional[int], Optional[date]]:
    """(category_id, listing_date) for ``code`` via the ETF detail API."""
    try:
        payload = _http_get_json(f"{base_url}/api/v1/etfs/{code}")
    except Exception as e:  # noqa: BLE001
        logger.warning("meta fetch failed for %s: %s", code, e)
        return None, None
    d = payload.get("data", payload) or {}
    cid = d.get("category_id")
    ld_raw = d.get("listing_date")
    ld = date.fromisoformat(ld_raw) if ld_raw else None
    return (int(cid) if cid is not None else None), ld


def list_category_codes(
    category_id: Optional[int], base_url: str
) -> List[str]:
    """ETF codes in ``category_id`` (None = all categories; paginated)."""
    codes: List[str] = []
    offset = 0
    cat = f"category_id={category_id}&" if category_id is not None else ""
    while True:
        url = f"{base_url}/api/v1/etfs?{cat}limit=100&offset={offset}"
        items = (_http_get_json(url).get("data") or [])
        if not items:
            break
        codes.extend(it["code"] for it in items if it.get("code"))
        if len(items) < 100:
            break
        offset += 100
    return codes


def _pearson(xs: List[float], ys: List[float]) -> float:
    """Pearson correlation of two equal-length sequences (0.0 if degenerate)."""
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


def _aligned_returns(
    a: Dict[date, float], b: Dict[date, float]
) -> Tuple[List[float], List[float], int]:
    """Daily pct-change pairs on dates both series have a prior point for."""
    common = sorted(set(a) & set(b))
    ra: List[float] = []
    rb: List[float] = []
    for i in range(1, len(common)):
        d0, d1 = common[i - 1], common[i]
        if a[d0] > 0 and b[d0] > 0:
            ra.append(a[d1] / a[d0] - 1.0)
            rb.append(b[d1] / b[d0] - 1.0)
    return ra, rb, len(common)


def select_proxy(
    target: str,
    target_map: Dict[date, float],
    candidates: List[str],
    raw: Dict[str, Dict[date, float]],
) -> Optional[Tuple[str, float, int]]:
    """Pick the candidate with the highest daily-return correlation.

    A candidate qualifies if it (a) starts ≥3y before the target's real
    data start and (b) overlaps the target by ≥``MIN_OVERLAP_DAYS`` shared
    trading days. Returns ``(proxy_code, corr, overlap_days)`` or ``None``.
    """
    if not target_map:
        return None
    tgt_start = min(target_map)
    best: Optional[Tuple[str, float, int]] = None
    for code in candidates:
        if code == target or code in ETF_CODES:
            continue
        cand = raw.get(code) or {}
        if not cand:
            continue
        if (tgt_start - min(cand)).days < MIN_PROXY_PREHISTORY_DAYS:
            continue
        ra, rb, overlap = _aligned_returns(target_map, cand)
        if overlap < MIN_OVERLAP_DAYS or len(ra) < MIN_OVERLAP_DAYS:
            continue
        corr = _pearson(ra, rb)
        if best is None or corr > best[1]:
            best = (code, corr, overlap)
    return best


class ProxyResolver:
    """Resolves & caches auto-selected proxies for short-history codes."""

    def __init__(self, base_url: str, period: str):
        self.base_url = base_url
        self.period = period
        self._meta: Dict[str, Tuple[Optional[int], Optional[date]]] = {}
        self.selected: Dict[str, Tuple[str, float, int]] = {}

    def meta(self, code: str) -> Tuple[Optional[int], Optional[date]]:
        if code not in self._meta:
            self._meta[code] = fetch_etf_meta(code, self.base_url)
        return self._meta[code]

    def _ensure_prices(
        self, codes: List[str], raw: Dict[str, Dict[date, float]]
    ) -> None:
        """Fetch missing candidate series, trimming corrupt prefixes."""
        need = [c for c in codes if c not in raw]
        if not need:
            return
        fetched = fetch_price_map(need, self.base_url, period=self.period)
        for c, dm in fetched.items():
            raw[c] = trim_to_clean_tail(dm)[0]

    def short_history_codes(
        self, raw: Dict[str, Dict[date, float]], window_start: date
    ) -> List[str]:
        """Equity codes whose real history at ``window_start`` is < ~3y."""
        out: List[str] = []
        for code in ETF_CODES:
            dm = raw.get(code) or {}
            if not dm:
                continue
            start = min(dm)
            recent_enough = start > window_start
            history = sum(1 for d in dm if d >= window_start)
            if recent_enough and history < SHORT_HISTORY_DAYS:
                out.append(code)
        return out

    def resolve(
        self, code: str, raw: Dict[str, Dict[date, float]]
    ) -> Optional[Tuple[str, float, int]]:
        """Auto-select a proxy for ``code`` (same-category first)."""
        if code in self.selected:
            return self.selected[code]
        cat_id, _ = self.meta(code)
        pools: List[List[str]] = []
        if cat_id is not None:
            pools.append(list_category_codes(cat_id, self.base_url))
        # fallback: every category (only if same-category yields nothing)
        chosen: Optional[Tuple[str, float, int]] = None
        for pool in pools:
            self._ensure_prices(pool, raw)
            chosen = select_proxy(code, raw.get(code) or {}, pool, raw)
            if chosen:
                break
        if chosen is None:
            allcat = list_category_codes(None, self.base_url)
            self._ensure_prices(allcat, raw)
            chosen = select_proxy(code, raw.get(code) or {}, allcat, raw)
        if chosen:
            self.selected[code] = chosen
            logger.info(
                "proxy: %s <- %s (corr=%.3f, overlap=%d days)",
                code,
                chosen[0],
                chosen[1],
                chosen[2],
            )
        else:
            logger.warning("no proxy found for short-history code %s", code)
        return chosen


# ---------------------------------------------------------------------------
# Scenario assembly
# ---------------------------------------------------------------------------


class FrequencyScenarioRunner:
    """Builds one scenario's price universe and runs the 4 frequency plans."""

    def __init__(self, config: BacktestConfig, resolver: ProxyResolver):
        self.config = config
        self.resolver = resolver
        self.metrics = MetricsCalculator(RISK_FREE_RATE)

    def prepare_prices(
        self, scenario: str, raw: Dict[str, Dict[date, float]]
    ) -> Tuple[Dict[str, Dict[date, float]], Dict[str, Tuple[str, float, int]]]:
        """Per-code price map for a scenario (CASH not yet added).

        ``primary``: short-history codes are proxy-backfilled (auto-selected
        proxy spliced at the code's real data start). ``secondary``: real
        data only (no splice).
        """
        prices: Dict[str, Dict[date, float]] = {
            c: dict(raw.get(c, {})) for c in ETF_CODES
        }
        proxies: Dict[str, Tuple[str, float, int]] = {}
        if scenario != "primary":
            return prices, proxies
        short_codes = self.resolver.short_history_codes(raw, PRIMARY_START)
        for code in short_codes:
            real = raw.get(code) or {}
            if not real:
                continue
            chosen = self.resolver.resolve(code, raw)
            if not chosen:
                continue
            proxy_code = chosen[0]
            prices[code] = splice_proxy(
                real, raw.get(proxy_code, {}), min(real)
            )
            proxies[code] = chosen
        return prices, proxies

    def scenario_window(
        self, scenario: str, prices: Dict[str, Dict[date, float]]
    ) -> Tuple[date, date]:
        """(start, end) date window for the scenario."""
        end = max(
            (max(dm) for dm in prices.values() if dm), default=date.today()
        )
        if scenario == "primary":
            start = PRIMARY_START
        else:  # secondary/staggered: earliest observation across codes
            start = min(
                (min(dm) for dm in prices.values() if dm), default=end
            )
        return start, end

    def _build_spec(self, plan: str) -> CaseSpec:
        """CaseSpec for ``plan``.

        Periodic-only plans use strategy="rebalance" (band disabled). Hybrid
        plans use the engine's existing "hybrid" strategy with the
        user-confirmed band=±3% / restore_fraction=30%; the periodic full
        rebalance schedule (if any) is supplied separately via
        ``rebalance_dates`` on the simulator.
        """
        weights = basket_weights()
        codes = ETF_CODES + [CASH_CODE]
        is_hybrid = plan in HYBRID_PLANS
        return CaseSpec(
            case_id=plan,
            group="custom",
            allocation="custom_basket",
            strategy="hybrid" if is_hybrid else "rebalance",
            codes=list(codes),
            target_weights=dict(weights),
            band=HYBRID_BAND if is_hybrid else None,
            restore_fraction=HYBRID_RESTORE_FRACTION,
        )

    def run(
        self,
        scenario: str,
        raw: Dict[str, Dict[date, float]],
        output_dir: Path,
    ) -> Dict:
        prices, proxies = self.prepare_prices(scenario, raw)
        start, end = self.scenario_window(scenario, prices)

        for code in list(prices):
            prices[code] = {
                d: p for d, p in prices[code].items() if start <= d <= end
            }

        calendar = build_business_calendar(prices, start, end)
        if not calendar:
            raise RuntimeError(f"empty calendar for scenario {scenario}")
        inject_cash_series(prices, calendar)
        assert_no_discontinuity(prices)

        listings = listing_date_map(prices)
        filled = forward_fill_prices(prices, calendar)

        results: List[Dict] = []
        for plan in PLAN_ORDER:
            rebal_dates = compute_period_end_dates(
                calendar, PLAN_MONTHS[plan]
            )
            sim = PortfolioSimulator(
                self.config,
                self._build_spec(plan),
                filled,
                calendar,
                listings,
                rebal_dates,
            )
            case = sim.run()
            case.update(self.metrics.compute(case["equity_curve"]))
            case["plan"] = plan
            results.append(case)
            if case["assert_failures"]:
                for msg in case["assert_failures"]:
                    logger.warning("[assert] %s/%s :: %s", scenario, plan, msg)
            logger.info(
                "  [%s/%s] total=%.2f%% cagr=%.2f%% sharpe=%.3f "
                "mdd=%.2f%% vol=%.2f%% rebal=%d band=%d",
                scenario,
                plan,
                case["total_return"] * 100,
                case["cagr"] * 100,
                case["sharpe"],
                case["mdd"] * 100,
                case["vol"] * 100,
                case["rebalance_count"],
                case["band_rebalance_count"],
            )

        self._write_outputs(scenario, start, end, results, proxies, output_dir)
        return {
            "scenario": scenario,
            "start": start,
            "end": end,
            "results": results,
            "proxies": proxies,
            "calendar_days": len(calendar),
        }

    def _write_outputs(
        self,
        scenario: str,
        start: date,
        end: date,
        results: List[Dict],
        proxies: Dict[str, Tuple[str, float, int]],
        output_dir: Path,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_summary_csv(results, output_dir)
        self._write_report(scenario, start, end, results, proxies, output_dir)

    @staticmethod
    def _write_summary_csv(results: List[Dict], output_dir: Path) -> None:
        path = output_dir / "summary.csv"
        fields = [
            "plan",
            "total_return",
            "cagr",
            "sharpe",
            "mdd",
            "vol",
            "rebalance_count",
            "band_rebalance_count",
            "start_value",
            "end_value",
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(fields)
            for r in results:
                w.writerow(
                    [
                        r["plan"],
                        f"{r['total_return']:.6f}",
                        f"{r['cagr']:.6f}",
                        f"{r['sharpe']:.6f}",
                        f"{r['mdd']:.6f}",
                        f"{r['vol']:.6f}",
                        r["rebalance_count"],
                        r["band_rebalance_count"],
                        f"{r['start_value']:.0f}",
                        f"{r['end_value']:.0f}",
                    ]
                )

    @staticmethod
    def _basket_line() -> str:
        return (
            "- バスケット（案B）: A群45%(1655/314A/1629 各15%) + "
            "B群40%(1615/2646/1618/200A 各10%) + 現金15%"
        )

    @staticmethod
    def _proxy_lines(
        proxies: Dict[str, Tuple[str, float, int]]
    ) -> List[str]:
        lines: List[str] = []
        lines.append("### 自動選定されたプロキシ一覧")
        lines.append("")
        if not proxies:
            lines.append("（本シナリオではプロキシ置換なし＝実データのみ）")
            lines.append("")
            return lines
        lines.append("| 対象 | プロキシ | 相関 | overlap日数 |")
        lines.append("|------|----------|------|-------------|")
        for tgt, (px, corr, ov) in sorted(proxies.items()):
            lines.append(f"| {tgt} | {px} | {corr:.3f} | {ov} |")
        lines.append("")
        return lines

    def _write_report(
        self,
        scenario: str,
        start: date,
        end: date,
        results: List[Dict],
        proxies: Dict[str, Tuple[str, float, int]],
        output_dir: Path,
    ) -> None:
        years = (end - start).days / 365.25
        best = max(results, key=lambda r: r["cagr"])
        best_sharpe = max(results, key=lambda r: r["sharpe"])
        lines: List[str] = []
        lines.append(f"# リバランス頻度比較バックテスト: {scenario}")
        lines.append("")
        lines.append(
            f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append("")
        lines.append("## 採用バスケット（案B）")
        lines.append("")
        lines.append(self._basket_line())
        lines.append("")
        lines.extend(self._proxy_lines(proxies))
        lines.append("## 前提条件")
        lines.append("")
        lines.append(f"- シナリオ: `{scenario}`")
        lines.append(f"- 期間: {start} 〜 {end}（約{years:.2f}年）")
        lines.append(f"- 初期投資: {INITIAL_CAPITAL:,.0f}円")
        lines.append(self._basket_line())
        lines.append(f"- リスクフリーレート={RISK_FREE_RATE}")
        lines.append("- 売買コスト・税金・分配金: 無視")
        lines.append("")
        lines.append("### 比較プラン")
        lines.append("")
        lines.append("| プラン | 説明 |")
        lines.append("|--------|------|")
        lines.append("| none | リバランスなし（買い持ち） |")
        lines.append("| 3mo | 3ヶ月ごと（四半期末=3/6/9/12月最終営業日） |")
        lines.append("| 6mo | 6ヶ月ごと（半期末=6/12月最終営業日） |")
        lines.append("| 12mo | 12ヶ月ごと（年末=12月最終営業日） |")
        lines.append(
            "| band_only | 定期なし・±3%乖離超で30%復元（hybrid） |"
        )
        lines.append(
            "| 3mo_band | 四半期末full + ±3%乖離超で30%復元（hybrid） |"
        )
        lines.append(
            "| 6mo_band | 半期末full + ±3%乖離超で30%復元（hybrid） |"
        )
        lines.append(
            "| 12mo_band | 年末full + ±3%乖離超で30%復元（hybrid） |"
        )
        lines.append("")
        lines.append("### 検証注記")
        lines.append("")
        lines.append(
            "1. 全価格は API（`/api/v1/etfs/chart/batch` period=20y）経由で"
            "取得。DB直接クエリ不使用（分割調整済み）。"
        )
        lines.append(
            "2. 単日ジャンプ非物理的不連続ガードを適用（1629 500:1分割対策）。"
        )
        if scenario == "primary":
            lines.append(
                "3. 短履歴銘柄（実履歴<約3年/750営業日）は同一カテゴリ内で"
                "日次リターン相関最大のETFを自動選定し、実データ開始日を"
                "アンカーとして後方バックフィル（連続性担保）。"
            )
        else:
            lines.append(
                "3. プロキシ不使用・実データのみ（staggered=段階エントリー）。"
            )
        lines.append("- 現金: 合成資産 `CASH`（全日付 価格=1.0 固定、weight 0.15）。")
        lines.append("")
        lines.append("## プラン別サマリ")
        lines.append("")
        lines.append(
            "| プラン | 総リターン | CAGR | Sharpe | MDD | 年率Vol | "
            "リバランス回数 | band発動回数 |"
        )
        lines.append(
            "|--------|-----------|------|--------|-----|---------|"
            "---------------|--------------|"
        )
        for r in results:
            lines.append(
                "| {pl} | {tr:.2%} | {cg:.2%} | {sh:.3f} | {md:.2%} | "
                "{vo:.2%} | {rc} | {bc} |".format(
                    pl=r["plan"],
                    tr=r["total_return"],
                    cg=r["cagr"],
                    sh=r["sharpe"],
                    md=r["mdd"],
                    vo=r["vol"],
                    rc=r["rebalance_count"],
                    bc=r["band_rebalance_count"],
                )
            )
        lines.append("")
        lines.append("## 所見")
        lines.append("")
        lines.append(
            f"- CAGR最良: **{best['plan']}** "
            f"(CAGR {best['cagr']:.2%}, Sharpe {best['sharpe']:.3f}, "
            f"MDD {best['mdd']:.2%})"
        )
        lines.append(
            f"- Sharpe最良: **{best_sharpe['plan']}** "
            f"(Sharpe {best_sharpe['sharpe']:.3f}, "
            f"CAGR {best_sharpe['cagr']:.2%}, MDD {best_sharpe['mdd']:.2%})"
        )
        lines.append("")
        (output_dir / "report.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Integrated cross-scenario report
# ---------------------------------------------------------------------------


_PERIODIC_ONLY = ("none", "3mo", "6mo", "12mo")
_PERIODIC_BAND = ("3mo_band", "6mo_band", "12mo_band")


def _best_of(results: List[Dict], plans: Tuple[str, ...]) -> Optional[Dict]:
    """Highest-CAGR result among ``plans`` (None if none present)."""
    pool = [r for r in results if r["plan"] in plans]
    return max(pool, key=lambda r: r["cagr"]) if pool else None


def _group_comparison_lines(scenario_outputs: List[Dict]) -> List[str]:
    """Per-scenario 3-way compare: periodic-only / periodic+band / band-only."""
    lines: List[str] = []
    for so in scenario_outputs:
        rs = so["results"]
        po = _best_of(rs, _PERIODIC_ONLY)
        pb = _best_of(rs, _PERIODIC_BAND)
        bo = next((r for r in rs if r["plan"] == "band_only"), None)
        if not (po and pb and bo):
            continue

        def fmt(r: Dict) -> str:
            return (
                f"`{r['plan']}` CAGR {r['cagr']:.2%} / Sharpe "
                f"{r['sharpe']:.3f} / MDD {r['mdd']:.2%} / "
                f"band {r['band_rebalance_count']}回"
            )

        lines.append(f"- **{so['scenario']}**")
        lines.append(f"  - 定期のみ最良: {fmt(po)}")
        lines.append(f"  - 定期+band最良: {fmt(pb)}")
        lines.append(f"  - band単独: {fmt(bo)}")
        ranked = sorted(
            [("定期のみ", po), ("定期+band", pb), ("band単独", bo)],
            key=lambda kv: kv[1]["cagr"],
            reverse=True,
        )
        order = " > ".join(
            f"{label}({r['cagr']:.2%})" for label, r in ranked
        )
        lines.append(f"  - CAGR順位: {order}")
    return lines


def write_integrated_report(
    root_dir: Path, scenario_outputs: List[Dict]
) -> Path:
    lines: List[str] = []
    lines.append("# リバランス頻度比較バックテスト（統合）")
    lines.append("")
    lines.append(
        f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    lines.append("")
    lines.append("## 採用バスケット（案B = test ユーザー実保有 / SSOT）")
    lines.append("")
    lines.append(
        "- A群45%: 1655=15% / 314A=15% / 1629=15%"
    )
    lines.append(
        "- B群40%: 1615=10% / 2646=10% / 1618=10% / 200A=10%"
    )
    lines.append("- 現金15%: 合成資産 `CASH`（価格=1.0 固定）")
    lines.append(f"- 初期投資: {INITIAL_CAPITAL:,.0f}円 / 合計 weight 1.00")
    lines.append("")
    lines.append("## 自動選定されたプロキシ一覧（シナリオ別）")
    lines.append("")
    lines.append("| シナリオ | 対象 | プロキシ | 相関 | overlap日数 |")
    lines.append("|----------|------|----------|------|-------------|")
    any_proxy = False
    for so in scenario_outputs:
        px = so.get("proxies") or {}
        if not px:
            lines.append(
                f"| {so['scenario']} | (なし) | 実データのみ | - | - |"
            )
            continue
        any_proxy = True
        for tgt, (p, corr, ov) in sorted(px.items()):
            lines.append(
                f"| {so['scenario']} | {tgt} | {p} | {corr:.3f} | {ov} |"
            )
    lines.append("")
    if any_proxy:
        lines.append(
            "プロキシは同一カテゴリ内で対象銘柄の日次リターンとの"
            "Pearson相関が最大のETFをデータ駆動で自動選定（ハードコード"
            "なし）。実データ開始日をアンカーに後方スプライス。"
        )
        lines.append("")
    lines.append("## 比較プラン")
    lines.append("")
    lines.append(
        "- 定期のみ: none(買い持ち) / 3mo(四半期末) / 6mo(半期末) / "
        "12mo(年末)"
    )
    lines.append(
        "- band単独: band_only（定期full なし・±3%乖離超で30%復元）"
    )
    lines.append(
        "- 定期+band: 3mo_band / 6mo_band / 12mo_band（各定期full + "
        "±3%乖離超で30%復元、hybrid戦略）"
    )
    lines.append("- 売買コスト・税金・分配金: 無視")
    lines.append("- 全価格は API 経由（DB直接クエリ不使用・分割調整済み）")
    lines.append("")
    lines.append("## シナリオ別 全プラン一覧")
    lines.append("")
    lines.append(
        "| シナリオ | 期間 | プラン | 総リターン | CAGR | Sharpe | MDD | "
        "年率Vol | リバランス回数 | band発動回数 |"
    )
    lines.append(
        "|----------|------|--------|-----------|------|--------|-----|"
        "---------|---------------|--------------|"
    )
    for so in scenario_outputs:
        period = f"{so['start']}〜{so['end']}"
        for r in so["results"]:
            lines.append(
                "| {sc} | {pe} | {pl} | {tr:.2%} | {cg:.2%} | {sh:.3f} | "
                "{md:.2%} | {vo:.2%} | {rc} | {bc} |".format(
                    sc=so["scenario"],
                    pe=period,
                    pl=r["plan"],
                    tr=r["total_return"],
                    cg=r["cagr"],
                    sh=r["sharpe"],
                    md=r["mdd"],
                    vo=r["vol"],
                    rc=r["rebalance_count"],
                    bc=r["band_rebalance_count"],
                )
            )
    lines.append("")
    lines.append("## シナリオ別 最良プラン")
    lines.append("")
    lines.append(
        "| シナリオ | 期間 | CAGR最良 | CAGR | Sharpe最良 | Sharpe | "
        "MDD最小 | MDD |"
    )
    lines.append(
        "|----------|------|----------|------|------------|--------|"
        "---------|-----|"
    )
    for so in scenario_outputs:
        rs = so["results"]
        best_cagr = max(rs, key=lambda r: r["cagr"])
        best_shp = max(rs, key=lambda r: r["sharpe"])
        best_mdd = max(rs, key=lambda r: r["mdd"])  # mdd<=0; max = shallowest
        years = (so["end"] - so["start"]).days / 365.25
        lines.append(
            "| {sc} | {pe}（約{yr:.2f}年） | {bc} | {cg:.2%} | {bs} | "
            "{sh:.3f} | {bm} | {md:.2%} |".format(
                sc=so["scenario"],
                pe=f"{so['start']}〜{so['end']}",
                yr=years,
                bc=best_cagr["plan"],
                cg=best_cagr["cagr"],
                bs=best_shp["plan"],
                sh=best_shp["sharpe"],
                bm=best_mdd["plan"],
                md=best_mdd["mdd"],
            )
        )
    lines.append("")
    lines.append("## 所見")
    lines.append("")
    for so in scenario_outputs:
        rs = so["results"]
        none = next((r for r in rs if r["plan"] == "none"), None)
        best = max(rs, key=lambda r: r["cagr"])
        if none is None:
            continue
        delta = best["cagr"] - none["cagr"]
        lines.append(
            f"- **{so['scenario']}**: CAGR最良は `{best['plan']}` "
            f"(CAGR {best['cagr']:.2%})。none比 CAGR 差 {delta:+.2%}、"
            f"最良MDD {best['mdd']:.2%} / none MDD {none['mdd']:.2%}。"
        )
    lines.append("")
    lines.append("### 定期のみ vs 定期+band vs band単独")
    lines.append("")
    lines.extend(_group_comparison_lines(scenario_outputs))
    lines.append("")
    lines.append(
        "- primary は短履歴銘柄を相関最大プロキシで延伸した参考値。"
        "secondary は段階エントリーで最長の実履歴のみを使う。"
    )
    lines.append("")
    path = root_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--scenario",
        choices=list(SCENARIOS) + ["all"],
        default="all",
        help="scenario to run (default: both)",
    )
    p.add_argument("--env", choices=list(ENV_BASE), default="dev")
    p.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="override API base URL (default: from --env)",
    )
    p.add_argument(
        "--period",
        type=str,
        default="20y",
        help="chart batch API period (default: 20y)",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="output root (default: reports/backtest/{ts}_rebalance_frequency)",
    )
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
            resolve_reports_root()
            / "backtest"
            / f"{ts}_rebalance_frequency"
        )
    root_dir.mkdir(parents=True, exist_ok=True)
    logger.info("output root: %s", root_dir)

    scenarios = (
        list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    )

    logger.info("fetching basket prices via API: %s", base_url)
    raw = fetch_price_map(ETF_CODES, base_url, period=args.period)
    for code in ETF_CODES:
        cleaned, jump = trim_to_clean_tail(raw.get(code) or {})
        if jump is not None:
            logger.warning(
                "series %s: dropped corrupt prefix (unadjusted split / "
                "is_chart_applied=False); clean tail starts %s (%d days)",
                code,
                jump,
                len(cleaned),
            )
        raw[code] = cleaned

    config = BacktestConfig(initial_capital=INITIAL_CAPITAL)
    resolver = ProxyResolver(base_url, args.period)
    runner = FrequencyScenarioRunner(config, resolver)

    scenario_outputs: List[Dict] = []
    for scenario in scenarios:
        out_dir = root_dir / scenario
        logger.info("=== scenario: %s ===", scenario)
        so = runner.run(scenario, raw, out_dir)
        scenario_outputs.append(so)

    integrated = write_integrated_report(root_dir, scenario_outputs)
    logger.info("integrated report: %s", integrated)

    total_fail = sum(
        len(r["assert_failures"])
        for so in scenario_outputs
        for r in so["results"]
    )
    if total_fail:
        logger.warning(
            "[assert] %d coherence violations across all cases", total_fail
        )
    else:
        logger.info("[assert] all coherence checks PASSED")

    print()
    print("=== SUMMARY (all scenarios) ===")
    for so in scenario_outputs:
        print(f"--- {so['scenario']} ({so['start']}..{so['end']}) ---")
        px = so.get("proxies") or {}
        if px:
            for tgt, (p, corr, ov) in sorted(px.items()):
                print(
                    f"  proxy: {tgt} <- {p} (corr={corr:.3f}, "
                    f"overlap={ov} days)"
                )
        for r in so["results"]:
            print(
                f"{r['plan']:10s} total={r['total_return']*100:7.2f}%  "
                f"cagr={r['cagr']*100:6.2f}%  vol={r['vol']*100:5.2f}%  "
                f"sharpe={r['sharpe']:6.3f}  mdd={r['mdd']*100:7.2f}%  "
                f"rebal={r['rebalance_count']:3d}  "
                f"band={r['band_rebalance_count']:3d}"
            )
    print()
    print(f"output root: {root_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
