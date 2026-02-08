"""モメンタム戦略パラメータ包括的最適化（4パターン検証）。

4つの異なる評価軸でグリッドサーチを実行し、
全パターンで安定して上位に来る設定を特定する。

Usage:
    docker compose exec backend python scripts/simulation/optimize_comprehensive.py
"""

import os
import random
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# パス設定（backend/scripts/simulation/ -> scripts/ -> backend/ -> project root）
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent
BACKEND_DIR = SCRIPTS_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

from src.app import create_app  # noqa: E402
from src.models.etf import ETF  # noqa: E402
from src.models.price_history import PriceHistory  # noqa: E402

from simulation.engine import SimulationEngine  # noqa: E402
from simulation.strategies.momentum import MomentumStrategy  # noqa: E402

LABEL_BUY_OPTIONS = [
    frozenset({"上昇加速"}),
    frozenset({"上昇加速", "反転上昇"}),
    frozenset({"上昇加速", "上昇維持"}),
    frozenset({"上昇加速", "上昇維持", "反転上昇"}),
    frozenset({"上昇加速", "上昇維持", "上昇減速"}),
    frozenset({"上昇加速", "上昇維持", "上昇減速", "反転上昇"}),
]

LABEL_SELL_OPTIONS = [
    frozenset({"下降加速"}),
    frozenset({"下降加速", "下降維持"}),
    frozenset({"下降加速", "下降維持", "下降減速"}),
    frozenset({"失速", "下降加速", "下降維持", "下降減速"}),
    frozenset({"失速"}),
]

THRESHOLD_BUY_OPTIONS = [5, 10, 15, 20, 25]
THRESHOLD_SELL_OPTIONS = [-10, -5, 0, 5]
WINDOW_1M_OPTIONS = [20, 30, 45]
WINDOW_3M_OPTIONS = [60, 90, 120]

LEVERAGED_CODES = {
    "1356", "1357", "1358", "1360", "1365", "1366", "1367", "1368", "140A",
    "1456", "1457", "1458", "1459", "1466", "1469", "1472", "1560", "1568",
    "1569", "1570", "1571", "1572", "1573", "1579", "1580", "2094", "2237",
    "2238", "2239", "2240", "2245", "2246", "2249", "2251", "2554", "2647",
    "2648", "2842", "2869", "2870", "354A", "376A",
}

SAMPLE_SIZE = 50


def generate_label_configs() -> List[Dict]:
    """ラベル戦略のパラメータ組み合わせを生成する。"""
    configs = []  # type: List[Dict]
    for buy in LABEL_BUY_OPTIONS:
        for sell in LABEL_SELL_OPTIONS:
            for w1 in WINDOW_1M_OPTIONS:
                for w3 in WINDOW_3M_OPTIONS:
                    configs.append({
                        "variant": "label",
                        "buy_labels": buy,
                        "sell_labels": sell,
                        "window_1m": w1,
                        "window_3m": w3,
                    })
    return configs


def generate_threshold_configs() -> List[Dict]:
    """閾値戦略のパラメータ組み合わせを生成する。"""
    configs = []  # type: List[Dict]
    for bt in THRESHOLD_BUY_OPTIONS:
        for st in THRESHOLD_SELL_OPTIONS:
            for w1 in WINDOW_1M_OPTIONS:
                for w3 in WINDOW_3M_OPTIONS:
                    configs.append({
                        "variant": "threshold",
                        "buy_threshold": bt,
                        "sell_threshold": st,
                        "window_1m": w1,
                        "window_3m": w3,
                    })
    return configs


def generate_configs() -> List[Dict]:
    """全パラメータ組み合わせを生成する。"""
    return generate_label_configs() + generate_threshold_configs()


def get_all_etf_codes() -> List[str]:
    """DBから全ETFコードを取得する。"""
    rows = ETF.query.with_entities(ETF.code).order_by(ETF.code).all()
    return [r.code for r in rows]


