#!/usr/bin/env python3
"""Custom 8-ETF basket rebalance backtest (3 scenarios x 5 strategies).

Reuses the price-source-agnostic engine from
``backtest_buy_hold_vs_rebalance.py`` (PortfolioSimulator / MetricsCalculator /
CaseSpec / calendar+forward-fill helpers). Only the *price source* is replaced:
prices come from the chart batch API (split-adjusted, API-only — no DB reads),
a synthetic ``CASH`` series (price=1.0) models the 10% cash sleeve, and 200A is
back-filled with a 2644 proxy splice for the extended-history scenario.

Basket:
  Group A (45%): 2559=15%, 1540=15%, 1629=15%
  Group B (45%): 2646=9%, 1306=9%, 1618=9%, 200A=9%, 1615=9%
  Cash:    10%  (synthetic "CASH" code, price=1.0)

Scenarios (default = run all three):
  proxy_extended : 2021-09-22 .. 2026-05-15, 200A spliced from 2644
  strict_common  : 2024-06-04 .. 2026-05-15, 200A real data only
  staggered      : longest available, staggered entry per listing date

Usage:
    python scripts/backtest_custom_basket_rebalance.py
    python scripts/backtest_custom_basket_rebalance.py --scenario strict_common
    python scripts/backtest_custom_basket_rebalance.py --base-url http://localhost:8902
"""
import argparse
import json
import logging
import os
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

# --- env bootstrap (production friendly) ---
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

# Reuse the engine — only the price source differs in this script.
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backtest_custom_basket")


# ---------------------------------------------------------------------------
# Basket configuration
# ---------------------------------------------------------------------------

CASH_CODE = "CASH"

GROUP_A_WEIGHTS: Dict[str, float] = {"2559": 0.15, "1540": 0.15, "1629": 0.15}
GROUP_B_WEIGHTS: Dict[str, float] = {
    "2646": 0.09,
    "1306": 0.09,
    "1618": 0.09,
    "200A": 0.09,
    "1615": 0.09,
}
CASH_WEIGHT = 0.10

# 200A proxy splice: pre-anchor history is reconstructed from 2644 daily
# returns; on/after the anchor the real 200A series is used as-is.
PROXY_TARGET = "200A"
PROXY_SOURCE = "2644"
PROXY_ANCHOR = date(2024, 6, 4)  # 200A first real trading day
PROXY_CORR_MONTHLY = 0.9815  # 200A vs 2644 monthly correlation (given)

INITIAL_CAPITAL = 1_000_000.0
RESTORE_FRACTION = 0.70
RISK_FREE_RATE = 0.0
MAX_DAILY_JUMP = 0.60  # non-physical discontinuity guard (CLAUDE.md)

ENV_BASE = {
    "dev": "http://localhost:8902",
    "prod": "https://kima3.net/japan-etf-analyzer",
}

SCENARIOS = ("proxy_extended", "strict_common", "staggered")

# Equity ETF codes (CASH excluded) in stable order.
ETF_CODES: List[str] = list(GROUP_A_WEIGHTS) + list(GROUP_B_WEIGHTS)


def basket_weights() -> Dict[str, float]:
    """Full target weights including the synthetic cash sleeve (sums to 1.0)."""
    w: Dict[str, float] = {}
    w.update(GROUP_A_WEIGHTS)
    w.update(GROUP_B_WEIGHTS)
    w[CASH_CODE] = CASH_WEIGHT
    return w


# ---------------------------------------------------------------------------
# Price source (API only — never reads the DB)
# ---------------------------------------------------------------------------


