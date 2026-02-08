"""モメンタム戦略パラメータ最適化（グリッドサーチ）。

リスク調整リターン（return_pct / max_drawdown）が最良の設定を探索する。

Usage:
    docker compose exec backend python scripts/simulation/optimize.py
"""

import os
import sys
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
from src.models.price_history import PriceHistory  # noqa: E402

from simulation.engine import SimulationEngine  # noqa: E402
from simulation.strategies.momentum import MomentumStrategy  # noqa: E402

# --- パラメータグリッド定義 ---

LABEL_BUY_OPTIONS: List[frozenset] = [
    frozenset({"上昇加速"}),
    frozenset({"上昇加速", "反転上昇"}),  # 現行デフォルト
    frozenset({"上昇加速", "上昇維持"}),
    frozenset({"上昇加速", "上昇維持", "反転上昇"}),
    frozenset({"上昇加速", "上昇維持", "上昇減速"}),
    frozenset({"上昇加速", "上昇維持", "上昇減速", "反転上昇"}),
]

LABEL_SELL_OPTIONS: List[frozenset] = [
    frozenset({"下降加速"}),
    frozenset({"下降加速", "下降維持"}),
    frozenset({"下降加速", "下降維持", "下降減速"}),
    frozenset({"失速", "下降加速", "下降維持", "下降減速"}),  # 現行デフォルト
    frozenset({"失速"}),
]

THRESHOLD_BUY_OPTIONS = [5, 10, 15, 20, 25]
THRESHOLD_SELL_OPTIONS = [-10, -5, 0, 5]

WINDOW_1M_OPTIONS = [20, 30, 45]
WINDOW_3M_OPTIONS = [60, 90, 120]

TARGET_ETFS = [
    "1306", "1489", "1545", "1655", "1678",
    "2559", "1326", "1343", "1615", "2644",
]

SIM_START = date(2024, 1, 1)


# --- 価格データロード ---


def load_prices(etf_code: str) -> List[Dict]:
    """DBから価格データを取得する（ウォームアップ期間含む）。"""
    data_start = SIM_START - timedelta(days=120)
    records = (
        PriceHistory.query
        .filter(PriceHistory.etf_code == etf_code)
        .filter(PriceHistory.date >= data_start)
        .filter(PriceHistory.close.isnot(None))
        .order_by(PriceHistory.date.asc())
        .all()
    )
    return [{"date": r.date, "close": float(r.close)} for r in records]


# --- スコア計算 ---


def calc_score(result: Dict) -> float:
    """リスク調整リターン = return_pct / max(max_drawdown, 1.0)。"""
    return result["return_pct"] / max(result["max_drawdown"], 1.0)


# --- 設定生成 ---


def generate_label_configs() -> List[Dict]:
    """ラベル戦略のパラメータ組み合わせを生成する。"""
    configs: List[Dict] = []
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
    configs: List[Dict] = []
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


# --- シミュレーション実行 ---


def run_config(
    config: Dict, price_cache: Dict[str, List[Dict]],
) -> Dict:
    """1設定を全ETFで実行し平均スコアを返す。"""
    strategy = MomentumStrategy(**config)
    engine = SimulationEngine(capital=1_000_000)

    scores: List[float] = []
    returns: List[float] = []
    win_rates: List[float] = []
    drawdowns: List[float] = []

    for prices in price_cache.values():
        if not prices:
            continue
        signals = strategy.generate_signals(prices)
        result = engine.run(signals)
        scores.append(calc_score(result))
        returns.append(result["return_pct"])
        win_rates.append(result["win_rate"])
        drawdowns.append(result["max_drawdown"])

    n = len(scores)
    if n == 0:
        return _empty_scores()

    return {
        "avg_score": sum(scores) / n,
        "avg_return": sum(returns) / n,
        "avg_win_rate": sum(win_rates) / n,
        "avg_drawdown": sum(drawdowns) / n,
    }


def _empty_scores() -> Dict:
    """ETFデータが無い場合のデフォルトスコア。"""
    return {
        "avg_score": 0.0,
        "avg_return": 0.0,
        "avg_win_rate": 0.0,
        "avg_drawdown": 0.0,
    }


# --- 表示フォーマット ---


def format_condition(config: Dict) -> Tuple[str, str]:
    """設定からBuy/Sell条件の表示文字列を返す。"""
    if config["variant"] == "label":
        buy = ",".join(sorted(config["buy_labels"]))
        sell = ",".join(sorted(config["sell_labels"]))
    else:
        buy = f"buy>{config['buy_threshold']}%"
        sell = f"sell<{config['sell_threshold']}%"
    return buy, sell


