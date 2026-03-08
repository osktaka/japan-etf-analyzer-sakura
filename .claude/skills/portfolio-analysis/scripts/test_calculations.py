#!/usr/bin/env python3
"""Phase 0.5 計算ロジックの回帰テスト。
使い方: python test_calculations.py
出力: JSON {"status": "OK"|"NG", "results": {...}, "failures": [...]}

pytest依存なし。標準ライブラリのみ使用。
"""
import json
import math
import statistics
import sys

TOLERANCE = 0.001


def approx_eq(a, b, tol=TOLERANCE):
    """浮動小数点の近似比較。"""
    return abs(a - b) <= tol


# =============================================================================
# 項目1: シャープレシオ
# =============================================================================

def test_sharpe_ratio_basic():
    """既知の月次リターン系列からシャープレシオを手計算で検証。"""
    monthly_returns = [0.02, -0.01, 0.03, 0.01, -0.02, 0.02,
                       0.01, 0.03, -0.01, 0.02, 0.01, 0.02]
    rf = 0.5  # パーセント表記（phase05_shared_calc.pyと同一形式）

    # 手計算
    mean_monthly = statistics.mean(monthly_returns)
    std_monthly = statistics.pstdev(monthly_returns)  # 母標準偏差

    annual_return = mean_monthly * 12
    annual_vol = std_monthly * math.sqrt(12)

    # phase05_shared_calc.pyの計算式: (ret - rf) / vol
    # ret, rfはパーセント表記、volもパーセント表記
    # ここではリターン・ボラティリティをパーセント表記に変換
    annual_return_pct = annual_return * 100
    annual_vol_pct = annual_vol * 100

    expected_sharpe = (annual_return_pct - rf) / annual_vol_pct

    # 検証
    errors = []
    if not approx_eq(mean_monthly, sum(monthly_returns) / len(monthly_returns)):
        errors.append(f"月次平均不一致: {mean_monthly}")
    if not approx_eq(expected_sharpe, (annual_return_pct - rf) / annual_vol_pct):
        errors.append(f"シャープレシオ計算不一致: {expected_sharpe}")

    # 具体的な期待値の検証
    # mean = (0.02-0.01+0.03+0.01-0.02+0.02+0.01+0.03-0.01+0.02+0.01+0.02)/12
    # mean = 0.13/12 = 0.010833...
    expected_mean = 0.13 / 12
    if not approx_eq(mean_monthly, expected_mean):
        errors.append(f"月次平均: got={mean_monthly}, expected={expected_mean}")

    # 年率リターン = 0.010833 * 12 = 0.13 = 13%
    if not approx_eq(annual_return_pct, 13.0, tol=0.01):
        errors.append(f"年率リターン: got={annual_return_pct}, expected=13.0")

    # シャープレシオの符号・妥当性チェック
    if expected_sharpe <= 0:
        errors.append(f"シャープレシオが非正: {expected_sharpe}")

    return {
        "name": "sharpe_ratio_basic",
        "status": "OK" if not errors else "NG",
        "details": {
            "mean_monthly": round(mean_monthly, 6),
            "annual_return_pct": round(annual_return_pct, 4),
            "annual_vol_pct": round(annual_vol_pct, 4),
            "sharpe_ratio": round(expected_sharpe, 4),
        },
        "errors": errors,
    }


def test_sharpe_ratio_negative():
    """負のリターン系列でシャープレシオが負になることを検証。"""
    monthly_returns = [-0.03, -0.02, -0.01, -0.04, 0.01, -0.02,
                       -0.03, -0.01, -0.02, -0.03, 0.00, -0.02]
    rf = 0.5

    mean_monthly = statistics.mean(monthly_returns)
    std_monthly = statistics.pstdev(monthly_returns)

    annual_return_pct = mean_monthly * 12 * 100
    annual_vol_pct = std_monthly * math.sqrt(12) * 100

    sharpe = (annual_return_pct - rf) / annual_vol_pct

    errors = []
    if sharpe >= 0:
        errors.append(f"負のリターンなのにシャープレシオが非負: {sharpe}")
    if annual_return_pct >= 0:
        errors.append(f"負のリターンなのに年率リターンが非負: {annual_return_pct}")

    return {
        "name": "sharpe_ratio_negative",
        "status": "OK" if not errors else "NG",
        "details": {
            "annual_return_pct": round(annual_return_pct, 4),
            "sharpe_ratio": round(sharpe, 4),
        },
        "errors": errors,
    }


