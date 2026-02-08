"""回帰計算ユーティリティ。

最小二乗法による直線回帰から価格のリターン率を算出する。
update_etf_data.py:463-523 のロジックをリスト入力に適合。
"""

import math
from typing import List, Optional


def calculate_regression_return(
    prices: List, days: int
) -> Optional[float]:
    """価格リストから回帰上昇率を計算する。

    最小二乗法で直線回帰（y = ax + b）をフィットし、
    回帰直線の開始値と終値からリターン率を計算。

    Args:
        prices: 終値のリスト（古い順）
        days: 期間日数

    Returns:
        回帰リターン率（%）またはNone
    """
    if len(prices) < 2:
        return None

    # 50%以上のデータがなければ不十分
    if len(prices) < days * 0.5:
        return None

    # 末尾 min(days, len(prices)) 件を使用
    period_prices = prices[-min(days, len(prices)):]

    # NaN / None をスキップ
    valid = _filter_valid_prices(period_prices)
    if len(valid) < 2:
        return None

    return _fit_and_calc_return(valid)


def _filter_valid_prices(prices: List) -> List[float]:
    """NaN・Noneを除外した有効価格リストを返す。"""
    result = []
    for p in prices:
        if p is None:
            continue
        if isinstance(p, float) and math.isnan(p):
            continue
        result.append(float(p))
    return result


def _fit_and_calc_return(prices: List[float]) -> Optional[float]:
    """最小二乗法で直線回帰し、リターン率(%)を返す。"""
    n = len(prices)

    sum_x = sum(range(n))
    sum_y = sum(prices)
    sum_xy = sum(i * prices[i] for i in range(n))
    sum_x2 = sum(i * i for i in range(n))

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return None

    a = (n * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - a * sum_x) / n

    start_value = b
    end_value = a * (n - 1) + b

    if start_value == 0:
        return None

    return round(((end_value - start_value) / start_value) * 100, 2)
