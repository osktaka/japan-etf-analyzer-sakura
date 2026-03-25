"""market_data_quick.py の出力JSONをバリデーションするスクリプト

標準入力からJSONを受け取り、バリデーション結果をJSON形式で標準出力に出力する。

使い方:
  python market_data_quick.py | python market_data_validate.py
  python market_data_quick.py | python market_data_validate.py --prev prev_data.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


# バリデーション対象外のメタデータキー
META_KEYS = {
    "fetched_at",
    "fetch_duration_sec",
    "ticker_count",
    "errors",
    "technical_summary",
    "yield_curve",
}

# 必須キー（存在しなければERROR）
CRITICAL_KEYS = {"sp500", "vix", "usdjpy", "nikkei_futures"}

# extreme_change 閾値（±%）
EXTREME_CHANGE_THRESHOLDS = {
    "sp500": 10.0,
    "nasdaq": 10.0,
    "dow": 10.0,
    "nikkei225": 8.0,
}

# extreme VIX 閾値
EXTREME_VIX_THRESHOLD = 80.0

# 主要指数の妥当レンジ（2026年時点の概算。大幅な変動があっても範囲外にはならない広さ）
INDEX_RANGES = {
    "sp500": (3000, 15000),
    "nasdaq": (10000, 50000),
    "dow": (20000, 80000),
    "nikkei225": (20000, 80000),
    "nikkei_futures": (20000, 80000),
    "sox": (1000, 20000),
}

# price_consistency: 逆方向乖離の閾値（%）
CONSISTENCY_DIVERGENCE_THRESHOLD = 5.0

# prev_deviation: 前回値との乖離閾値（±%）
PREV_DEVIATION_THRESHOLD = 5.0
PREV_DEVIATION_KEYS = {"sp500", "nasdaq", "nikkei_futures", "usdjpy", "vix"}


def validate_prev_deviation(current_data, prev_data):
    """前回取得値との乖離をチェックし、警告リストを返す。"""
    warnings = []
    for key in PREV_DEVIATION_KEYS:
        cur_entry = current_data.get(key)
        prev_entry = prev_data.get(key)
        if not isinstance(cur_entry, dict) or not isinstance(prev_entry, dict):
            continue
        cur_price = cur_entry.get("price")
        prev_price = prev_entry.get("price")
        if cur_price is None or prev_price is None or prev_price == 0:
            continue
        deviation = (cur_price - prev_price) / prev_price * 100
        if abs(deviation) > PREV_DEVIATION_THRESHOLD:
            warnings.append(
                f"prev_deviation: {key} 前回値 {prev_price} → 今回値 {cur_price} "
                f"(乖離: {deviation:+.2f}%、閾値: ±{PREV_DEVIATION_THRESHOLD}%)"
            )
    return warnings


def validate(data, prev_data=None):
    """市場データJSONをバリデーションする。

    Args:
        data: 現在の市場データJSON
        prev_data: 前回の市場データJSON（省略可）

    Returns:
        dict: {"status", "errors", "warnings", "summary"}
    """
    errors = []
    warnings = []

    # JSON内のerrorsキーをチェック
    json_errors = data.get("errors", [])
    if json_errors:
        for err_msg in json_errors:
            errors.append(f"fetch_error: {err_msg}")

    # ティッカーキーを抽出
    ticker_keys = [k for k in data.keys() if k not in META_KEYS]
    total_tickers = data.get("ticker_count", len(ticker_keys))
    success_count = len(ticker_keys)

    # missing_critical: 必須キーの存在チェック
    for key in CRITICAL_KEYS:
        if key not in data:
            errors.append(f"missing_critical: {key} が存在しません")

    # stale_data: fetched_atから2営業日以上前のデータがないか
    fetched_at_str = data.get("fetched_at")
    if fetched_at_str:
        try:
            fetched_at = datetime.fromisoformat(fetched_at_str)
            now = datetime.now(fetched_at.tzinfo) if fetched_at.tzinfo else datetime.now()
            # 全ティッカーがclosed かつ 取得時刻が営業日内なら stale の可能性
            all_closed = all(
                isinstance(data.get(k), dict) and data[k].get("status") == "closed"
                for k in ticker_keys
                if isinstance(data.get(k), dict) and "status" in data.get(k, {})
            )
            # fetched_atの曜日確認（土日は市場休場のため除外）
            is_weekday = now.weekday() < 5
            if all_closed and is_weekday:
                warnings.append(
                    "stale_data: 全ティッカーのstatusがclosed（"
                    "市場休場日でなければデータが古い可能性あり）"
                )
        except (ValueError, TypeError):
            pass

    # 各ティッカーのバリデーション
    for name in ticker_keys:
        entry = data[name]
        if not isinstance(entry, dict):
            continue

        price = entry.get("price")
        change_pct = entry.get("change_pct")

        # nan_values: price/change_pct が None
        if price is None:
            errors.append(f"nan_values: {name}.price が null です")
        if change_pct is None:
            errors.append(f"nan_values: {name}.change_pct が null です")

        # zero_price: price が 0.0
        if price == 0.0:
            errors.append(f"zero_price: {name}.price が 0.0 です")

        # extreme_change: 異常な騰落率
        if name in EXTREME_CHANGE_THRESHOLDS and change_pct is not None:
            threshold = EXTREME_CHANGE_THRESHOLDS[name]
            if abs(change_pct) > threshold:
                warnings.append(
                    f"extreme_change: {name}.change_pct = {change_pct}% "
                    f"(閾値: ±{threshold}%)"
                )

        # extreme_vix: VIX が異常値
        if name == "vix" and price is not None and price > EXTREME_VIX_THRESHOLD:
            warnings.append(
                f"extreme_vix: vix = {price} (閾値: {EXTREME_VIX_THRESHOLD})"
            )

    # index_range_check: 主要指数が妥当な範囲内にあるか確認
    for name, (range_min, range_max) in INDEX_RANGES.items():
        entry = data.get(name)
        if not isinstance(entry, dict):
            continue
        price = entry.get("price")
        if price is not None and not (range_min <= price <= range_max):
            errors.append(
                f"index_range: {name}.price = {price} が"
                f"レンジ({range_min}-{range_max})外です。"
                f"データの桁落ちまたは取得エラーの可能性"
            )

    # price_consistency_check: 関連指数間の逆方向大幅乖離を検出
    sp500_entry = data.get("sp500", {})
    nasdaq_entry = data.get("nasdaq", {})
    if isinstance(sp500_entry, dict) and isinstance(nasdaq_entry, dict):
        sp500_chg = sp500_entry.get("change_pct")
        nasdaq_chg = nasdaq_entry.get("change_pct")
        if sp500_chg is not None and nasdaq_chg is not None:
            threshold = CONSISTENCY_DIVERGENCE_THRESHOLD
            if (sp500_chg > threshold and nasdaq_chg < -threshold) or \
               (sp500_chg < -threshold and nasdaq_chg > threshold):
                warnings.append(
                    f"price_consistency: sp500 ({sp500_chg:+.2f}%) と "
                    f"nasdaq ({nasdaq_chg:+.2f}%) が逆方向に大幅乖離"
                    f"（閾値: ±{threshold}%）"
                )

    # cross_consistency: S&P500とVIXの3日騰落率が両方正
    sp500_entry = data.get("sp500", {})
    vix_entry = data.get("vix", {})
    if isinstance(sp500_entry, dict) and isinstance(vix_entry, dict):
        sp500_3d = sp500_entry.get("change_3d")
        vix_3d = vix_entry.get("change_3d")
        if sp500_3d is not None and vix_3d is not None:
            if sp500_3d > 0 and vix_3d > 0:
                warnings.append(
                    f"cross_consistency: sp500 ({sp500_3d}%) と vix ({vix_3d}%) "
                    f"の3日騰落率が両方正（株上昇+VIX上昇の3日連続）"
                )

    # prev_deviation: 前回値との乖離チェック
    if prev_data is not None:
        warnings.extend(validate_prev_deviation(data, prev_data))

    # ステータス判定
    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    summary = f"{success_count}/{total_tickers}指標取得成功、バリデーション: {status}"

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(description="市場データJSONのバリデーション")
    parser.add_argument(
        "--prev", type=str, default=None,
        help="前回の市場データJSONファイルパス（乖離チェック用）",
    )
    args = parser.parse_args()

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        result = {
            "status": "FAIL",
            "errors": [f"JSONパースエラー: {str(e)}"],
            "warnings": [],
            "summary": "入力JSONの解析に失敗しました",
        }
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
        sys.exit(1)

    # 前回データの読み込み
    prev_data = None
    if args.prev:
        prev_path = Path(args.prev)
        if prev_path.exists():
            try:
                prev_data = json.loads(prev_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass  # 読み込み失敗時はスキップ

    result = validate(data, prev_data=prev_data)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()

    # FAILの場合は終了コード1
    if result["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