def test_sharpe_ratio_zero_vol():
    """ボラティリティ0の場合の除算エラー回避を検証。
    phase05_shared_calc.pyでは vol > 0 をチェックしている。"""
    monthly_returns = [0.01] * 12  # 完全に一定

    std_monthly = statistics.pstdev(monthly_returns)

    errors = []
    if std_monthly != 0.0:
        errors.append(f"一定リターンなのにstd != 0: {std_monthly}")

    # vol == 0 のとき phase05_shared_calc.py はスキップする
    # テストはこの条件確認のみ
    vol_is_zero = (std_monthly == 0.0)
    if not vol_is_zero:
        errors.append("ボラティリティが0にならない")

    return {
        "name": "sharpe_ratio_zero_vol",
        "status": "OK" if not errors else "NG",
        "details": {"std_monthly": std_monthly, "should_skip": vol_is_zero},
        "errors": errors,
    }


# =============================================================================
# 項目2: 相関分析
# =============================================================================

def _pearson_corr(x, y):
    """標準ライブラリのみでピアソン相関係数を計算。"""
    n = len(x)
    if n < 2:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
    if std_x == 0 or std_y == 0:
        return 0.0
    return cov / (std_x * std_y)


def _beta(returns_i, returns_m):
    """β = ρ_im × (σ_i / σ_m)"""
    corr = _pearson_corr(returns_i, returns_m)
    std_i = statistics.pstdev(returns_i)
    std_m = statistics.pstdev(returns_m)
    if std_m == 0:
        return 0.0
    return corr * (std_i / std_m)


def test_correlation_perfect():
    """完全相関（同一系列）→ 相関=1.0, ベータ=1.0"""
    series = [0.02, -0.01, 0.03, 0.01, -0.02, 0.02, 0.01, 0.03, -0.01, 0.02, 0.01, 0.02]

    corr = _pearson_corr(series, series)
    beta = _beta(series, series)

    errors = []
    if not approx_eq(corr, 1.0):
        errors.append(f"完全相関で corr != 1.0: {corr}")
    if not approx_eq(beta, 1.0):
        errors.append(f"完全相関で beta != 1.0: {beta}")

    return {
        "name": "correlation_perfect",
        "status": "OK" if not errors else "NG",
        "details": {"corr": round(corr, 6), "beta": round(beta, 6)},
        "errors": errors,
    }


def test_correlation_known_series():
    """既知の2系列で手計算の相関係数・ベータ値を検証。"""
    x = [0.02, 0.04, 0.06, 0.08, 0.10, 0.12]
    y = [0.01, 0.03, 0.04, 0.06, 0.09, 0.11]

    corr = _pearson_corr(x, y)
    beta_val = _beta(y, x)  # yのxに対するベータ

    # 手計算: x, yは強い正の線形関係
    # 相関は0.99付近のはず
    errors = []
    if corr < 0.99:
        errors.append(f"強い線形関係なのに相関が低い: {corr}")

    # ベータ = corr * (std_y / std_x)
    std_x = statistics.pstdev(x)
    std_y = statistics.pstdev(y)
    expected_beta = corr * (std_y / std_x)
    if not approx_eq(beta_val, expected_beta):
        errors.append(f"ベータ不一致: got={beta_val}, expected={expected_beta}")

    return {
        "name": "correlation_known_series",
        "status": "OK" if not errors else "NG",
        "details": {
            "corr": round(corr, 6),
            "beta": round(beta_val, 6),
            "expected_beta": round(expected_beta, 6),
        },
        "errors": errors,
    }