def get_codes_with_data(
    codes: List[str], min_date: date,
) -> List[str]:
    """指定日以前のデータが存在するコードに絞り込む。"""
    valid = []  # type: List[str]
    for code in codes:
        count = (
            PriceHistory.query
            .filter(PriceHistory.etf_code == code)
            .filter(PriceHistory.date <= min_date)
            .filter(PriceHistory.close.isnot(None))
            .count()
        )
        if count > 0:
            valid.append(code)
    return valid


def sample_codes(codes: List[str], n: int = SAMPLE_SIZE) -> List[str]:
    """均等サンプリングでn銘柄を選択する。"""
    if len(codes) <= n:
        return codes
    step = len(codes) // n
    return codes[::step][:n]


def exclude_leveraged(codes: List[str]) -> List[str]:
    """レバレッジ/インバースETFを除外する。"""
    return [c for c in codes if c not in LEVERAGED_CODES]


def load_prices(
    etf_code: str, sim_start: date,
) -> List[Dict]:
    """DBから価格データを取得する（ウォームアップ期間含む）。"""
    data_start = sim_start - timedelta(days=150)
    records = (
        PriceHistory.query
        .filter(PriceHistory.etf_code == etf_code)
        .filter(PriceHistory.date >= data_start)
        .filter(PriceHistory.close.isnot(None))
        .order_by(PriceHistory.date.asc())
        .all()
    )
    return [{"date": r.date, "close": float(r.close)} for r in records]


def load_price_cache(
    codes: List[str], sim_start: date,
) -> Dict[str, List[Dict]]:
    """複数ETFの価格データを一括ロードする。"""
    cache = {}  # type: Dict[str, List[Dict]]
    for code in codes:
        cache[code] = load_prices(code, sim_start)
        print(
            f"  Loaded {code}: {len(cache[code])} records",
            file=sys.stderr,
        )
    return cache


def calc_risk_adjusted(result: Dict) -> float:
    """リスク調整リターン = return_pct / max(max_drawdown, 1.0)。"""
    return result["return_pct"] / max(result["max_drawdown"], 1.0)


def run_single_config(
    config: Dict, price_cache: Dict[str, List[Dict]],
) -> List[Dict]:
    """1設定を全ETFで実行し、個別結果リストを返す。"""
    strategy = MomentumStrategy(**config)
    engine = SimulationEngine(capital=1_000_000)
    results = []  # type: List[Dict]
    for prices in price_cache.values():
        if not prices:
            continue
        signals = strategy.generate_signals(prices)
        result = engine.run(signals)
        results.append(result)
    return results


def score_median(results: List[Dict]) -> float:
    """中央値ベースのリスク調整リターンを算出する。"""
    scores = [calc_risk_adjusted(r) for r in results]
    if not scores:
        return 0.0
    return statistics.median(scores)


def score_bh_win_rate(results: List[Dict]) -> float:
    """Buy&Hold勝率（戦略がBHを上回った割合%）を算出する。"""
    if not results:
        return 0.0
    wins = sum(
        1 for r in results
        if r["return_pct"] > r["buy_and_hold_return"]
    )
    return wins / len(results) * 100


def build_patterns(
    all_codes: List[str],
) -> List[Dict]:
    """4つの検証パターン定義を構築する。"""
    random.seed(42)
    normal_codes = exclude_leveraged(all_codes)

    # Pattern A & B: 1年、通常ETFのみ
    codes_ab = sample_codes(normal_codes)
    # Pattern C: 3年、通常ETFのみ（3年以上データあり）
    codes_c_pool = get_codes_with_data(
        normal_codes, date(2022, 1, 1),
    )
    codes_c = sample_codes(codes_c_pool)
    # Pattern D: 1年、全ETF（レバ含む）
    codes_d = sample_codes(all_codes)

    return [
        {
            "name": "Pattern A: 中央値ベース（1年、通常ETFのみ）",
            "sim_start": date(2024, 1, 1),
            "codes": codes_ab,
            "score_fn": score_median,
            "score_label": "MedScore",
        },
        {
            "name": "Pattern B: Buy&Hold勝率（1年、通常ETFのみ）",
            "sim_start": date(2024, 1, 1),
            "codes": codes_ab,
            "score_fn": score_bh_win_rate,
            "score_label": "BH_WinRate",
        },
        {
            "name": "Pattern C: 長期3年（通常ETFのみ）",
            "sim_start": date(2022, 1, 1),
            "codes": codes_c,
            "score_fn": score_median,
            "score_label": "MedScore",
        },
        {
            "name": "Pattern D: 全ETF中央値（レバ含む）",
            "sim_start": date(2024, 1, 1),
            "codes": codes_d,
            "score_fn": score_median,
            "score_label": "MedScore",
        },
    ]