def print_ranking(
    results: List[Tuple[Dict, Dict]], top_n: int = 10,
) -> None:
    """ランキングを表形式で出力する。"""
    sorted_results = sorted(
        results, key=lambda x: x[1]["avg_score"], reverse=True,
    )

    _print_header()
    _print_table_header()

    for rank, (config, scores) in enumerate(sorted_results[:top_n], 1):
        _print_row(rank, config, scores)

    _print_separator()
    _print_default_result(results)
    _print_separator()


def _print_header() -> None:
    """出力ヘッダーを表示する。"""
    print("=" * 120)
    print("Optimization Results: TOP 10")
    print("=" * 120)


def _print_table_header() -> None:
    """テーブルヘッダーを表示する。"""
    print(
        f"{'Rank':>4}  {'Strategy':<10} {'Window':<8} "
        f"{'Buy Condition':<24} {'Sell Condition':<24} "
        f"{'Avg Return':>10} {'Avg WinRate':>11} "
        f"{'Avg MaxDD':>9} {'Score':>7}"
    )
    print(
        f"{'----':>4}  {'----------':<10} {'--------':<8} "
        f"{'------------------------':<24} {'------------------------':<24} "
        f"{'----------':>10} {'-----------':>11} "
        f"{'---------':>9} {'------':>7}"
    )


def _print_row(rank: int, config: Dict, scores: Dict) -> None:
    """ランキング1行を表示する。"""
    buy_cond, sell_cond = format_condition(config)
    window = f"{config['window_1m']}/{config['window_3m']}"
    print(
        f"{rank:>4}  {config['variant']:<10} {window:<8} "
        f"{buy_cond:<24} {sell_cond:<24} "
        f"{scores['avg_return']:>+9.1f}% "
        f"{scores['avg_win_rate']:>10.1f}% "
        f"{scores['avg_drawdown']:>8.1f}% "
        f"{scores['avg_score']:>7.2f}"
    )


def _print_separator() -> None:
    """区切り線を出力する。"""
    print("=" * 120)


def _print_default_result(
    results: List[Tuple[Dict, Dict]],
) -> None:
    """現行デフォルト設定の結果を表示する。"""
    default = _find_default(results)
    if default is None:
        print("Current default: not found in grid")
        return

    config, scores = default
    buy_cond, sell_cond = format_condition(config)
    window = f"{config['window_1m']}/{config['window_3m']}"
    print(
        f"Current default:\n"
        f"      {config['variant']:<10} {window:<8} "
        f"{buy_cond:<24} {sell_cond:<24} "
        f"{scores['avg_return']:>+9.1f}% "
        f"{scores['avg_win_rate']:>10.1f}% "
        f"{scores['avg_drawdown']:>8.1f}% "
        f"{scores['avg_score']:>7.2f}"
    )


def _find_default(
    results: List[Tuple[Dict, Dict]],
) -> Tuple[Dict, Dict]:
    """現行デフォルト設定を結果リストから探す。"""
    default_buy = frozenset({"上昇加速", "反転上昇"})
    default_sell = frozenset({"失速", "下降減速", "下降維持", "下降加速"})

    for config, scores in results:
        if (
            config["variant"] == "label"
            and config.get("buy_labels") == default_buy
            and config.get("sell_labels") == default_sell
            and config["window_1m"] == 30
            and config["window_3m"] == 90
        ):
            return config, scores
    return None


# --- メイン ---


def main() -> int:
    """グリッドサーチを実行しランキングを表示する。"""
    app = create_app()
    with app.app_context():
        price_cache = _load_all_prices()
        configs = generate_configs()
        total = len(configs)

        print(
            f"Starting optimization: {total} configs x "
            f"{len(TARGET_ETFS)} ETFs",
            file=sys.stderr,
        )

        results = _run_all_configs(configs, price_cache, total)
        print_ranking(results)

    return 0


def _load_all_prices() -> Dict[str, List[Dict]]:
    """全ETFの価格データを一括ロードする。"""
    cache: Dict[str, List[Dict]] = {}
    for code in TARGET_ETFS:
        cache[code] = load_prices(code)
        count = len(cache[code])
        print(f"  Loaded {code}: {count} records", file=sys.stderr)
    return cache


def _run_all_configs(
    configs: List[Dict],
    price_cache: Dict[str, List[Dict]],
    total: int,
) -> List[Tuple[Dict, Dict]]:
    """全設定のシミュレーションを実行する。"""
    results: List[Tuple[Dict, Dict]] = []
    for i, config in enumerate(configs):
        scores = run_config(config, price_cache)
        results.append((config, scores))
        if (i + 1) % 50 == 0:
            print(
                f"Progress: {i + 1}/{total}",
                file=sys.stderr,
            )
    return results


if __name__ == "__main__":
    sys.exit(main())