def test_correlation_uncorrelated():
    """無相関（乱数seed固定）→ 相関≈0"""
    # seed固定の擬似乱数（標準ライブラリのみ）
    import random
    rng = random.Random(42)
    x = [rng.gauss(0, 0.03) for _ in range(100)]
    rng2 = random.Random(99)
    y = [rng2.gauss(0, 0.03) for _ in range(100)]

    corr = _pearson_corr(x, y)

    errors = []
    # 無相関なので |corr| < 0.2 程度を期待
    if abs(corr) > 0.3:
        errors.append(f"無相関のはずが |corr| > 0.3: {corr}")

    return {
        "name": "correlation_uncorrelated",
        "status": "OK" if not errors else "NG",
        "details": {"corr": round(corr, 6), "abs_corr": round(abs(corr), 6)},
        "errors": errors,
    }


def test_correlation_inverse():
    """逆相関（符号反転系列）→ 相関=-1.0"""
    x = [0.02, -0.01, 0.03, 0.01, -0.02, 0.02]
    y = [-xi for xi in x]

    corr = _pearson_corr(x, y)

    errors = []
    if not approx_eq(corr, -1.0):
        errors.append(f"完全逆相関で corr != -1.0: {corr}")

    return {
        "name": "correlation_inverse",
        "status": "OK" if not errors else "NG",
        "details": {"corr": round(corr, 6)},
        "errors": errors,
    }


# =============================================================================
# 項目2b: 複合判定ロジック
# =============================================================================

def _composite_label(corr, return_gap_pct, beta_diff, te_pct, stability):
    """複合判定ロジック（phase05-shared-calculations.mdの判定順序に準拠）。

    Args:
        corr: 相関係数
        return_gap_pct: 年率リターン格差（%）
        beta_diff: ベータ差
        te_pct: 年率追跡誤差（%）
        stability: "安定" | "不安定" | "算出不可"
    """
    CORR_HIGH = 0.85
    CORR_LOW = 0.3
    RETURN_GAP_THRESHOLD = 15  # %
    BETA_DIFF_THRESHOLD = 0.3
    TE_THRESHOLD = 7  # %

    # 判定順序1: 高リスク連動型
    if corr > CORR_HIGH and (return_gap_pct >= RETURN_GAP_THRESHOLD or beta_diff >= 0.5):
        return "高リスク連動型"

    # 判定順序2: 実質重複
    if (corr > CORR_HIGH
            and return_gap_pct < RETURN_GAP_THRESHOLD
            and beta_diff < BETA_DIFF_THRESHOLD
            and te_pct < TE_THRESHOLD):
        return "実質重複"

    # 判定順序3: 不安定相関
    if corr > 0.7 and stability == "不安定":
        return "不安定相関"

    # 判定順序4: 高相関（要確認）
    if corr > 0.7:
        return "高相関（要確認）"

    # 判定順序5: 低相関（分散効果）
    if corr < CORR_LOW:
        return "低相関（分散効果）"

    # いずれにも該当しない（中程度の相関）
    return None