def run_pattern(
    pattern: Dict, configs: List[Dict],
) -> List[Tuple[Dict, float]]:
    """1パターンの全設定を実行しスコア付きリストを返す。"""
    print(
        f"\n--- {pattern['name']} ({len(pattern['codes'])}銘柄) ---",
        file=sys.stderr,
    )
    cache = load_price_cache(pattern["codes"], pattern["sim_start"])
    total = len(configs)
    scored = []  # type: List[Tuple[Dict, float]]

    for i, config in enumerate(configs):
        results = run_single_config(config, cache)
        score = pattern["score_fn"](results)
        scored.append((config, score))
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{total}", file=sys.stderr)

    print(f"  Done ({total} configs)", file=sys.stderr)
    return scored


def format_condition(config: Dict) -> Tuple[str, str]:
    """設定からBuy/Sell条件の表示文字列を返す。"""
    if config["variant"] == "label":
        buy = ",".join(sorted(config["buy_labels"]))
        sell = ",".join(sorted(config["sell_labels"]))
    else:
        buy = f"buy>{config['buy_threshold']}%"
        sell = f"sell<{config['sell_threshold']}%"
    return buy, sell


def config_key(config: Dict) -> str:
    """設定をユニークキーに変換する。"""
    buy_cond, sell_cond = format_condition(config)
    w = f"{config['window_1m']}/{config['window_3m']}"
    return f"{config['variant']}|{w}|{buy_cond}|{sell_cond}"


def print_pattern_ranking(
    pattern_name: str,
    scored: List[Tuple[Dict, float]],
    score_label: str,
    top_n: int = 10,
) -> None:
    """パターン別ランキングを表示する。"""
    sorted_scored = sorted(scored, key=lambda x: x[1], reverse=True)
    print(f"\n{'=' * 110}")
    print(f" {pattern_name}")
    print(f"{'=' * 110}")
    _print_pattern_header(score_label)

    for rank, (config, score) in enumerate(sorted_scored[:top_n], 1):
        _print_pattern_row(rank, config, score)
    print(f"{'=' * 110}")


def _print_pattern_header(score_label: str) -> None:
    """パターンランキングのヘッダーを表示する。"""
    print(
        f"{'Rank':>4}  {'Strategy':<10} {'Window':<8} "
        f"{'Buy Condition':<28} {'Sell Condition':<28} "
        f"{score_label:>10}"
    )
    print(
        f"{'----':>4}  {'----------':<10} {'--------':<8} "
        f"{'----------------------------':<28} {'----------------------------':<28} "
        f"{'----------':>10}"
    )


def _print_pattern_row(
    rank: int, config: Dict, score: float,
) -> None:
    """パターンランキングの1行を表示する。"""
    buy_cond, sell_cond = format_condition(config)
    window = f"{config['window_1m']}/{config['window_3m']}"
    print(
        f"{rank:>4}  {config['variant']:<10} {window:<8} "
        f"{buy_cond:<28} {sell_cond:<28} "
        f"{score:>10.2f}"
    )


def build_rank_map(
    scored: List[Tuple[Dict, float]],
) -> Dict[str, int]:
    """スコアリストから {config_key: 順位} のマップを返す。"""
    sorted_scored = sorted(scored, key=lambda x: x[1], reverse=True)
    return {
        config_key(cfg): rank
        for rank, (cfg, _) in enumerate(sorted_scored, 1)
    }


def compute_comprehensive(
    all_rank_maps: List[Dict[str, int]],
    configs: List[Dict],
    total_configs: int,
) -> List[Tuple[Dict, float, List[int]]]:
    """総合ランキングを算出する。平均順位が低いほど良い。"""
    results = []  # type: List[Tuple[Dict, float, List[int]]]
    for config in configs:
        key = config_key(config)
        ranks = [
            rm.get(key, total_configs)
            for rm in all_rank_maps
        ]
        avg_rank = sum(ranks) / len(ranks)
        results.append((config, avg_rank, ranks))
    results.sort(key=lambda x: x[1])
    return results


