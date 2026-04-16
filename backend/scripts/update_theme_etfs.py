"""テーマETF週次自動選定スクリプト

候補プール (backend/config/theme_etfs.json) の全銘柄をyfinanceで取得し、
3指標でスコアリングして上位3-5銘柄を active_theme_etfs.json に出力する。

スコアリング指標:
  - abs(5日騰落率): 重み40%
  - 出来高増加率 (vs 20日平均): 重み40%
  - 日経225との騰落率乖離: 重み20%

使い方:
  python backend/scripts/update_theme_etfs.py           # 通常実行
  python backend/scripts/update_theme_etfs.py --dry-run # 標準出力のみ
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# プロジェクトルートを特定（backend/scripts/ → backend/ → project root）
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 環境変数設定（本番環境用）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

# Yahoo Finance API 429エラー対策: User-Agentを強制的に上書き
import requests  # noqa: E402

original_prepare_request = requests.Session.prepare_request


def custom_prepare_request(self, request):
    request.headers[
        "User-Agent"
    ] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    return original_prepare_request(self, request)


requests.Session.prepare_request = custom_prepare_request

import yfinance as yf  # noqa: E402

JST = timezone(timedelta(hours=9))

CANDIDATES_PATH = BACKEND_DIR / "config" / "theme_etfs.json"
OUTPUT_PATH = BACKEND_DIR / "config" / "active_theme_etfs.json"

# 日経225のティッカー（乖離率算出用）
NIKKEI_SYMBOL = "^N225"

# 選定パラメータ
MAX_ACTIVE = 5
MIN_ACTIVE = 3
MAX_PER_THEME = 2

# 重み
WEIGHT_CHANGE_5D = 0.4
WEIGHT_VOLUME_RATIO = 0.4
WEIGHT_NIKKEI_DIVERGENCE = 0.2


def load_candidates():
    """候補プールJSONを読み込む"""
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["candidates"]


def fetch_nikkei_change_5d():
    """日経225の5日騰落率を取得"""
    try:
        ticker = yf.Ticker(NIKKEI_SYMBOL)
        hist = ticker.history(period="1mo")
        if len(hist) < 6:
            return 0.0
        price = float(hist.iloc[-1]["Close"])
        price_5d = float(hist.iloc[-6]["Close"])
        return ((price - price_5d) / price_5d) * 100
    except Exception as e:
        print(f"WARNING: 日経225取得失敗: {e}", file=sys.stderr)
        return 0.0


def score_candidate(candidate, nikkei_change_5d):
    """個別銘柄のスコアリングデータを取得

    Returns:
        dict with scoring data or None on failure
    """
    symbol = candidate["symbol"]
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")

        if len(hist) < 6:
            print(f"SKIP: {symbol} データ不足 ({len(hist)}行)", file=sys.stderr)
            return None

        price = float(hist.iloc[-1]["Close"])
        price_5d = float(hist.iloc[-6]["Close"])
        change_5d = ((price - price_5d) / price_5d) * 100

        # 出来高増加率 (直近5日平均 vs 20日平均)
        volumes = [float(row["Volume"]) for _, row in hist.iterrows()]
        if len(volumes) >= 20:
            vol_recent = sum(volumes[-5:]) / 5
            vol_20d = sum(volumes[-20:]) / 20
            volume_ratio = vol_recent / vol_20d if vol_20d > 0 else 1.0
        elif len(volumes) >= 5:
            vol_recent = sum(volumes[-5:]) / 5
            vol_all = sum(volumes) / len(volumes)
            volume_ratio = vol_recent / vol_all if vol_all > 0 else 1.0
        else:
            volume_ratio = 1.0

        # 日経225との騰落率乖離
        nikkei_divergence = abs(change_5d - nikkei_change_5d)

        return {
            "change_5d": round(change_5d, 2),
            "volume_ratio": round(volume_ratio, 2),
            "nikkei_divergence": round(nikkei_divergence, 2),
        }

    except Exception as e:
        print(f"SKIP: {symbol} 取得失敗: {e}", file=sys.stderr)
        return None


def normalize_min_max(values):
    """min-max正規化 (0-1)"""
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [0.5] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]


def select_active(scored_candidates):
    """スコア上位から同一テーマ制約を適用して3-5銘柄を選定"""
    # スコア降順ソート
    sorted_candidates = sorted(
        scored_candidates, key=lambda x: x["score"], reverse=True
    )

    selected = []
    theme_count = {}

    for c in sorted_candidates:
        theme = c["theme"]
        if theme_count.get(theme, 0) >= MAX_PER_THEME:
            continue
        selected.append(c)
        theme_count[theme] = theme_count.get(theme, 0) + 1
        if len(selected) >= MAX_ACTIVE:
            break

    return selected


def main():
    dry_run = "--dry-run" in sys.argv

    # 候補プール読み込み
    candidates = load_candidates()
    print(f"候補プール: {len(candidates)}銘柄", file=sys.stderr)

    # 日経225の5日騰落率を取得
    nikkei_change_5d = fetch_nikkei_change_5d()
    print(f"日経225 5日騰落率: {nikkei_change_5d:.2f}%", file=sys.stderr)

    # 各銘柄のスコアリングデータ取得
    scoring_data = []
    for c in candidates:
        data = score_candidate(c, nikkei_change_5d)
        if data is not None:
            scoring_data.append({**c, **data})

    if len(scoring_data) < MIN_ACTIVE:
        print(
            f"ERROR: 有効銘柄数 {len(scoring_data)} < 最低 {MIN_ACTIVE}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"有効銘柄: {len(scoring_data)}/{len(candidates)}", file=sys.stderr)

    # min-max正規化
    abs_changes = [abs(d["change_5d"]) for d in scoring_data]
    vol_ratios = [d["volume_ratio"] for d in scoring_data]
    divergences = [d["nikkei_divergence"] for d in scoring_data]

    norm_changes = normalize_min_max(abs_changes)
    norm_volumes = normalize_min_max(vol_ratios)
    norm_divergences = normalize_min_max(divergences)

    # 総合スコア算出
    for i, d in enumerate(scoring_data):
        score = (
            WEIGHT_CHANGE_5D * norm_changes[i]
            + WEIGHT_VOLUME_RATIO * norm_volumes[i]
            + WEIGHT_NIKKEI_DIVERGENCE * norm_divergences[i]
        )
        d["score"] = round(score, 2)

    # 上位選定
    active = select_active(scoring_data)

    # 出力JSON構築
    now = datetime.now(JST)
    valid_until = now + timedelta(days=7)
    output = {
        "generated_at": now.isoformat(),
        "valid_until": valid_until.isoformat(),
        "active": [
            {
                "key": a["key"],
                "symbol": a["symbol"],
                "name": a["name"],
                "theme": a["theme"],
                "etf_code": a["etf_code"],
                "score": a["score"],
                "change_5d": a["change_5d"],
                "volume_ratio": a["volume_ratio"],
                "nikkei_divergence": a["nikkei_divergence"],
            }
            for a in active
        ],
    }

    output_json = json.dumps(output, ensure_ascii=False, indent=2)

    if dry_run:
        print(output_json)
        print(f"\n選定: {len(active)}銘柄 (dry-run)", file=sys.stderr)
    else:
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(output_json + "\n")
        print(f"選定: {len(active)}銘柄 → {OUTPUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
