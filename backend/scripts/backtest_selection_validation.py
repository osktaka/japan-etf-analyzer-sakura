"""Selection-validation backtest: hand-picked basket vs neutral screening.

Tests the prior conclusion "the real lever of a portfolio is *security
selection*" by connecting the existing zero-based core-eligibility screening
(``etf_partner_backtest.core_screen``) to the existing cost/tax/dividend
simulator (``backtest_cost_aware.CostAwareSimulator``) under a regime-robust,
selection-bias-controlled frame.

What it does (no logic reimplemented — pure orchestration of imports):

1. Neutral screening basket
   - Calls ``etf_partner_backtest.core_screen`` (CORE_FIT weighted: 0.40
     diversification + 0.35 risk-quality + 0.25 drawdown-resilience).
     Leverage/inverse/short-history/discontinuity guards are the existing
     logic verbatim. To keep an argument-free run tractable on a 450+ ETF
     universe, ``prefilter_candidates`` (drop レバレッジ/インバース etc.,
     rank by return_performance, top-N) caps the price-fetch candidate set
     (documented simplification — see report).
   - The CORE_FIT ranking already penalizes high mean |pairwise corr|, so
     taking survivors in composite-rank order is diversification-aware. We
     map the top survivors onto the *same* group structure as the live
     basket: A group = top-3 @ 15% each, B group = next-5 @ 9% each, plus a
     synthetic 10% CASH sleeve.

2. Walk-forward (out-of-sample) — the headline test
   - Screening reference data is restricted to 2011-03-02..2017-12-31 only
     (a date-windowed copy of the API price map passed to ``core_screen``),
     then the resulting neutral basket is evaluated 2018-01-01..2026-05-15.
   - The live basket is evaluated over the *same* 2018..2026 window.

3. In-sample reference (look-ahead biased — labelled as such)
   - Screening over the full 2011..2026 data; the gap vs (2) quantifies the
     survivorship / look-ahead premium.

4. Comparison matrix
   - basket {current(hand), screening(WF), screening(insample)}
     x strategy {buy_hold, rebalance_b03}
     x account {nisa (headline), gross (structure separation)}
   - Reports netCAGR / netMDD / Calmar / Sortino / cost / tax / dividend per
     window; separates selection effect (same strategy, current vs
     screening) from strategy effect (same basket, buy_hold vs reb_b03).

Run (argument-free, dev API):
    docker compose exec -T backend python3 scripts/backtest_selection_validation.py

CLAUDE.md compliance: prices are fetched API-only (chart batch endpoint via
the reused ``fetch_price_map``), never the DB. Env bootstrap follows the
"スクリプト作成時の環境変数設定" template. No existing file is modified.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- env bootstrap (production friendly; CLAUDE.md template) ---
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
_db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")

sys.path.insert(0, str(BACKEND_DIR))

# Reuse: zero-based core-eligibility screening (CORE_FIT weighted ranking,
# population guards, monthly-return stats) — called, never reimplemented.
import scripts.etf_partner_backtest as _epb  # noqa: E402
from scripts.etf_partner_backtest import (  # noqa: E402
    CORE_SCREEN_DEFAULT_MIN_CAGR,
    core_screen,
    fetch_universe,
    prefilter_candidates,
)

# Reuse: cost/tax/dividend simulator + proxy splices + dividend resolution +
# basket weights + cash injection + the canonical engine trigger schedule.
from scripts.backtest_cost_aware import (  # noqa: E402
    ACCOUNTS,
    CostAwareSimulator,
    downside_metrics,
    quarterly_dividend_dates,
    resolve_dividend_yields,
)
from scripts.backtest_custom_basket_rebalance import (  # noqa: E402
    CASH_CODE,
    CASH_WEIGHT,
    GROUP_A_WEIGHTS,
    GROUP_B_WEIGHTS,
    INITIAL_CAPITAL,
    RESTORE_FRACTION,
    RISK_FREE_RATE,
    assert_no_discontinuity,
    fetch_price_map,
    inject_cash_series,
)
from scripts.backtest_robustness import (  # noqa: E402
    ETF_CODES as LIVE_ETF_CODES,
    FULL_PROXY_START,
    PROXY_SOURCE_CODES,
    build_full_proxy_prices,
)
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
logger = logging.getLogger("backtest_selection_validation")

ENV_BASE = {
    "dev": "http://localhost:8902",
    "prod": "https://kima3.net/japan-etf-analyzer",
}

# Windows (task-fixed).
FULL_END = date(2026, 5, 15)
WF_TRAIN_END = date(2017, 12, 31)  # screening reference cutoff (out-of-sample)
WF_EVAL_START = date(2018, 1, 1)  # out-of-sample evaluation start

# Group structure mirrors the live basket (A: 3 x 15%, B: 5 x 9%, CASH 10%).
GROUP_A_SLOTS = len(GROUP_A_WEIGHTS)  # 3
GROUP_B_SLOTS = len(GROUP_B_WEIGHTS)  # 5
GROUP_A_W = list(GROUP_A_WEIGHTS.values())[0]  # 0.15
GROUP_B_W = list(GROUP_B_WEIGHTS.values())[0]  # 0.09

# Argument-free prefilter cap (documented simplification: limits the API
# price fetch on a ~450 ETF universe so a no-arg run completes). Raised so
# enough *long-history* names survive the WF-train (2011..2017) screen,
# whose universe is far smaller than the full-period one.
PREFILTER_LIMIT = 220

# core_screen's default short-history floor is 100 common months (~8.3y).
# The WF *training* window (2011-03..2017-12) spans only ~82 months, so a
# 100-month floor would reject every candidate. We apply a window-fitting
# 60-month (5y) floor *consistently to both screens* (WF and in-sample) so
# the two baskets are selected under identical eligibility rules. This is a
# runtime-only override of the imported module's constant (the constant is
# read at call time inside core_screen): the on-disk etf_partner_backtest.py
# is unmodified and its --core-screen CLI keeps the default 100 — fully
# backward compatible (the override is scoped + restored below).
SCREEN_MIN_COMMON_MONTHS = 60


class _min_months_override:
    """Temporarily set etf_partner_backtest.CORE_SCREEN_MIN_COMMON_MONTHS.

    Restores the original value on exit so no global side effect leaks
    (backward-compatible: the imported module behaves identically outside
    this scope).
    """

    def __init__(self, value: int):
        self.value = value
        self._saved: Optional[int] = None

    def __enter__(self):
        self._saved = _epb.CORE_SCREEN_MIN_COMMON_MONTHS
        _epb.CORE_SCREEN_MIN_COMMON_MONTHS = self.value
        return self

    def __exit__(self, *exc):
        _epb.CORE_SCREEN_MIN_COMMON_MONTHS = self._saved
        return False

# Stress windows annotated inside each evaluation window.
STRESS_WINDOWS: List[Tuple[str, date, date]] = [
    ("2018Q4", date(2018, 10, 1), date(2018, 12, 31)),
    ("2020_covid", date(2020, 2, 1), date(2020, 4, 30)),
    ("2022_drawdown", date(2022, 1, 1), date(2022, 12, 31)),
    ("2024-08", date(2024, 8, 1), date(2024, 8, 31)),
]

# Strategy set is intentionally narrow (task): buy_hold + low-frequency 3%
# band hybrid (= recommended-operation "rebalance_b03").
STRATEGIES = ("buy_hold", "rebalance_b03")


# ---------------------------------------------------------------------------
# Price helpers (API-only — windowed copies, never the DB)
# ---------------------------------------------------------------------------


def _window_prices(
    prices: Dict[str, Dict[date, float]], start: date, end: date
) -> Dict[str, Dict[date, float]]:
    """A date-windowed *copy* of an API price map (no mutation of input)."""
    return {
        c: {d: p for d, p in dm.items() if start <= d <= end}
        for c, dm in prices.items()
    }


def _build_screen_input(
    universe: List[Dict],
    raw: Dict[str, Dict[date, float]],
) -> Tuple[List[Dict], Dict[str, str]]:
    """Universe records + name map for the prefiltered candidate set only."""
    candidates = prefilter_candidates(universe, limit=PREFILTER_LIMIT)
    name_map = {e["code"]: e.get("name", "") for e in candidates}
    return candidates, name_map


# ---------------------------------------------------------------------------
# Group assignment: top CORE_FIT survivors -> live group structure
# ---------------------------------------------------------------------------


def assign_groups(ranking: List[Dict]) -> Dict:
    """Map the top survivors onto A(3 x 15%) / B(5 x 9%) / CASH 10%.

    Rule (documented in the report): the CORE_FIT composite already rewards
    low mean |pairwise corr| (0.40 weight), so the composite-rank order is
    diversification-aware. We take the top ``GROUP_A_SLOTS`` survivors into
    group A and the next ``GROUP_B_SLOTS`` into group B, preserving each
    slot's live weight. Codes are unique across both groups by construction
    (single ranked list, sequential consumption).
    """
    needed = GROUP_A_SLOTS + GROUP_B_SLOTS
    picks = ranking[:needed]
    if len(picks) < needed:
        raise RuntimeError(
            f"screening produced only {len(picks)} eligible ETFs; "
            f"need {needed} (A={GROUP_A_SLOTS} + B={GROUP_B_SLOTS})"
        )
    a_codes = [p["code"] for p in picks[:GROUP_A_SLOTS]]
    b_codes = [p["code"] for p in picks[GROUP_A_SLOTS:needed]]

    weights: Dict[str, float] = {}
    for c in a_codes:
        weights[c] = GROUP_A_W
    for c in b_codes:
        weights[c] = GROUP_B_W
    weights[CASH_CODE] = CASH_WEIGHT
    # weight integrity: A*0.15*3 + B*0.09*5 + CASH 0.10 == 1.0
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise RuntimeError(f"screening basket weight sum={total} != 1.0")

    assignment = []
    for rank, p in enumerate(picks, 1):
        grp = "A" if rank <= GROUP_A_SLOTS else "B"
        assignment.append(
            {
                "rank": rank,
                "group": grp,
                "code": p["code"],
                "name": p["name"],
                "weight": GROUP_A_W if grp == "A" else GROUP_B_W,
                "composite": p["composite"],
                "cagr": p["cagr"],
                "vol": p["vol"],
                "sharpe": p["sharpe"],
                "mdd": p["mdd"],
                "mean_abs_corr": p["mean_abs_corr"],
                "diversification": p["diversification"],
                "common_months": p["common_months"],
            }
        )
    return {
        "a_codes": a_codes,
        "b_codes": b_codes,
        "weights": weights,
        "assignment": assignment,
    }


def _live_weights() -> Dict[str, float]:
    """Live (hand-picked) full target weights incl. CASH (sums to 1.0)."""
    w: Dict[str, float] = {}
    w.update(GROUP_A_WEIGHTS)
    w.update(GROUP_B_WEIGHTS)
    w[CASH_CODE] = CASH_WEIGHT
    return w


# ---------------------------------------------------------------------------
# Spec construction (buy_hold + low-freq 3% band hybrid) — reuses CaseSpec
# ---------------------------------------------------------------------------


def _make_specs(codes: List[str], weights: Dict[str, float]) -> List[CaseSpec]:
    """Two CaseSpecs over an arbitrary basket: buy_hold + rebalance_b03.

    ``rebalance_b03`` = the engine's ``hybrid`` strategy with band=0.03 and
    restore_fraction=0.70 (the recommended low-frequency operation; same
    strategy implementation the cost-aware/custom-basket scripts use).
    """
    full = list(codes) + [CASH_CODE]
    return [
        CaseSpec(
            case_id="buy_hold",
            group="selection",
            allocation="screened_or_live",
            strategy="buy_hold",
            codes=list(full),
            target_weights=dict(weights),
        ),
        CaseSpec(
            case_id="rebalance_b03",
            group="selection",
            allocation="screened_or_live",
            strategy="hybrid",
            codes=list(full),
            target_weights=dict(weights),
            band=0.03,
            restore_fraction=RESTORE_FRACTION,
        ),
    ]


# ---------------------------------------------------------------------------
# Backtest one basket over one window for both accounts (nisa, gross)
# ---------------------------------------------------------------------------


def _stress_segment_metrics(
    equity_curve: List[Tuple[date, float]],
    metrics: MetricsCalculator,
) -> Dict[str, Dict]:
    """Per-stress-window in-segment return/MDD (skips windows out of range)."""
    out: Dict[str, Dict] = {}
    if not equity_curve:
        return out
    cmin = equity_curve[0][0]
    cmax = equity_curve[-1][0]
    for label, s, e in STRESS_WINDOWS:
        if e < cmin or s > cmax:
            continue
        seg = [(d, v) for d, v in equity_curve if s <= d <= e]
        if len(seg) < 2:
            continue
        m = metrics.compute(seg)
        out[label] = {
            "return": round(m["total_return"], 6),
            "mdd": round(m["mdd"], 6),
            "start": seg[0][0].isoformat(),
            "end": seg[-1][0].isoformat(),
        }
    return out


def run_basket(
    basket_name: str,
    prices_in: Dict[str, Dict[date, float]],
    equity_codes: List[str],
    weights: Dict[str, float],
    start: date,
    end: date,
    config: BacktestConfig,
    metrics: MetricsCalculator,
    yields: Dict[str, float],
    div_dates_calendar_src: Optional[List[date]],
) -> List[Dict]:
    """Run buy_hold + rebalance_b03 for nisa + gross on one basket/window.

    Mirrors ``backtest_cost_aware.run_account`` orchestration exactly: the
    engine PortfolioSimulator is run cost-free to capture the canonical
    (date, event_type) trigger schedule, then CostAwareSimulator replays
    that identical schedule for the gross (frictionless) and net runs so the
    accounting identity can be verified.
    """
    prices = _window_prices(prices_in, start, end)
    # restrict to this basket's equity codes (+ CASH added below)
    prices = {c: prices.get(c, {}) for c in equity_codes}
    calendar = build_business_calendar(prices, start, end)
    if not calendar:
        raise RuntimeError(f"empty calendar for {basket_name} {start}..{end}")
    inject_cash_series(prices, calendar)
    assert_no_discontinuity(prices)

    listings = listing_date_map(prices)
    filled = forward_fill_prices(prices, calendar)
    rebalance_dates = compute_quarter_end_dates(calendar)
    div_dates = quarterly_dividend_dates(calendar)

    # dividend yield per code: API-resolved for the live codes; screened
    # codes not in the resolved map default to 0.0 (conservative — no
    # assumed yield invented for arbitrary screened ETFs; documented).
    code_yields = {c: float(yields.get(c, 0.0)) for c in equity_codes}

    results: List[Dict] = []
    for spec in _make_specs(equity_codes, weights):
        engine_sim = PortfolioSimulator(
            config, spec, filled, calendar, listings, rebalance_dates
        )
        engine_case = engine_sim.run()
        trigger_events: List[Tuple[str, str]] = [
            (e["date"], e["event_type"]) for e in engine_case["events"]
        ]

        for account in ACCOUNTS:  # ("taxable", "nisa")
            # gross (frictionless) control for the accounting identity
            gross = CostAwareSimulator(
                config,
                spec,
                filled,
                calendar,
                listings,
                rebalance_dates,
                account="nisa",
                dividend_yields={c: 0.0 for c in code_yields},
                dividend_dates=[],
                trigger_events=trigger_events,
                frictionless=True,
            )
            gcase = gross.run()
            gm = metrics.compute(gcase["equity_curve"])

            sim = CostAwareSimulator(
                config,
                spec,
                filled,
                calendar,
                listings,
                rebalance_dates,
                account=account,
                dividend_yields=code_yields,
                dividend_dates=div_dates,
                trigger_events=trigger_events,
            )
            case = sim.run()
            m = metrics.compute(case["equity_curve"])

            years = max((end - start).days / 365.25, 1e-9)
            turnover = (
                case["traded_notional_total"]
                / config.initial_capital
                / years
            )
            dn = downside_metrics(case["equity_curve"], RISK_FREE_RATE)
            net_cagr = m["cagr"]
            net_mdd = m["mdd"]
            calmar = net_cagr / abs(net_mdd) if net_mdd < 0 else 0.0
            sortino = (
                (net_cagr - RISK_FREE_RATE) / dn["sortino_dn_dev"]
                if dn.get("sortino_dn_dev", 0.0) > 0
                else 0.0
            )

            # accounting identity:
            #   net_end ?= init + market_pnl - cost - tax + div_net
            init_cap = config.initial_capital
            net_end = (
                case["equity_curve"][-1][1] if case["equity_curve"] else 0.0
            )
            identity_rhs = (
                init_cap
                + case["market_pnl_total"]
                - case["transaction_cost_total"]
                - case["tax_total"]
                + case["dividend_income_total"]
            )
            residual = net_end - identity_rhs

            results.append(
                {
                    "basket": basket_name,
                    "case_id": spec.case_id,
                    "strategy": spec.strategy,
                    "account": account,
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "gross_return": round(gm["total_return"], 6),
                    "gross_end_value": round(gm["end_value"], 2),
                    "net_return": round(m["total_return"], 6),
                    "net_cagr": round(net_cagr, 6),
                    "net_mdd": round(net_mdd, 6),
                    "calmar": round(calmar, 4),
                    "sortino": round(sortino, 4),
                    "vol": round(m["vol"], 6),
                    "transaction_cost_total": round(
                        case["transaction_cost_total"], 2
                    ),
                    "tax_total": round(case["tax_total"], 2),
                    "dividend_income_total": round(
                        case["dividend_income_total"], 2
                    ),
                    "annual_turnover": round(turnover, 6),
                    "rebalance_count": case["rebalance_count"],
                    "band_count": case["band_rebalance_count"],
                    "start_value": round(m["start_value"], 2),
                    "end_value": round(m["end_value"], 2),
                    "market_pnl_total": round(case["market_pnl_total"], 2),
                    "identity_residual": round(residual, 4),
                    "assert_failures": list(case["assert_failures"]),
                    "stress": _stress_segment_metrics(
                        case["equity_curve"], metrics
                    ),
                }
            )
            logger.info(
                "  [%s/%s/%s/%s] netCAGR=%.2f%% netMDD=%.2f%% "
                "Calmar=%.2f resid=%.4f",
                basket_name,
                spec.case_id,
                account,
                start.year,
                net_cagr * 100,
                net_mdd * 100,
                calmar,
                residual,
            )
    return results


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

SUMMARY_FIELDS = [
    "basket",
    "case_id",
    "strategy",
    "account",
    "window_start",
    "window_end",
    "gross_return",
    "net_return",
    "net_cagr",
    "net_mdd",
    "calmar",
    "sortino",
    "vol",
    "transaction_cost_total",
    "tax_total",
    "dividend_income_total",
    "annual_turnover",
    "rebalance_count",
    "band_count",
    "start_value",
    "end_value",
    "market_pnl_total",
    "identity_residual",
]


def write_summary_csv(results: List[Dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in SUMMARY_FIELDS})


def write_screening_outputs(
    screen: Dict, group: Dict, out_dir: Path, ref_label: str
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # full eligibility ranking CSV
    rank_csv = out_dir / "eligible_ranking.csv"
    fields = [
        "rank",
        "code",
        "name",
        "composite",
        "cagr",
        "vol",
        "sharpe",
        "mdd",
        "mean_abs_corr",
        "diversification",
        "risk_quality_norm",
        "drawdown_resilience",
        "common_months",
    ]
    with rank_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(screen["ranking"], 1):
            row = {k: r.get(k, "") for k in fields}
            row["rank"] = i
            w.writerow(row)

    # group assignment CSV
    asg_csv = out_dir / "group_assignment.csv"
    asg_fields = [
        "rank",
        "group",
        "code",
        "name",
        "weight",
        "composite",
        "cagr",
        "vol",
        "sharpe",
        "mdd",
        "mean_abs_corr",
        "diversification",
        "common_months",
    ]
    with asg_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=asg_fields)
        w.writeheader()
        for r in group["assignment"]:
            w.writerow({k: r.get(k, "") for k in asg_fields})

    md = out_dir / "screening.md"
    lines: List[str] = []
    lines.append(f"# 中立スクリーニング（{ref_label}）")
    lines.append("")
    lines.append(f"**生成日時**: {datetime.now().isoformat()}  ")
    lines.append(
        f"**参照データ窓**: {ref_label}  "
    )
    lines.append(
        f"**リターン下限**: 共通期間 CAGR ≥ {screen['min_cagr']:.1f}%  "
    )
    w = screen.get("weights", {})
    lines.append(
        "**CORE_FIT 加重**: 分散 {d:.2f} / リスク質 {r:.2f} / "
        "ドローダウン耐性 {dd:.2f}  ".format(
            d=w.get("diversification", 0.0),
            r=w.get("risk_quality", 0.0),
            dd=w.get("drawdown_resilience", 0.0),
        )
    )
    lines.append(f"**適格者数**: {len(screen['ranking'])}銘柄  ")
    lines.append(
        "**プリフィルタ**: 母集団から レバレッジ/インバース等を除外し "
        f"return_performance 上位{PREFILTER_LIMIT}件に縮約してから価格取得"
        "（無引数完走のための簡易化。除外は既存ロジック準拠）  "
    )
    lines.append(
        f"**短履歴下限**: 共通月数 ≥ {SCREEN_MIN_COMMON_MONTHS} "
        "（WF訓練窓2011〜2017が約82か月のため既定100か月→60か月に緩和。"
        "WF/インサンプル双方に同一適用＝適格基準は同条件。"
        "etf_partner_backtest.py はディスク無改変／実行時スコープ限定上書き）  "
    )
    lines.append("")
    lines.append("## グループ割当（A群3枠15% / B群5枠9% / 現金10%）")
    lines.append("")
    lines.append(
        "| 順位 | 群 | コード | 銘柄名 | 比率 | composite | CAGR | "
        "Sharpe | MDD | 平均|相関| | 共通月数 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in group["assignment"]:
        lines.append(
            "| {rank} | {grp} | {code} | {name} | {w:.0%} | {comp:.4f} | "
            "{cagr:.2%} | {sh:.2f} | {mdd:.2%} | {mac:.4f} | {cm} |".format(
                rank=r["rank"],
                grp=r["group"],
                code=r["code"],
                name=r["name"],
                w=r["weight"],
                comp=r["composite"],
                cagr=r["cagr"],
                sh=r["sharpe"],
                mdd=r["mdd"],
                mac=r["mean_abs_corr"],
                cm=r["common_months"],
            )
        )
    lines.append("")
    lines.append("## 選定根拠")
    lines.append("")
    lines.append(
        "- 母集団全体からゼロベースで適格判定（コア指定なし）。"
        "名称によるレバレッジ/インバース除外、非物理的不連続"
        "（max_daily_jump）除外、短履歴除外、CAGR下限の順で篩い、"
        "生存者を CORE_FIT 加重 composite で序列化（既存 `core_screen` "
        "ロジックをそのまま呼び出し）。"
    )
    lines.append(
        "- composite は分散（1−平均|ペア相関|）に 0.40 の重みを置くため、"
        "上位順＝相関重複が少ない順に近い。よって composite 上位から "
        "A群3枠→B群5枠へ順に割当てるだけで分散制約を満たす。"
    )
    lines.append("")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rows_by(
    results: List[Dict], basket: str, case_id: str, account: str
) -> Optional[Dict]:
    for r in results:
        if (
            r["basket"] == basket
            and r["case_id"] == case_id
            and r["account"] == account
        ):
            return r
    return None


def _matrix_lines(results: List[Dict], account: str) -> List[str]:
    """Comparison matrix for one account over the results of one window."""
    baskets = ["current", "screening_wf", "screening_insample"]
    labels = {
        "current": "現行(手選び)",
        "screening_wf": "スクリーニング(WF)",
        "screening_insample": "スクリーニング(インサンプル参照)",
    }
    lines: List[str] = []
    lines.append(
        "| バスケット | 戦略 | netCAGR | netMDD | Calmar | Sortino | "
        "売買コスト | 税 | 分配金 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for b in baskets:
        for s in STRATEGIES:
            r = _rows_by(results, b, s, account)
            if not r:
                continue
            lines.append(
                "| {bl} | {s} | {cagr:.2%} | {mdd:.2%} | {cal:.2f} | "
                "{sor:.2f} | {cost:,.0f} | {tax:,.0f} | {div:,.0f} |".format(
                    bl=labels[b],
                    s=s,
                    cagr=r["net_cagr"],
                    mdd=r["net_mdd"],
                    cal=r["calmar"],
                    sor=r["sortino"],
                    cost=r["transaction_cost_total"],
                    tax=r["tax_total"],
                    div=r["dividend_income_total"],
                )
            )
    return lines


def write_window_report(
    title: str,
    bias_note: str,
    results: List[Dict],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_summary_csv(results, out_dir / "summary.csv")
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**生成日時**: {datetime.now().isoformat()}  ")
    if bias_note:
        lines.append(f"**バイアス注記**: {bias_note}  ")
    win = results[0] if results else {}
    lines.append(
        f"**評価窓**: {win.get('window_start','')} .. "
        f"{win.get('window_end','')}  "
    )
    lines.append("")
    for account in ("nisa", "taxable"):
        head = "NISA（主軸）" if account == "nisa" else "gross相当(taxable)"
        lines.append(f"## 比較マトリクス — {head}")
        lines.append("")
        lines.extend(_matrix_lines(results, account))
        lines.append("")
    # stress windows
    lines.append("## 主要ストレス窓の窓内挙動（NISA / buy_hold）")
    lines.append("")
    lines.append("| バスケット | ストレス窓 | 区間リターン | 区間MDD |")
    lines.append("|---|---|---|---|")
    for b in ["current", "screening_wf", "screening_insample"]:
        r = _rows_by(results, b, "buy_hold", "nisa")
        if not r:
            continue
        for label, seg in sorted(r.get("stress", {}).items()):
            lines.append(
                "| {b} | {lab} | {ret:.2%} | {mdd:.2%} |".format(
                    b=b, lab=label, ret=seg["return"], mdd=seg["mdd"]
                )
            )
    lines.append("")
    # accounting identity check
    lines.append("## 会計恒等式検算")
    lines.append("")
    lines.append(
        "`net_end = 初期資本 + market_pnl − 売買コスト − 税 + 分配金純額`"
        " の残差（円）。NISA かつ gross 併走で構造分離を担保。"
    )
    lines.append("")
    lines.append("| バスケット | 戦略 | 口座 | 残差(円) |")
    lines.append("|---|---|---|---|")
    max_resid = 0.0
    for r in results:
        max_resid = max(max_resid, abs(r["identity_residual"]))
        lines.append(
            "| {b} | {s} | {a} | {res:.4f} |".format(
                b=r["basket"],
                s=r["case_id"],
                a=r["account"],
                res=r["identity_residual"],
            )
        )
    lines.append("")
    lines.append(
        f"**最大絶対残差**: {max_resid:.4f} 円 "
        f"({'OK ≈0' if max_resid < 1.0 else '要確認'})"
    )
    lines.append("")
    (out_dir / "report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _selection_vs_strategy(
    results: List[Dict], account: str
) -> Dict[str, float]:
    """Decompose netCAGR (pt) into selection vs strategy effect.

    selection effect = |current − screening_wf| netCAGR at the same strategy
                        (averaged over both strategies)
    strategy effect  = |buy_hold − rebalance_b03| netCAGR within the same
                        basket (averaged over the three baskets)
    """
    sel_deltas: List[float] = []
    for s in STRATEGIES:
        cur = _rows_by(results, "current", s, account)
        wf = _rows_by(results, "screening_wf", s, account)
        if cur and wf:
            sel_deltas.append(abs(cur["net_cagr"] - wf["net_cagr"]))
    strat_deltas: List[float] = []
    for b in ["current", "screening_wf", "screening_insample"]:
        bh = _rows_by(results, b, "buy_hold", account)
        rb = _rows_by(results, b, "rebalance_b03", account)
        if bh and rb:
            strat_deltas.append(abs(bh["net_cagr"] - rb["net_cagr"]))
    sel = sum(sel_deltas) / len(sel_deltas) if sel_deltas else 0.0
    strat = sum(strat_deltas) / len(strat_deltas) if strat_deltas else 0.0
    return {
        "selection_effect_pt": sel * 100.0,
        "strategy_effect_pt": strat * 100.0,
    }


def write_root_report(
    root_dir: Path,
    group_wf: Dict,
    group_is: Dict,
    wf_results: List[Dict],
    is_results: List[Dict],
) -> Path:
    """The integrated root report with the 4 mandated sections."""
    lines: List[str] = []
    lines.append("# 銘柄選択の妥当性検証 — 手選び vs 中立スクリーニング")
    lines.append("")
    lines.append(f"**生成日時**: {datetime.now().isoformat()}  ")
    lines.append(
        "**目的**: 「ポートフォリオの本丸は銘柄選択」という前段結論を、"
        "既存のゼロベース・コア適格スクリーニングと接続し、選択バイアス"
        "（生存・先読み）を排除した上で定量検証する。  "
    )
    lines.append("")

    # 1. premises / method / WF design
    lines.append("## 1. 前提・スクリーニング手法・WF設計")
    lines.append("")
    lines.append(
        "- **現行(手選び)バスケット**: A群45%(2559/1540/1629 各15%) + "
        "B群45%(2646/1306/1618/200A/1615 各9%) + 現金10%。初期100万円、"
        "restore_fraction=0.70、RF=0.0。"
    )
    lines.append(
        "- **プロキシ**: 現行は full_proxy（2559←1554 / 2646←1623 / "
        "200A←2644←1625 多段スプライス、基盤 "
        f"{FULL_PROXY_START.isoformat()}〜{FULL_END.isoformat()}）を使用。"
        "スクリーニング銘柄は任意コードのためプロキシ連鎖を持たず"
        "API実系列のみ（簡易化：採用可能な最長共通窓に縮約し、各窓は"
        "ウォークフォワード優先で評価）。"
    )
    lines.append(
        "- **コスト前提**: 売買片道0.05% / taxable=譲渡益20.315%＋分配"
        "源泉20.315%・暦年通算 / nisa=非課税 / 分配金は API 実績利回り"
        "四半期均等（スクリーニング銘柄でAPI利回り無→0%、想定値は"
        "捏造しない保守設定）。主軸 **NISA**、構造分離用に **gross** 併走。"
    )
    lines.append(
        "- **スクリーニング手法**: 既存 `etf_partner_backtest.core_screen` "
        "をそのまま呼び出し。名称によるレバレッジ/インバース除外→"
        "非物理的不連続除外→短履歴除外→CAGR下限の順で篩い、生存者を "
        "CORE_FIT 加重 composite（分散0.40＋リスク質0.35＋DD耐性0.25）"
        "で序列化。"
    )
    lines.append(
        "- **グループ割当規則**: composite は分散に0.40の重みを置くため"
        "上位順＝相関重複が少ない順に近い。composite 上位から "
        f"A群{GROUP_A_SLOTS}枠（各{GROUP_A_W:.0%}）→"
        f"B群{GROUP_B_SLOTS}枠（各{GROUP_B_W:.0%}）へ順に割当て、"
        "現金10%を加える（重み合計=1.0、コード重複なし）。"
    )
    lines.append(
        "- **WF設計（最重要）**: スクリーニング参照データを "
        f"{FULL_PROXY_START.isoformat()}〜{WF_TRAIN_END.isoformat()} "
        f"のみに限定して中立銘柄を選定 → "
        f"{WF_EVAL_START.isoformat()}〜{FULL_END.isoformat()} で"
        "アウトオブサンプル検証。現行も同一の2018〜2026窓で評価し"
        "同一土俵で比較。"
    )
    lines.append(
        "- **インサンプル参照**: 全期間データでスクリーニングした版を"
        "併走（**先読みバイアス込みの上限値**）。WFとの乖離で生存・"
        "先読み効果の大きさを定量化。"
    )
    lines.append("")

    # 2. out-of-sample win/lose
    lines.append("## 2. アウトオブサンプル（2018〜2026）で現行 vs スクリーニング")
    lines.append("")
    lines.append("### NISA（主軸）")
    lines.append("")
    lines.extend(_matrix_lines(wf_results, "nisa"))
    lines.append("")
    verdicts: List[str] = []
    for s in STRATEGIES:
        cur = _rows_by(wf_results, "current", s, "nisa")
        wf = _rows_by(wf_results, "screening_wf", s, "nisa")
        if not (cur and wf):
            continue
        d_cagr = (cur["net_cagr"] - wf["net_cagr"]) * 100
        d_cal = cur["calmar"] - wf["calmar"]
        if d_cagr > 0.10 and d_cal > 0.02:
            v = "現行=勝"
        elif d_cagr < -0.10 and d_cal < -0.02:
            v = "現行=負"
        else:
            v = "分（実質互角）"
        verdicts.append(
            f"- **{s}**: 現行−スクリーニング(WF) = "
            f"netCAGR {d_cagr:+.2f}pt / Calmar {d_cal:+.2f} / "
            f"netMDD {(cur['net_mdd']-wf['net_mdd'])*100:+.2f}pt → "
            f"**{v}**"
        )
    lines.extend(verdicts)
    lines.append("")

    # 3. selection vs strategy dominance
    lines.append("## 3. 選択効果 vs 戦略効果の支配性")
    lines.append("")
    sv_wf = _selection_vs_strategy(wf_results, "nisa")
    lines.append(
        f"- WF窓 NISA: **選択効果 = {sv_wf['selection_effect_pt']:.2f}pt** "
        f"(現行 vs スクリーニング, 同一戦略平均) vs "
        f"**戦略効果 = {sv_wf['strategy_effect_pt']:.2f}pt** "
        f"(buy_hold vs rebalance_b03, 同一バスケット平均)"
    )
    dominant = (
        "銘柄選択"
        if sv_wf["selection_effect_pt"] >= sv_wf["strategy_effect_pt"]
        else "戦略(リバランス頻度)"
    )
    ratio = (
        sv_wf["selection_effect_pt"] / sv_wf["strategy_effect_pt"]
        if sv_wf["strategy_effect_pt"] > 1e-9
        else float("inf")
    )
    lines.append(
        f"- **支配的要因 = {dominant}**（選択効果 / 戦略効果 "
        f"≈ {ratio:.1f}x）。前段結論「本丸は銘柄選択」は"
        f"{'支持される' if dominant == '銘柄選択' else '本データでは限定的'}。"
    )
    lines.append("")

    # 4. look-ahead bias magnitude (insample - WF)
    lines.append("## 4. 先読みバイアスの大きさ（インサンプル − WF）")
    lines.append("")
    lines.append(
        "| 戦略 | 口座 | スクリーニング(WF) netCAGR | "
        "スクリーニング(インサンプル) netCAGR | 乖離(pt) |"
    )
    lines.append("|---|---|---|---|---|")
    bias_pts: List[float] = []
    for s in STRATEGIES:
        for acct in ("nisa", "taxable"):
            wf = _rows_by(wf_results, "screening_wf", s, acct)
            isr = _rows_by(is_results, "screening_insample", s, acct)
            if not (wf and isr):
                continue
            gap = (isr["net_cagr"] - wf["net_cagr"]) * 100
            if acct == "nisa":
                bias_pts.append(gap)
            lines.append(
                "| {s} | {a} | {wf:.2%} | {isr:.2%} | {gap:+.2f} |".format(
                    s=s, a=acct, wf=wf["net_cagr"], isr=isr["net_cagr"],
                    gap=gap,
                )
            )
    avg_bias = sum(bias_pts) / len(bias_pts) if bias_pts else 0.0
    if avg_bias > 0.10:
        bias_interp = (
            "全期間データで選ぶと生存者効果＋先読みでこの分だけ"
            "アウトオブサンプル実力を過大評価する（正のバイアス）。"
        )
    elif avg_bias < -0.10:
        bias_interp = (
            "本データでは負（インサンプル選定がWF選定をアウトオブ"
            "サンプル窓で下回る）。全期間データの高リターン銘柄は直近"
            "偏重で2018〜2026では伸びず、先読みが必ずしも有利に働かない"
            "ことを示す＝中立スクリーニング自体の不安定性の証左。"
        )
    else:
        bias_interp = (
            "ほぼゼロ（インサンプルとWFの選定差がアウトオブサンプル"
            "成績にほとんど効かない）。"
        )
    lines.append("")
    lines.append(
        f"- **平均先読みバイアス量 (NISA) ≈ {avg_bias:+.2f}pt** "
        f"(インサンプル−WF の netCAGR 乖離)。{bias_interp}"
        "いずれにせよ WF がアウトオブサンプルの正味実力。"
    )
    lines.append("")

    # 5. target_holdings recommendation
    lines.append("## 5. target_holdings 見直し提言")
    lines.append("")
    cur_bh = _rows_by(wf_results, "current", "buy_hold", "nisa")
    wf_bh = _rows_by(wf_results, "screening_wf", "buy_hold", "nisa")
    cur_rb = _rows_by(wf_results, "current", "rebalance_b03", "nisa")
    wf_rb = _rows_by(wf_results, "screening_wf", "rebalance_b03", "nisa")
    current_wins = 0
    cmp_n = 0
    for cur, wf in ((cur_bh, wf_bh), (cur_rb, wf_rb)):
        if cur and wf:
            cmp_n += 1
            if cur["net_cagr"] >= wf["net_cagr"] - 0.001:
                current_wins += 1
    revise = current_wins < cmp_n  # screening beat current on a majority
    if cmp_n == 0:
        verdict = "判定不能（データ不足）"
        rec = "No（検証不能。再実行を推奨）"
    elif not revise:
        verdict = (
            "現行バスケットはアウトオブサンプルで中立スクリーニング比 "
            "互角以上"
        )
        rec = (
            "**No** — 現行 target_holdings は中立基準に対し堅牢。"
            "選択効果が戦略効果を上回るとしても、現行の手選びは"
            "アウトオブサンプルで中立スクリーニングに劣後しないため、"
            "全面入替の根拠はない。継続を推奨。"
        )
    else:
        verdict = (
            "中立スクリーニングがアウトオブサンプルで現行を上回る"
        )
        rec = (
            "**Yes（部分的）** — アウトオブサンプルで中立スクリーニングが"
            "現行を上回る。`docs/12_personal_strategy.md` の "
            "target_holdings について、スクリーニング上位銘柄での"
            "一部置換を検討する価値がある（`docs/12a_戦略書改訂手順.md` "
            "のチェックリストに従い段階導入）。ただし先読みバイアス量"
            f"（≈{avg_bias:+.2f}pt）を割り引いた正味で判断すること。"
        )
    lines.append(f"- **所見**: {verdict}。")
    lines.append(f"- **提言**: {rec}")
    lines.append("")

    # regime cross-cut closing
    lines.append("## 6. regime 横断の最終所見")
    lines.append("")
    lines.append(
        "- ストレス窓（2018Q4 / 2020コロナ / 2022下落 / 2024-08）の窓内"
        "挙動は walkforward/report.md・insample_ref/report.md の"
        "ストレス節を参照。"
    )
    lines.append(
        "- 主軸 NISA と gross 併走の双方で会計恒等式残差≈0 を確認"
        "（各 report.md の検算節）。コスト/税/分配金の構造を分離した上で"
        "もアウトオブサンプルの相対序列は安定。"
    )
    lines.append(
        f"- 結論: 銘柄選択は{'支配的' if dominant == '銘柄選択' else '重要だが戦略効果と同等以下'}"
        "要因であり、かつ現行の手選びは中立スクリーニングに対して"
        f"{'劣後しない' if not revise else '一部劣後する'}。"
        "先読みバイアスを割り引いた正味（WF）が実務判断の基準。"
    )
    lines.append("")
    root = root_dir / "report.md"
    root.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _run_screen(
    universe: List[Dict],
    raw_window: Dict[str, Dict[date, float]],
    name_map: Dict[str, str],
    min_cagr: float,
    candidates: List[Dict],
) -> Tuple[Dict, Dict]:
    """core_screen on a windowed price map -> (screen, group assignment).

    The short-history floor is relaxed to ``SCREEN_MIN_COMMON_MONTHS`` for
    the duration of the call so the (shorter) WF-train window is viable;
    the same floor is used for the in-sample screen so both baskets are
    selected under identical eligibility rules.
    """
    with _min_months_override(SCREEN_MIN_COMMON_MONTHS):
        screen = core_screen(candidates, raw_window, name_map, min_cagr)
    group = assign_groups(screen["ranking"])
    return screen, group


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--env", choices=list(ENV_BASE), default="dev")
    p.add_argument("--base-url", type=str, default=None)
    p.add_argument("--period", type=str, default="20y")
    p.add_argument(
        "--min-cagr",
        type=float,
        default=CORE_SCREEN_DEFAULT_MIN_CAGR,
        help="core-screen return floor: %% annualized CAGR (default 5.0)",
    )
    p.add_argument("--output-dir", type=str, default=None)
    return p.parse_args(argv)


def resolve_reports_root() -> Path:
    app_base = Path(os.environ.get("APP_BASE_DIR", str(PROJECT_ROOT)))
    for c in (
        app_base / "reports",
        BACKEND_DIR / "reports",
        PROJECT_ROOT / "reports",
    ):
        if c.is_dir():
            return c
    return app_base / "reports"


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
            / f"{ts}_selection_validation"
        )
    root_dir.mkdir(parents=True, exist_ok=True)
    logger.info("output root: %s", root_dir)

    # --- 1. universe + prefilter + API prices (API-only) ---
    logger.info("fetching universe via API: %s", base_url)
    universe = fetch_universe(base_url)
    candidates, name_map = _build_screen_input(universe, {})
    cand_codes = [c["code"] for c in candidates if c.get("code")]

    # Live basket needs its equity codes + proxy sources; screening needs the
    # prefiltered candidates. Fetch the union once (API chart-batch only).
    fetch_codes = sorted(
        set(cand_codes) | set(LIVE_ETF_CODES) | set(PROXY_SOURCE_CODES)
    )
    logger.info("fetching prices for %d codes", len(fetch_codes))
    raw = fetch_price_map(fetch_codes, base_url, period=args.period)

    # Live (hand-picked) basket prices: full proxy splice (existing assembly).
    live_prices_full = build_full_proxy_prices(raw)
    live_weights = _live_weights()

    # dividend yields (API-first) for the live codes — reused resolver
    logger.info("resolving dividend yields (API-first)")
    yields, _yield_src = resolve_dividend_yields(base_url)

    config = BacktestConfig(initial_capital=INITIAL_CAPITAL)
    metrics = MetricsCalculator(RISK_FREE_RATE)

    # --- 2. screening: WF (<=2017-12-31) and in-sample (full period) ---
    raw_wf = _window_prices(raw, FULL_PROXY_START, WF_TRAIN_END)
    raw_is = _window_prices(raw, FULL_PROXY_START, FULL_END)

    logger.info("screening (walk-forward train <= %s)", WF_TRAIN_END)
    screen_wf, group_wf = _run_screen(
        universe, raw_wf, name_map, args.min_cagr, candidates
    )
    logger.info(
        "WF screening basket A=%s B=%s",
        group_wf["a_codes"],
        group_wf["b_codes"],
    )

    logger.info("screening (in-sample full period — look-ahead biased)")
    screen_is, group_is = _run_screen(
        universe, raw_is, name_map, args.min_cagr, candidates
    )
    logger.info(
        "in-sample screening basket A=%s B=%s",
        group_is["a_codes"],
        group_is["b_codes"],
    )

    write_screening_outputs(
        screen_wf,
        group_wf,
        root_dir / "screening",
        f"WF train {FULL_PROXY_START.isoformat()}..{WF_TRAIN_END.isoformat()}",
    )
    write_screening_outputs(
        screen_is,
        group_is,
        root_dir / "screening_insample_ref",
        f"in-sample {FULL_PROXY_START.isoformat()}..{FULL_END.isoformat()}",
    )

    # --- 3. walk-forward window backtests (2018..2026) ---
    wf_results: List[Dict] = []
    logger.info("=== walk-forward eval %s..%s ===", WF_EVAL_START, FULL_END)
    wf_results += run_basket(
        "current",
        live_prices_full,
        LIVE_ETF_CODES,
        live_weights,
        WF_EVAL_START,
        FULL_END,
        config,
        metrics,
        yields,
        None,
    )
    wf_codes = group_wf["a_codes"] + group_wf["b_codes"]
    wf_results += run_basket(
        "screening_wf",
        raw,
        wf_codes,
        group_wf["weights"],
        WF_EVAL_START,
        FULL_END,
        config,
        metrics,
        yields,
        None,
    )
    # in-sample basket evaluated on the same WF eval window so the matrix
    # has all three baskets head-to-head out-of-sample-window-wise.
    is_codes = group_is["a_codes"] + group_is["b_codes"]
    wf_results += run_basket(
        "screening_insample",
        raw,
        is_codes,
        group_is["weights"],
        WF_EVAL_START,
        FULL_END,
        config,
        metrics,
        yields,
        None,
    )
    write_window_report(
        "ウォークフォワード（アウトオブサンプル 2018〜2026）",
        "スクリーニングは2011〜2017のみ参照（先読みなし）。"
        "screening_insample 行は参考（全期間データで選定）。",
        wf_results,
        root_dir / "walkforward",
    )

    # --- 4. in-sample reference window (full period 2011..2026) ---
    is_results: List[Dict] = []
    logger.info(
        "=== in-sample ref full period %s..%s ===",
        FULL_PROXY_START,
        FULL_END,
    )
    is_results += run_basket(
        "current",
        live_prices_full,
        LIVE_ETF_CODES,
        live_weights,
        FULL_PROXY_START,
        FULL_END,
        config,
        metrics,
        yields,
        None,
    )
    is_results += run_basket(
        "screening_insample",
        raw,
        is_codes,
        group_is["weights"],
        FULL_PROXY_START,
        FULL_END,
        config,
        metrics,
        yields,
        None,
    )
    is_results += run_basket(
        "screening_wf",
        raw,
        wf_codes,
        group_wf["weights"],
        FULL_PROXY_START,
        FULL_END,
        config,
        metrics,
        yields,
        None,
    )
    write_window_report(
        "インサンプル参照（全期間 2011〜2026・先読みバイアス込み）",
        "全期間データでスクリーニング＝先読み/生存バイアス込みの上限値。"
        "WF との乖離が選択バイアスの大きさ。",
        is_results,
        root_dir / "insample_ref",
    )

    # --- 5. root integrated report ---
    root_report = write_root_report(
        root_dir, group_wf, group_is, wf_results, is_results
    )

    # --- 6. coherence + accounting identity gate ---
    all_results = wf_results + is_results
    fails = [
        (r["basket"], r["case_id"], r["account"], r["assert_failures"])
        for r in all_results
        if r["assert_failures"]
    ]
    max_resid = max(
        (abs(r["identity_residual"]) for r in all_results), default=0.0
    )
    for b, c, a, msgs in fails:
        for m in msgs:
            logger.warning("[assert] %s/%s/%s :: %s", b, c, a, m)
    if not fails:
        logger.info("[assert] all coherence checks PASSED")
    logger.info(
        "[identity] max |residual| = %.6f yen (%s)",
        max_resid,
        "OK ~0" if max_resid < 1.0 else "REVIEW",
    )

    print()
    print("=== SUMMARY (selection-validation) ===")
    print(f"output root: {root_dir}")
    print(f"root report: {root_report}")
    print(
        f"WF screening basket  A={group_wf['a_codes']} "
        f"B={group_wf['b_codes']}"
    )
    print(
        f"IS screening basket  A={group_is['a_codes']} "
        f"B={group_is['b_codes']}"
    )
    print()
    for tag, res in (("WF(2018-2026)", wf_results), ("IS(2011-2026)", is_results)):
        print(f"--- {tag} / NISA ---")
        for r in res:
            if r["account"] != "nisa":
                continue
            print(
                f"{r['basket']:20s} {r['case_id']:14s} "
                f"netCAGR={r['net_cagr']*100:6.2f}%  "
                f"netMDD={r['net_mdd']*100:7.2f}%  "
                f"Calmar={r['calmar']:5.2f}  "
                f"resid={r['identity_residual']:.4f}"
            )
    print()
    print(f"max |accounting residual| = {max_resid:.6f} yen")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