def print_comprehensive(
    ranked: List[Tuple[Dict, float, List[int]]],
    top_n: int = 10,
) -> None:
    """総合ランキングを表示する。"""
    print(f"\n{'=' * 130}")
    print(" COMPREHENSIVE RANKING (Top 10)")
    print(f"{'=' * 130}")
    _print_comp_header()
    for rank, (config, avg, ranks) in enumerate(ranked[:top_n], 1):
        _print_comp_row(rank, config, avg, ranks)
    print(f"{'=' * 130}")


def _print_comp_header() -> None:
    """総合ランキングのヘッダーを表示する。"""
    print(
        f"{'Rank':>4}  {'Strategy':<10} {'Window':<8} "
        f"{'Buy Condition':<28} {'Sell Condition':<28} "
        f"{'AvgRank':>8} {'A-Rank':>7} {'B-Rank':>7} "
        f"{'C-Rank':>7} {'D-Rank':>7}"
    )
    print(
        f"{'----':>4}  {'----------':<10} {'--------':<8} "
        f"{'----------------------------':<28} {'----------------------------':<28} "
        f"{'--------':>8} {'-------':>7} {'-------':>7} "
        f"{'-------':>7} {'-------':>7}"
    )


def _print_comp_row(
    rank: int,
    config: Dict,
    avg_rank: float,
    ranks: List[int],
) -> None:
    """総合ランキングの1行を表示する。"""
    buy_cond, sell_cond = format_condition(config)
    window = f"{config['window_1m']}/{config['window_3m']}"
    print(
        f"{rank:>4}  {config['variant']:<10} {window:<8} "
        f"{buy_cond:<28} {sell_cond:<28} "
        f"{avg_rank:>8.1f} {ranks[0]:>7d} {ranks[1]:>7d} "
        f"{ranks[2]:>7d} {ranks[3]:>7d}"
    )


def print_default_in_comprehensive(
    ranked: List[Tuple[Dict, float, List[int]]],
) -> None:
    """現行デフォルト設定の総合順位を表示する。"""
    default_key = _default_config_key()
    for rank, (config, avg, ranks) in enumerate(ranked, 1):
        if config_key(config) == default_key:
            print("Current default:")
            _print_comp_row(rank, config, avg, ranks)
            return
    print("Current default: not found in grid")


def _default_config_key() -> str:
    """現行デフォルト設定のキーを返す。"""
    default_config = {
        "variant": "label",
        "buy_labels": frozenset({"上昇加速", "反転上昇"}),
        "sell_labels": frozenset({"失速", "下降減速", "下降維持", "下降加速"}),
        "window_1m": 30,
        "window_3m": 90,
    }
    return config_key(default_config)


def main() -> int:
    """4パターン包括的最適化を実行する。"""
    start_time = time.time()
    app = create_app()

    with app.app_context():
        all_codes = get_all_etf_codes()
        print(f"Total ETFs in DB: {len(all_codes)}", file=sys.stderr)

        patterns = build_patterns(all_codes)
        configs = generate_configs()
        total = len(configs)
        print(f"Total configs: {total}", file=sys.stderr)

        all_rank_maps = []  # type: List[Dict[str, int]]
        all_scored = []  # type: List[Tuple[List[Tuple[Dict, float]], Dict]]

        for pattern in patterns:
            scored = run_pattern(pattern, configs)
            all_scored.append((scored, pattern))
            all_rank_maps.append(build_rank_map(scored))

        # パターン別ランキング表示
        for scored, pattern in all_scored:
            print_pattern_ranking(
                pattern["name"], scored, pattern["score_label"],
            )

        # 総合ランキング
        ranked = compute_comprehensive(
            all_rank_maps, configs, total,
        )
        print_comprehensive(ranked)
        print_default_in_comprehensive(ranked)
        print(f"{'=' * 130}")

    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.0f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