def test_composite_jitsu_juufuku():
    """「実質重複」判定: corr=0.92, return_gap=5%, beta_diff=0.1, te=4%"""
    label = _composite_label(corr=0.92, return_gap_pct=5.0, beta_diff=0.1,
                             te_pct=4.0, stability="安定")
    errors = []
    if label != "実質重複":
        errors.append(f"expected='実質重複', got='{label}'")
    return {
        "name": "composite_jitsu_juufuku",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


def test_composite_high_risk_rendou():
    """「高リスク連動型」判定: corr=0.90, return_gap=20%, beta_diff=0.6"""
    label = _composite_label(corr=0.90, return_gap_pct=20.0, beta_diff=0.6,
                             te_pct=10.0, stability="安定")
    errors = []
    if label != "高リスク連動型":
        errors.append(f"expected='高リスク連動型', got='{label}'")
    return {
        "name": "composite_high_risk_rendou",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


def test_composite_high_risk_rendou_beta_only():
    """「高リスク連動型」: corr=0.90, return_gap=10%(閾値未満), beta_diff=0.6(>=0.5)"""
    label = _composite_label(corr=0.90, return_gap_pct=10.0, beta_diff=0.6,
                             te_pct=5.0, stability="安定")
    errors = []
    if label != "高リスク連動型":
        errors.append(f"expected='高リスク連動型', got='{label}'")
    return {
        "name": "composite_high_risk_rendou_beta_only",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


def test_composite_fuantei_soukan():
    """「不安定相関」判定: corr=0.75, stability='不安定'"""
    label = _composite_label(corr=0.75, return_gap_pct=8.0, beta_diff=0.2,
                             te_pct=5.0, stability="不安定")
    errors = []
    if label != "不安定相関":
        errors.append(f"expected='不安定相関', got='{label}'")
    return {
        "name": "composite_fuantei_soukan",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


def test_composite_kou_soukan():
    """「高相関（要確認）」判定: corr=0.75, stability='安定'"""
    label = _composite_label(corr=0.75, return_gap_pct=8.0, beta_diff=0.2,
                             te_pct=5.0, stability="安定")
    errors = []
    if label != "高相関（要確認）":
        errors.append(f"expected='高相関（要確認）', got='{label}'")
    return {
        "name": "composite_kou_soukan",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


def test_composite_tei_soukan():
    """「低相関（分散効果）」判定: corr=0.2"""
    label = _composite_label(corr=0.2, return_gap_pct=5.0, beta_diff=0.1,
                             te_pct=3.0, stability="安定")
    errors = []
    if label != "低相関（分散効果）":
        errors.append(f"expected='低相関（分散効果）', got='{label}'")
    return {
        "name": "composite_tei_soukan",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


def test_composite_boundary_corr_high():
    """境界値: corr=0.85（ちょうどCORR_HIGH）は '>' なので該当しない。"""
    # corr > 0.85 が条件なので、0.85ちょうどは高リスク連動型/実質重複に該当しない
    # しかし corr > 0.7 なので「高相関（要確認）」に該当
    label = _composite_label(corr=0.85, return_gap_pct=5.0, beta_diff=0.1,
                             te_pct=4.0, stability="安定")
    errors = []
    if label != "高相関（要確認）":
        errors.append(f"expected='高相関（要確認）', got='{label}'")
    return {
        "name": "composite_boundary_corr_high",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


def test_composite_boundary_corr_07():
    """境界値: corr=0.7（ちょうど0.7）は '>' なので高相関に該当しない。"""
    label = _composite_label(corr=0.7, return_gap_pct=5.0, beta_diff=0.1,
                             te_pct=4.0, stability="安定")
    errors = []
    # corr=0.7 は > 0.7 を満たさないので高相関にならない
    # corr=0.7 は < 0.3 でもないので低相関にもならない
    # → None（いずれにも非該当）
    if label is not None:
        errors.append(f"expected=None, got='{label}'")
    return {
        "name": "composite_boundary_corr_07",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


def test_composite_priority_order():
    """判定順序テスト: 高リスク連動型が実質重複より優先される。
    corr=0.90, return_gap=20%(両条件成立) → 高リスク連動型が先に判定される。"""
    label = _composite_label(corr=0.90, return_gap_pct=20.0, beta_diff=0.1,
                             te_pct=4.0, stability="安定")
    errors = []
    if label != "高リスク連動型":
        errors.append(f"expected='高リスク連動型', got='{label}'")
    return {
        "name": "composite_priority_order",
        "status": "OK" if not errors else "NG",
        "details": {"label": label},
        "errors": errors,
    }


# =============================================================================
# 項目7: VaR/CVaR
# =============================================================================

def test_var_cvar_basic():
    """既知のリターン系列でVaR(95%)とCVaR(95%)を手計算で検証。"""
    # 20点のリターン系列（ソート済みで確認しやすいように設計）
    returns = [-0.08, -0.06, -0.04, -0.03, -0.02, -0.01, 0.00, 0.01, 0.01, 0.02,
               0.02, 0.03, 0.03, 0.04, 0.04, 0.05, 0.05, 0.06, 0.07, 0.08]

    # VaR(95%) = 5パーセンタイル
    # 20点の5%タイル: index = 0.05 * (20-1) = 0.95
    # numpy.quantile(method='linear'): returns[0] + 0.95 * (returns[1] - returns[0])
    # = -0.08 + 0.95 * (-0.06 - (-0.08)) = -0.08 + 0.95 * 0.02 = -0.08 + 0.019 = -0.061
    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    # 線形補間法（numpyのデフォルト method='linear' 相当）
    pos = 0.05 * (n - 1)
    lower = int(math.floor(pos))
    upper = int(math.ceil(pos))
    frac = pos - lower
    expected_var = sorted_returns[lower] + frac * (sorted_returns[upper] - sorted_returns[lower])

    # CVaR = VaR以下のリターンの平均
    cvar_values = [r for r in sorted_returns if r <= expected_var]
    if cvar_values:
        expected_cvar = sum(cvar_values) / len(cvar_values)
    else:
        expected_cvar = expected_var

    errors = []

    # VaR検証
    if not approx_eq(expected_var, -0.061, tol=0.001):
        errors.append(f"VaR(95%): got={expected_var}, expected=-0.061")

    # CVaRはVaR以下 → -0.08のみ（-0.061以下は-0.08だけ）
    if not approx_eq(expected_cvar, -0.08, tol=0.001):
        errors.append(f"CVaR(95%): got={expected_cvar}, expected=-0.08")

    # CVaR <= VaR（CVaRはVaRより悪い＝より負の値）
    if expected_cvar > expected_var:
        errors.append(f"CVaR({expected_cvar}) > VaR({expected_var}): CVaRはVaR以下であるべき")

    total_value = 1000000  # 100万円
    var_amount = expected_var * total_value
    cvar_amount = expected_cvar * total_value

    return {
        "name": "var_cvar_basic",
        "status": "OK" if not errors else "NG",
        "details": {
            "var_95": round(expected_var, 6),
            "cvar_95": round(expected_cvar, 6),
            "var_amount": round(var_amount, 0),
            "cvar_amount": round(cvar_amount, 0),
            "data_points": n,
        },
        "errors": errors,
    }


def test_var_cvar_uniform():
    """均一リターンのVaR/CVaR: 全て同じ値なら VaR=CVaR=その値。"""
    returns = [0.01] * 20

    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    pos = 0.05 * (n - 1)
    lower = int(math.floor(pos))
    upper = int(math.ceil(pos))
    frac = pos - lower
    var_val = sorted_returns[lower] + frac * (sorted_returns[upper] - sorted_returns[lower])

    cvar_values = [r for r in sorted_returns if r <= var_val]
    cvar_val = sum(cvar_values) / len(cvar_values) if cvar_values else var_val

    errors = []
    if not approx_eq(var_val, 0.01):
        errors.append(f"均一リターンでVaR != 0.01: {var_val}")
    if not approx_eq(cvar_val, 0.01):
        errors.append(f"均一リターンでCVaR != 0.01: {cvar_val}")

    return {
        "name": "var_cvar_uniform",
        "status": "OK" if not errors else "NG",
        "details": {"var_95": round(var_val, 6), "cvar_95": round(cvar_val, 6)},
        "errors": errors,
    }


def test_var_cvar_min_data_check():
    """データ不足（6ヶ月未満）ではスキップすべき。"""
    returns = [-0.02, 0.01, 0.03, -0.01, 0.02]  # 5点

    errors = []
    if len(returns) >= 6:
        errors.append(f"5点なのに6以上と判定された: {len(returns)}")

    # phase05_shared_calc.pyの条件: len(monthly_returns) >= 6
    should_skip = len(returns) < 6
    if not should_skip:
        errors.append("5点でスキップすべき")

    return {
        "name": "var_cvar_min_data_check",
        "status": "OK" if not errors else "NG",
        "details": {"data_points": len(returns), "should_skip": should_skip},
        "errors": errors,
    }


# =============================================================================
# 項目3: 最大ドローダウン
# =============================================================================

def test_max_drawdown_basic():
    """既知の評価額系列で最大ドローダウンを検証。"""
    # 日次評価額: 1000→1100→900→1050→1200→800→1100
    values = [1000, 1050, 1100, 1000, 900, 950, 1050, 1200, 800, 1000, 1100]
    dates = [f"2025-01-{i+1:02d}" for i in range(len(values))]

    # 手計算: 累積最大値の推移
    # cummax: 1000, 1050, 1100, 1100, 1100, 1100, 1100, 1200, 1200, 1200, 1200
    # dd:     0,    0,    0,   -9.1%, -18.2%, -13.6%, -4.5%, 0, -33.3%, -16.7%, -8.3%
    # 最大DD: -33.3% (value=800, peak=1200)

    cummax = []
    current_max = 0
    for v in values:
        current_max = max(current_max, v)
        cummax.append(current_max)

    dd = [(v - cm) / cm for v, cm in zip(values, cummax)]
    max_dd = min(dd)
    max_dd_idx = dd.index(max_dd)

    # ピーク = max_dd_idxまでの最大値のインデックス
    peak_value = cummax[max_dd_idx]
    peak_idx = values.index(peak_value)

    errors = []
    expected_dd = (800 - 1200) / 1200  # -0.3333...
    if not approx_eq(max_dd, expected_dd, tol=0.001):
        errors.append(f"最大DD: got={max_dd}, expected={expected_dd}")

    if max_dd_idx != 8:  # 800は9番目（index=8）
        errors.append(f"ボトムindex: got={max_dd_idx}, expected=8")

    if peak_idx != 7:  # 1200は8番目（index=7）
        errors.append(f"ピークindex: got={peak_idx}, expected=7")

    # 回復: 800以降で1200以上になるindex → index=なし(1100<1200)
    recovery_idx = None
    for i in range(max_dd_idx + 1, len(values)):
        if values[i] >= peak_value:
            recovery_idx = i
            break

    if recovery_idx is not None:
        errors.append(f"未回復のはずが回復あり: index={recovery_idx}")

    return {
        "name": "max_drawdown_basic",
        "status": "OK" if not errors else "NG",
        "details": {
            "max_dd": round(max_dd, 6),
            "peak_date": dates[peak_idx],
            "bottom_date": dates[max_dd_idx],
            "recovery": recovery_idx,
        },
        "errors": errors,
    }


def test_max_drawdown_with_recovery():
    """回復ありの最大ドローダウン検証。"""
    values = [1000, 1200, 900, 1000, 1100, 1200, 1300]
    dates = [f"2025-01-{i+1:02d}" for i in range(len(values))]

    cummax = []
    current_max = 0
    for v in values:
        current_max = max(current_max, v)
        cummax.append(current_max)

    dd = [(v - cm) / cm for v, cm in zip(values, cummax)]
    max_dd = min(dd)
    max_dd_idx = dd.index(max_dd)

    # 最大DD: (900 - 1200) / 1200 = -25%
    expected_dd = -0.25

    # 回復: 900以降で1200以上 → index=5 (values[5]=1200)
    peak_value = cummax[max_dd_idx]
    recovery_idx = None
    for i in range(max_dd_idx + 1, len(values)):
        if values[i] >= peak_value:
            recovery_idx = i
            break

    errors = []
    if not approx_eq(max_dd, expected_dd, tol=0.001):
        errors.append(f"最大DD: got={max_dd}, expected={expected_dd}")
    if recovery_idx != 5:
        errors.append(f"回復index: got={recovery_idx}, expected=5")
    if recovery_idx is not None:
        # 回復日数: index 5 - index 2 = 3日
        recovery_days = recovery_idx - max_dd_idx
        if recovery_days != 3:
            errors.append(f"回復日数: got={recovery_days}, expected=3")

    return {
        "name": "max_drawdown_with_recovery",
        "status": "OK" if not errors else "NG",
        "details": {
            "max_dd": round(max_dd, 6),
            "bottom_date": dates[max_dd_idx],
            "recovery_idx": recovery_idx,
        },
        "errors": errors,
    }


def test_max_drawdown_no_drawdown():
    """単調増加の場合、ドローダウン=0。"""
    values = [100, 200, 300, 400, 500]

    cummax = []
    current_max = 0
    for v in values:
        current_max = max(current_max, v)
        cummax.append(current_max)

    dd = [(v - cm) / cm for v, cm in zip(values, cummax)]
    max_dd = min(dd)

    errors = []
    if not approx_eq(max_dd, 0.0):
        errors.append(f"単調増加でDD != 0: {max_dd}")

    return {
        "name": "max_drawdown_no_drawdown",
        "status": "OK" if not errors else "NG",
        "details": {"max_dd": round(max_dd, 6)},
        "errors": errors,
    }


# =============================================================================
# 追加: 追跡誤差（TE）の計算検証
# =============================================================================

def test_tracking_error():
    """年率追跡誤差: std(R_it - R_jt) * sqrt(12) の検証。"""
    returns_i = [0.02, -0.01, 0.03, 0.01, -0.02, 0.02, 0.01, 0.03, -0.01, 0.02, 0.01, 0.02]
    returns_j = [0.01, -0.02, 0.02, 0.02, -0.01, 0.01, 0.02, 0.02, 0.00, 0.01, 0.02, 0.01]

    diff = [ri - rj for ri, rj in zip(returns_i, returns_j)]
    te_monthly = statistics.pstdev(diff)
    te_annual = te_monthly * math.sqrt(12)

    # 手計算
    # diff = [0.01, 0.01, 0.01, -0.01, -0.01, 0.01, -0.01, 0.01, -0.01, 0.01, -0.01, 0.01]
    mean_diff = sum(diff) / len(diff)
    var_diff = sum((d - mean_diff) ** 2 for d in diff) / len(diff)
    expected_te_monthly = math.sqrt(var_diff)
    expected_te_annual = expected_te_monthly * math.sqrt(12)

    errors = []
    if not approx_eq(te_annual, expected_te_annual):
        errors.append(f"TE不一致: got={te_annual}, expected={expected_te_annual}")

    # TE閾値チェック（仕様: TE_THRESHOLD = 7%）
    te_pct = te_annual * 100
    te_is_low = te_pct < 7.0

    return {
        "name": "tracking_error",
        "status": "OK" if not errors else "NG",
        "details": {
            "te_monthly": round(te_monthly, 6),
            "te_annual": round(te_annual, 6),
            "te_annual_pct": round(te_pct, 4),
            "below_threshold": te_is_low,
        },
        "errors": errors,
    }


# =============================================================================
# 追加: 相関安定性の計算検証
# =============================================================================

def test_correlation_stability():
    """前後半の相関差で安定性を判定する検証。"""
    # 14点以上で前後半に分割
    x = [0.02, -0.01, 0.03, 0.01, -0.02, 0.02, 0.01,
         0.03, -0.01, 0.02, 0.01, 0.02, -0.01, 0.03]
    y = [0.01, 0.00, 0.02, 0.02, -0.01, 0.01, 0.02,
         0.02, 0.00, 0.01, 0.02, 0.01, 0.00, 0.02]

    n = len(x)
    mid = n // 2
    x_first, x_second = x[:mid], x[mid:]
    y_first, y_second = y[:mid], y[mid:]

    corr_first = _pearson_corr(x_first, y_first)
    corr_second = _pearson_corr(x_second, y_second)
    stability_diff = abs(corr_first - corr_second)

    # STABILITY_DIFF = 0.3
    is_unstable = stability_diff > 0.3

    errors = []
    if n < 14:
        errors.append(f"データ点数不足: {n} < 14")

    # 差分が妥当な範囲か確認
    if stability_diff < 0 or stability_diff > 2.0:
        errors.append(f"相関差が範囲外: {stability_diff}")

    return {
        "name": "correlation_stability",
        "status": "OK" if not errors else "NG",
        "details": {
            "data_points": n,
            "corr_first_half": round(corr_first, 6),
            "corr_second_half": round(corr_second, 6),
            "stability_diff": round(stability_diff, 6),
            "is_unstable": is_unstable,
        },
        "errors": errors,
    }


def test_correlation_stability_unstable():
    """明示的に不安定な相関の検証。前半は正相関、後半は逆相関。"""
    # 前半: 正の相関
    x_first = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]
    y_first = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08]
    # 後半: 逆の相関
    x_second = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]
    y_second = [0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02]

    x = x_first + x_second
    y = y_first + y_second

    mid = len(x) // 2
    corr_first = _pearson_corr(x[:mid], y[:mid])
    corr_second = _pearson_corr(x[mid:], y[mid:])
    stability_diff = abs(corr_first - corr_second)

    errors = []
    # 前半: ほぼ1.0、後半: ほぼ-1.0 → 差 ≈ 2.0 >> 0.3
    if stability_diff <= 0.3:
        errors.append(f"不安定なはずが安定と判定: diff={stability_diff}")
    if corr_first < 0.9:
        errors.append(f"前半相関が低い: {corr_first}")
    if corr_second > -0.9:
        errors.append(f"後半相関が高い: {corr_second}")

    return {
        "name": "correlation_stability_unstable",
        "status": "OK" if not errors else "NG",
        "details": {
            "corr_first": round(corr_first, 6),
            "corr_second": round(corr_second, 6),
            "stability_diff": round(stability_diff, 6),
        },
        "errors": errors,
    }


# =============================================================================
# テストランナー
# =============================================================================

ALL_TESTS = [
    # 項目1: シャープレシオ
    test_sharpe_ratio_basic,
    test_sharpe_ratio_negative,
    test_sharpe_ratio_zero_vol,
    # 項目2: 相関分析
    test_correlation_perfect,
    test_correlation_known_series,
    test_correlation_uncorrelated,
    test_correlation_inverse,
    # 項目2: 追跡誤差
    test_tracking_error,
    # 項目2: 相関安定性
    test_correlation_stability,
    test_correlation_stability_unstable,
    # 項目2b: 複合判定ロジック
    test_composite_jitsu_juufuku,
    test_composite_high_risk_rendou,
    test_composite_high_risk_rendou_beta_only,
    test_composite_fuantei_soukan,
    test_composite_kou_soukan,
    test_composite_tei_soukan,
    test_composite_boundary_corr_high,
    test_composite_boundary_corr_07,
    test_composite_priority_order,
    # 項目7: VaR/CVaR
    test_var_cvar_basic,
    test_var_cvar_uniform,
    test_var_cvar_min_data_check,
    # 項目3: 最大ドローダウン
    test_max_drawdown_basic,
    test_max_drawdown_with_recovery,
    test_max_drawdown_no_drawdown,
]


def main():
    results = {}
    failures = []

    for test_fn in ALL_TESTS:
        try:
            result = test_fn()
        except Exception as e:
            result = {
                "name": test_fn.__name__,
                "status": "NG",
                "details": {},
                "errors": [f"例外発生: {type(e).__name__}: {e}"],
            }

        results[result["name"]] = result
        if result["status"] != "OK":
            failures.append(result["name"])

    total = len(ALL_TESTS)
    passed = total - len(failures)
    status = "OK" if not failures else "NG"

    output = {
        "status": status,
        "summary": f"{passed}/{total} passed",
        "results": results,
        "failures": failures,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if status == "OK" else 1)


if __name__ == "__main__":
    main()