def _http_get_json(url: str, timeout: int = 180) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_price_map(
    codes: List[str], base_url: str, period: str = "20y"
) -> Dict[str, Dict[date, float]]:
    """Fetch split-adjusted daily close per code via the chart batch API.

    API-only (split-adjusted, is_chart_applied honored server-side). Never
    touches the DB (CLAUDE.md 計算前必須チェック / 株式分割の管理).
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


def max_daily_jump(day_map: Dict[date, float]) -> float:
    """Largest |consecutive-day return| (0.0 if <2 points).

    Data-integrity guard: a single-day move above MAX_DAILY_JUMP is a
    non-physical listing-unit/currency discontinuity, not a real move.
    """
    items = sorted(day_map.items())
    worst = 0.0
    for i in range(1, len(items)):
        p0 = items[i - 1][1]
        p1 = items[i][1]
        if p0 > 0:
            worst = max(worst, abs(p1 / p0 - 1.0))
    return worst


def assert_no_discontinuity(price_map: Dict[str, Dict[date, float]]) -> None:
    """Abort if any equity series has a non-physical single-day jump."""
    for code, dm in price_map.items():
        if code == CASH_CODE:
            continue
        jump = max_daily_jump(dm)
        if jump > MAX_DAILY_JUMP:
            raise RuntimeError(
                f"series {code} has a non-physical discontinuity "
                f"(max_daily_jump={jump:.4f} > {MAX_DAILY_JUMP}); aborting "
                f"to avoid a misleading report (CLAUDE.md 計算前必須チェック)"
            )


def splice_proxy(
    target_map: Dict[date, float],
    source_map: Dict[date, float],
    anchor: date,
) -> Dict[date, float]:
    """Back-fill ``target`` before ``anchor`` using ``source`` daily returns.

    On/after ``anchor`` the real target series is kept verbatim. Before the
    anchor, the target level is reconstructed by walking source daily returns
    backward from the target's anchor-day open level so the spliced series is
    continuous (no jump at the splice point).
    """
    if not target_map or not source_map:
        return dict(target_map)
    target_dates = sorted(d for d in target_map if d >= anchor)
    if not target_dates:
        return dict(target_map)
    anchor_eff = target_dates[0]
    anchor_level = target_map[anchor_eff]

    src_dates = sorted(source_map)
    # source observations strictly before the effective anchor, oldest->newest
    pre = [d for d in src_dates if d < anchor_eff]
    spliced: Dict[date, float] = {}
    if pre:
        # ratio so source[last_pre] maps onto anchor_level (continuity).
        scale = anchor_level / source_map[pre[-1]]
        for d in pre:
            spliced[d] = source_map[d] * scale
    # real target data verbatim from the anchor onward
    for d in target_dates:
        spliced[d] = target_map[d]
    return spliced


def splice_proxy_chain(
    stages: List[tuple],
) -> Dict[date, float]:
    """Multi-stage backward splice over an ordered list of ``stages``.

    ``stages`` is newest-first: ``[(series, anchor), ...]``. The first entry
    is the real/most-recent series (its ``anchor`` is the date from which it
    is kept verbatim — pass ``None`` to keep the whole series). Each older
    stage back-fills the levels strictly before the *running effective
    anchor* using that stage's daily returns, scaled for continuity at the
    splice point (same continuity contract as :func:`splice_proxy`, applied
    transitively). Returns one continuous {date: level} map with no jumps at
    any splice point.

    This is a pure superset of two-stage ``splice_proxy`` behaviour; the
    existing three-scenario script does not call it, so its behaviour is
    unchanged (backward compatible).
    """
    stages = [(dict(s or {}), a) for s, a in stages if s]
    if not stages:
        return {}
    base_series, base_anchor = stages[0]
    if base_anchor is not None:
        kept = {d: p for d, p in base_series.items() if d >= base_anchor}
    else:
        kept = dict(base_series)
    if not kept:
        return {}
    spliced: Dict[date, float] = dict(kept)
    # running effective anchor: oldest date currently materialised
    eff_anchor = min(spliced)
    eff_level = spliced[eff_anchor]
    for src_series, _ in stages[1:]:
        src_dates = sorted(src_series)
        pre = [d for d in src_dates if d < eff_anchor]
        if not pre:
            continue
        scale = eff_level / src_series[pre[-1]]
        for d in pre:
            spliced[d] = src_series[d] * scale
        eff_anchor = pre[0]
        eff_level = spliced[eff_anchor]
    return spliced


def inject_cash_series(
    price_map: Dict[str, Dict[date, float]], calendar: List[date]
) -> None:
    """Add a synthetic CASH series (price=1.0) for every calendar date."""
    price_map[CASH_CODE] = {d: 1.0 for d in calendar}


# ---------------------------------------------------------------------------
# Scenario assembly
# ---------------------------------------------------------------------------


class CustomScenarioRunner:
    """Builds one scenario's price universe and runs the 5 strategies."""

    STRATEGIES = ("buy_hold", "rebalance", "hybrid", "hybrid", "hybrid")
    HYBRID_BANDS = (0.01, 0.02, 0.03)

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.metrics = MetricsCalculator(RISK_FREE_RATE)

    def build_specs(self) -> List[CaseSpec]:
        weights = basket_weights()
        codes = ETF_CODES + [CASH_CODE]
        specs: List[CaseSpec] = [
            CaseSpec(
                case_id="buy_hold",
                group="custom",
                allocation="custom_basket",
                strategy="buy_hold",
                codes=list(codes),
                target_weights=dict(weights),
            ),
            CaseSpec(
                case_id="rebalance_q",
                group="custom",
                allocation="custom_basket",
                strategy="rebalance",
                codes=list(codes),
                target_weights=dict(weights),
            ),
        ]
        for band in self.HYBRID_BANDS:
            specs.append(
                CaseSpec(
                    case_id=f"hybrid_b{int(band * 100):02d}",
                    group="custom",
                    allocation="custom_basket",
                    strategy="hybrid",
                    codes=list(codes),
                    target_weights=dict(weights),
                    band=band,
                    restore_fraction=RESTORE_FRACTION,
                )
            )
        return specs

    def prepare_prices(
        self,
        scenario: str,
        raw: Dict[str, Dict[date, float]],
    ) -> Dict[str, Dict[date, float]]:
        """Return the per-code price map for a scenario (CASH not yet added)."""
        prices: Dict[str, Dict[date, float]] = {
            c: dict(raw.get(c, {})) for c in ETF_CODES
        }
        if scenario == "proxy_extended":
            prices[PROXY_TARGET] = splice_proxy(
                raw.get(PROXY_TARGET, {}),
                raw.get(PROXY_SOURCE, {}),
                PROXY_ANCHOR,
            )
        # strict_common / staggered: 200A real data only (no proxy splice)
        return prices

    def scenario_window(
        self, scenario: str, prices: Dict[str, Dict[date, float]]
    ) -> tuple:
        """(start, end) date window for the scenario."""
        end = max(
            (max(dm) for dm in prices.values() if dm), default=date.today()
        )
        if scenario == "proxy_extended":
            start = date(2021, 9, 22)
        elif scenario == "strict_common":
            start = date(2024, 6, 4)
        else:  # staggered: earliest observation across all equity codes
            start = min(
                (min(dm) for dm in prices.values() if dm), default=end
            )
        return start, end

    def run(
        self,
        scenario: str,
        raw: Dict[str, Dict[date, float]],
        output_dir: Path,
    ) -> Dict:
        prices = self.prepare_prices(scenario, raw)
        start, end = self.scenario_window(scenario, prices)

        # restrict to window
        for code in list(prices):
            prices[code] = {
                d: p for d, p in prices[code].items() if start <= d <= end
            }

        for sc in (
            "proxy_extended",
            "strict_common",
        ):
            if scenario == sc:
                # full-history scenarios: every equity code must cover day 1
                self._assert_all_present_on(prices, start, scenario)

        calendar = build_business_calendar(prices, start, end)
        if not calendar:
            raise RuntimeError(f"empty calendar for scenario {scenario}")
        inject_cash_series(prices, calendar)
        assert_no_discontinuity(prices)

        listings = listing_date_map(prices)
        filled = forward_fill_prices(prices, calendar)
        rebalance_dates = compute_quarter_end_dates(calendar)
        logger.info(
            "[%s] window=%s..%s calendar=%d quarter_ends=%d listings=%s",
            scenario,
            start,
            end,
            len(calendar),
            len(rebalance_dates),
            {k: v.isoformat() for k, v in sorted(listings.items())},
        )

        results: List[Dict] = []
        for spec in self.build_specs():
            sim = PortfolioSimulator(
                self.config,
                spec,
                filled,
                calendar,
                listings,
                rebalance_dates,
            )
            case = sim.run()
            case.update(self.metrics.compute(case["equity_curve"]))
            results.append(case)
            if case["assert_failures"]:
                for msg in case["assert_failures"]:
                    logger.warning("[assert] %s :: %s", spec.case_id, msg)
            logger.info(
                "  [%s/%s] total=%.2f%% cagr=%.2f%% mdd=%.2f%% "
                "rebal=%d band=%d",
                scenario,
                spec.case_id,
                case["total_return"] * 100,
                case["cagr"] * 100,
                case["mdd"] * 100,
                case["rebalance_count"],
                case["band_rebalance_count"],
            )

        writer = ReportWriter(self.config, results, output_dir, listings)
        writer.write_summary_csv()
        writer.write_equity_curves_csv()
        writer.write_events_csv()
        chart_path = writer.try_write_chart()
        self._write_scenario_report(
            scenario, start, end, results, listings, output_dir
        )
        return {
            "scenario": scenario,
            "start": start,
            "end": end,
            "results": results,
            "listings": listings,
            "calendar_days": len(calendar),
            "rebalance_dates": len(rebalance_dates),
            "chart": chart_path is not None,
        }

    @staticmethod
    def _assert_all_present_on(
        prices: Dict[str, Dict[date, float]], start: date, scenario: str
    ) -> None:
        """Every equity code must have an observation within ~5 trading days
        of the scenario start (full-history scenarios only)."""
        for code in ETF_CODES:
            dm = prices.get(code, {})
            if not dm:
                raise RuntimeError(
                    f"[{scenario}] {code} has no data in window"
                )
            first = min(dm)
            if (first - start).days > 7:
                raise RuntimeError(
                    f"[{scenario}] {code} first obs {first} is far from "
                    f"window start {start} (expected all codes present)"
                )

    def _write_scenario_report(
        self,
        scenario: str,
        start: date,
        end: date,
        results: List[Dict],
        listings: Dict[str, date],
        output_dir: Path,
    ) -> Path:
        years = (end - start).days / 365.25
        lines: List[str] = []
        lines.append(f"# カスタム8銘柄バスケット バックテスト: {scenario}")
        lines.append("")
        lines.append(
            f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append("")
        lines.append("## 前提条件")
        lines.append("")
        lines.append(f"- シナリオ: `{scenario}`")
        lines.append(f"- 期間: {start} 〜 {end}（約{years:.2f}年）")
        lines.append(f"- 初期投資: {INITIAL_CAPITAL:,.0f}円")
        lines.append(
            "- バスケット: A群45%(2559/1540/1629 各15%) + "
            "B群45%(2646/1306/1618/200A/1615 各9%) + 現金10%"
        )
        lines.append(
            f"- restore_fraction={RESTORE_FRACTION}, "
            f"リスクフリーレート={RISK_FREE_RATE}"
        )
        lines.append("- 売買コスト・税金・分配金: 無視")
        lines.append("")
        lines.append("### 検証注記")
        lines.append("")
        lines.append(
            "1. 全価格は API（`/api/v1/etfs/chart/batch` period=20y）経由で"
            "取得。DB直接クエリ不使用。"
        )
        lines.append(
            f"2. 単日ジャンプ > {MAX_DAILY_JUMP:.0%} 除外フィルタを適用"
            "（非物理的不連続ガード）。"
        )
        lines.append(
            "3. 1629(2026-03-30/500倍)・1306(2026-03-30/10倍) は "
            "is_chart_applied=True でAPI系列調整済み・DB生データ不使用。"
        )
        lines.append(
            "4. 2559の分割(2026-06-05)は観測期間外のため無影響。"
        )
        if scenario == "proxy_extended":
            lines.append(
                f"5. 200A プロキシ・スプライス: アンカー {PROXY_ANCHOR} "
                f"（200A実初値日）以前は代替銘柄 {PROXY_SOURCE}"
                "（グローバルX 半導体関連-日本株式, データ開始2021-09-22, "
                f"200Aとの月次相関 {PROXY_CORR_MONTHLY}）の日次リターンで"
                "後方バックフィル。アンカー以降は200A実データ。"
            )
        else:
            lines.append(
                "5. 200A はプロキシ不使用・実データのみ。"
            )
        lines.append("- 現金: 合成資産 `CASH`（全日付 価格=1.0 固定）。")
        lines.append("")
        lines.append("### 銘柄別データ開始日（本シナリオ窓内）")
        lines.append("")
        lines.append("| 銘柄 | データ開始 |")
        lines.append("|------|-----------|")
        for c in ETF_CODES + [CASH_CODE]:
            ld = listings.get(c)
            lines.append(f"| {c} | {ld} |")
        lines.append("")
        lines.append("## 戦略別サマリ")
        lines.append("")
        lines.append(
            "| 戦略 | 総リターン | CAGR | 年率Vol | Sharpe | MDD | "
            "リバランス | バンド発火 |"
        )
        lines.append(
            "|------|-----------|------|---------|--------|-----|"
            "-----------|-----------|"
        )
        for r in results:
            lines.append(
                "| {cid} | {tr:.2%} | {cg:.2%} | {vo:.2%} | {sh:.3f} | "
                "{md:.2%} | {rc} | {bc} |".format(
                    cid=r["case_id"],
                    tr=r["total_return"],
                    cg=r["cagr"],
                    vo=r["vol"],
                    sh=r["sharpe"],
                    md=r["mdd"],
                    rc=r["rebalance_count"],
                    bc=r["band_rebalance_count"],
                )
            )
        lines.append("")
        ranked = sorted(
            results, key=lambda r: r["cagr"], reverse=True
        )
        if ranked:
            b = ranked[0]
            lines.append(
                f"- 最良(CAGR基準): **{b['case_id']}** "
                f"(CAGR {b['cagr']:.2%}, Sharpe {b['sharpe']:.3f}, "
                f"MDD {b['mdd']:.2%})"
            )
            lines.append("")
        path = output_dir / "report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# Integrated cross-scenario report
# ---------------------------------------------------------------------------


def write_integrated_report(
    root_dir: Path, scenario_outputs: List[Dict]
) -> Path:
    lines: List[str] = []
    lines.append("# カスタム8銘柄バスケット リバランス バックテスト（統合）")
    lines.append("")
    lines.append(
        f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    lines.append("")
    lines.append("## 1. 前提条件")
    lines.append("")
    lines.append(
        "- バスケット: A群45%(2559=15%/1540=15%/1629=15%) + "
        "B群45%(2646=9%/1306=9%/1618=9%/200A=9%/1615=9%) + 現金10%"
    )
    lines.append(f"- 初期投資: {INITIAL_CAPITAL:,.0f}円")
    lines.append(
        f"- restore_fraction={RESTORE_FRACTION}、"
        f"リスクフリーレート={RISK_FREE_RATE}"
    )
    lines.append(
        "- 比較5戦略: buy_hold / rebalance(四半期末) / "
        "hybrid band=0.01 / 0.02 / 0.03"
    )
    lines.append("- 売買コスト・税金・分配金: 無視")
    lines.append("")
    lines.append("## 2. 検証注記")
    lines.append("")
    lines.append(
        "1. 全価格は API（`/api/v1/etfs/chart/batch` period=20y）経由。"
        "DB直接クエリ不使用。"
    )
    lines.append(
        f"2. 単日ジャンプ > {MAX_DAILY_JUMP:.0%} 除外フィルタを適用。"
    )
    lines.append(
        "3. 1629(2026-03-30/500倍)・1306(2026-03-30/10倍) は "
        "is_chart_applied=True でAPI系列調整済み・DB生データ不使用。"
    )
    lines.append("4. 2559の分割(2026-06-05)は観測期間外のため無影響。")
    lines.append(
        f"5. 200A スプライス: proxy_extended のみ アンカー {PROXY_ANCHOR}"
        f"以前を {PROXY_SOURCE}（月次相関 {PROXY_CORR_MONTHLY}）で"
        "後方バックフィル。strict_common / staggered は実データのみ。"
    )
    lines.append("- 現金: 合成資産 `CASH`（全日付 価格=1.0 固定）。")
    lines.append("")
    lines.append("## 3. シナリオ別 全戦略一覧")
    lines.append("")
    lines.append(
        "| シナリオ | 期間 | 戦略 | 総リターン | CAGR | Vol | Sharpe | "
        "MDD | リバランス | バンド |"
    )
    lines.append(
        "|----------|------|------|-----------|------|-----|--------|"
        "-----|-----------|--------|"
    )
    for so in scenario_outputs:
        period = f"{so['start']}〜{so['end']}"
        for r in so["results"]:
            lines.append(
                "| {sc} | {pe} | {cid} | {tr:.2%} | {cg:.2%} | {vo:.2%} | "
                "{sh:.3f} | {md:.2%} | {rc} | {bc} |".format(
                    sc=so["scenario"],
                    pe=period,
                    cid=r["case_id"],
                    tr=r["total_return"],
                    cg=r["cagr"],
                    vo=r["vol"],
                    sh=r["sharpe"],
                    md=r["mdd"],
                    rc=r["rebalance_count"],
                    bc=r["band_rebalance_count"],
                )
            )
    lines.append("")
    lines.append("## 4. シナリオ間比較（各シナリオの最良戦略・CAGR基準）")
    lines.append("")
    lines.append(
        "| シナリオ | 期間 | 最良戦略 | CAGR | MDD | Sharpe | "
        "総リターン | リバランス回数 |"
    )
    lines.append(
        "|----------|------|----------|------|-----|--------|"
        "-----------|----------------|"
    )
    for so in scenario_outputs:
        best = max(so["results"], key=lambda r: r["cagr"])
        years = (so["end"] - so["start"]).days / 365.25
        lines.append(
            "| {sc} | {pe}（約{yr:.2f}年） | {cid} | {cg:.2%} | {md:.2%} | "
            "{sh:.3f} | {tr:.2%} | {rc} |".format(
                sc=so["scenario"],
                pe=f"{so['start']}〜{so['end']}",
                yr=years,
                cid=best["case_id"],
                cg=best["cagr"],
                md=best["mdd"],
                sh=best["sharpe"],
                tr=best["total_return"],
                rc=best["rebalance_count"],
            )
        )
    lines.append("")
    lines.append("## 5. 所見")
    lines.append("")
    for so in scenario_outputs:
        bh = next(
            (r for r in so["results"] if r["case_id"] == "buy_hold"), None
        )
        best = max(so["results"], key=lambda r: r["cagr"])
        if bh is None:
            continue
        delta = best["cagr"] - bh["cagr"]
        lines.append(
            f"- **{so['scenario']}**: 最良は `{best['case_id']}` "
            f"(CAGR {best['cagr']:.2%})。B&H比 CAGR 差 {delta:+.2%}、"
            f"最良MDD {best['mdd']:.2%} / B&H MDD {bh['mdd']:.2%}。"
        )
    lines.append("")
    lines.append(
        "- proxy_extended は2644スプライスで履歴を延伸した参考値であり、"
        "200A実データ区間は strict_common と一致する。staggered は段階"
        "エントリーで最長履歴を使うため初期は上場済み銘柄のみで"
        "比率再正規化される点に留意。"
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
        help="scenario to run (default: all 3)",
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
        help="output root (default: reports/backtest/{ts}_custom_basket_rebalance)",
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
            / f"{ts}_custom_basket_rebalance"
        )
    root_dir.mkdir(parents=True, exist_ok=True)
    logger.info("output root: %s", root_dir)

    scenarios = (
        list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    )

    # Fetch once: equity codes + proxy source (200A spliced from 2644).
    fetch_codes = ETF_CODES + [PROXY_SOURCE]
    logger.info("fetching prices via API: %s", base_url)
    raw = fetch_price_map(fetch_codes, base_url, period=args.period)

    # config is reused only for tolerances / initial_capital.
    config = BacktestConfig(initial_capital=INITIAL_CAPITAL)
    runner = CustomScenarioRunner(config)

    scenario_outputs: List[Dict] = []
    for scenario in scenarios:
        out_dir = root_dir / scenario
        out_dir.mkdir(parents=True, exist_ok=True)
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
        for r in so["results"]:
            print(
                f"{r['case_id']:14s} total={r['total_return']*100:7.2f}%  "
                f"cagr={r['cagr']*100:6.2f}%  vol={r['vol']*100:5.2f}%  "
                f"sharpe={r['sharpe']:6.3f}  mdd={r['mdd']*100:7.2f}%  "
                f"rebal={r['rebalance_count']:3d}  band={r['band_rebalance_count']}"
            )
    print()
    print(f"output root: {root_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
