#!/usr/bin/env python3
"""Phase 0.5: 共通定量計算スクリプト

Phase 0で収集した portfolio_data.json を入力として、
決定論的な数値計算（シャープレシオ、相関係数、最大ドローダウン、VaR/CVaR等）を実行し、
_calc_temp.json に出力する。

Usage:
    docker compose exec backend python scripts/phase05_shared_calc.py <work_dir>

    例: docker compose exec backend python scripts/phase05_shared_calc.py .tmp/pf_20260308_143000_abcd

入力: <work_dir>/00_portfolio_data.json
出力: <work_dir>/_calc_temp.json
"""
import json
import math
import os
import re
import sys
from pathlib import Path

# プロジェクトルートを特定（backend/scripts/ → backend/ → project root）
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
# Docker環境では /app/scripts/ 構造のため、BACKEND_DIR.parent が / になる
# APP_BASE_DIR環境変数 or ディレクトリ構造で判定
_candidate = BACKEND_DIR.parent
if os.environ.get("APP_BASE_DIR"):
    PROJECT_ROOT = Path(os.environ["APP_BASE_DIR"])
elif (_candidate / "backend" / "src").exists():
    # 本番/ローカル: backend/scripts/ → backend/ → project root
    PROJECT_ROOT = _candidate
else:
    # Docker: /app/scripts/ → BACKEND_DIR=/app がプロジェクトルート
    PROJECT_ROOT = BACKEND_DIR

# 環境変数設定（本番環境用）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))


def load_params() -> dict:
    """calc_params.json から閾値パラメータを読み込む"""
    params_path = PROJECT_ROOT / ".claude" / "skills" / "portfolio-analysis" / "calc_params.json"
    with open(params_path) as f:
        return json.load(f)


def _normalize_data(data: dict) -> dict:
    """フラットリスト形式のデータをdict形式に正規化する。

    Phase 0の出力形式（フラットリスト）とスクリプトが期待する形式（dict keyed by ticker）を変換。
    """
    # performance_cache: list -> dict[ticker, list[period_data]]
    perf = data.get("performance_cache")
    if isinstance(perf, list):
        perf_dict = {}
        for item in perf:
            ticker = str(item.get("etf_code", ""))
            if ticker not in perf_dict:
                perf_dict[ticker] = []
            perf_dict[ticker].append(item)
        data["performance_cache"] = perf_dict

    # price_data: list -> dict[ticker, list[{date, close}]]
    pd_ = data.get("price_data")
    if isinstance(pd_, list):
        pd_dict = {}
        for item in pd_:
            ticker = str(item.get("etf_code", ""))
            if ticker not in pd_dict:
                pd_dict[ticker] = []
            pd_dict[ticker].append({"date": item.get("date"), "close": item.get("close")})
        data["price_data"] = pd_dict

    # score_cache: list -> list (holdingsのticker_codeをetf_codeから変換)
    sc = data.get("score_cache")
    if isinstance(sc, list):
        for item in sc:
            if "etf_code" in item and "ticker_code" not in item:
                item["ticker_code"] = item["etf_code"]

    # etf_data: list -> dict[ticker, info]
    ed = data.get("etf_data")
    if isinstance(ed, list):
        ed_dict = {}
        for item in ed:
            ticker = str(item.get("code", ""))
            ed_dict[ticker] = item
        data["etf_data"] = ed_dict

    # tag_data: list -> dict[ticker, list[{category, tag_name}]]
    td = data.get("tag_data")
    if isinstance(td, list):
        td_dict = {}
        for item in td:
            ticker = str(item.get("etf_code", ""))
            if ticker not in td_dict:
                td_dict[ticker] = []
            td_dict[ticker].append({"category": item.get("category", ""), "tag_name": item.get("name", "")})
        data["tag_data"] = td_dict

    # holdings: ticker_code フィールドを etf_code から設定
    holdings_data = data.get("holdings", {}).get("data", [])
    for h in holdings_data:
        if "etf_code" in h and "ticker_code" not in h:
            h["ticker_code"] = h["etf_code"]

    return data


def load_portfolio_data(work_dir: str) -> dict:
    """00_portfolio_data.json を読み込む"""
    data_path = PROJECT_ROOT / work_dir / "00_portfolio_data.json"
    with open(data_path) as f:
        data = json.load(f)
    return _normalize_data(data)


def get_holdings_weights(data: dict) -> tuple:
    """保有銘柄リストと総評価額を取得"""
    holdings = data.get("holdings", {}).get("data", [])
    total_value = sum(h.get("current_value", 0) for h in holdings)
    return holdings, total_value


def calc_sharpe_ratios(data: dict, params: dict, rf_rate=None) -> dict:
    """項目1: シャープレシオ計算

    performance_cacheから1年リターン・ボラティリティを取得し計算。
    rf_rate が None の場合、calc_params.json のフォールバック値を使用。
    """
    rf = rf_rate if rf_rate is not None else params["sharpe_ratio"]["risk_free_rate_fallback"] / 100
    perf_cache = data.get("performance_cache", {})
    results = []

    for ticker, periods in perf_cache.items():
        # 1年データを探す
        one_year = None
        period_list = periods if isinstance(periods, list) else [periods]
        for p in period_list:
            if isinstance(p, dict) and p.get("period") == "1y":
                one_year = p
                break

        if one_year and one_year.get("volatility") and one_year["volatility"] > 0 and one_year.get("return_rate") is not None:
            ret = one_year["return_rate"] / 100  # %->小数
            vol = one_year["volatility"] / 100
            sr = (ret - rf) / vol
            results.append({
                "ticker": ticker,
                "return_1y": one_year.get("return_rate", 0),
                "volatility_1y": one_year.get("volatility", 0),
                "sharpe_ratio": round(sr, 4),
                "risk_free_rate_used": round(rf * 100, 2)
            })

    # ランキング（降順）
    results.sort(key=lambda x: x["sharpe_ratio"], reverse=True)

    # ポートフォリオ加重シャープレシオ
    holdings, total_value = get_holdings_weights(data)

    weighted_sr = 0
    if total_value > 0:
        for r in results:
            holding = next(
                (h for h in holdings if str(h.get("ticker_code", "")) == str(r["ticker"])),
                None
            )
            if holding:
                weight = holding.get("current_value", 0) / total_value
                weighted_sr += r["sharpe_ratio"] * weight

    return {
        "individual": results,
        "portfolio_weighted": round(weighted_sr, 4),
        "risk_free_rate_used": round(rf * 100, 2),
        "risk_free_rate_source": "market_environment" if rf_rate is not None else "fallback"
    }


def extract_monthly_returns(price_data: dict) -> dict:
    """price_dataから月次リターンを計算する共通関数"""
    monthly_returns = {}
    for ticker, prices in price_data.items():
        if not isinstance(prices, list) or len(prices) < 2:
            continue

        # 月初価格を抽出
        monthly_prices = {}
        for p in prices:
            date_str = p.get("date", "")
            if not date_str:
                continue
            month_key = date_str[:7]  # YYYY-MM
            if month_key not in monthly_prices:
                monthly_prices[month_key] = p.get("close", 0)

        # 月次リターンを計算
        sorted_months = sorted(monthly_prices.keys())
        returns = []
        for i in range(1, len(sorted_months)):
            prev_price = monthly_prices[sorted_months[i - 1]]
            curr_price = monthly_prices[sorted_months[i]]
            if prev_price > 0:
                ret = (curr_price - prev_price) / prev_price
                returns.append(ret)

        if returns:
            monthly_returns[ticker] = returns

    return monthly_returns


def _pearson_correlation(x, y):
    """ピアソン相関係数を計算"""
    n = len(x)
    if n < 3:
        return None

    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(a * b for a, b in zip(x, y))
    sum_x_sq = sum(a * a for a in x)
    sum_y_sq = sum(b * b for b in y)

    numerator = n * sum_xy - sum_x * sum_y
    denominator = math.sqrt(
        max(0, (n * sum_x_sq - sum_x ** 2)) *
        max(0, (n * sum_y_sq - sum_y ** 2))
    )

    if denominator == 0:
        return None

    return numerator / denominator


def _classify_pair(
    corr, return_gap, return_gap_threshold,
    beta_diff, beta_diff_threshold, beta_high_risk,
    te, te_threshold,
    stability_label, corr_high, corr_low
):
    """複合判定ロジック（判定順序に従う）"""
    if corr > corr_high:
        # 高リスク連動型
        if return_gap is not None and return_gap >= return_gap_threshold:
            return "高リスク連動型"
        if beta_diff is not None and beta_diff >= beta_high_risk:
            return "高リスク連動型"
        # 実質重複
        rg_ok = return_gap is not None and return_gap < return_gap_threshold
        bd_ok = beta_diff is None or beta_diff < beta_diff_threshold
        te_ok = te is None or te < te_threshold
        if rg_ok and bd_ok and te_ok:
            return "実質重複"

    if corr > 0.7:
        if stability_label == "不安定":
            return "不安定相関"
        return "高相関（要確認）"

    if corr < corr_low:
        return "低相関（分散効果）"

    return "通常"


def _calc_pair_metrics(
    ticker_a, ticker_b, returns_a, returns_b, one_year_returns, params
):
    """ペア間の相関指標を計算して辞書を返す。算出不可ならNone。"""
    min_len = min(len(returns_a), len(returns_b))
    r1 = returns_a[:min_len]
    r2 = returns_b[:min_len]

    min_months_basic = params["min_months"]["basic"]
    min_months_full = params["min_months"]["full"]
    stability_diff_threshold = params["stability_diff"]["threshold"]

    # ピアソン相関係数
    corr = _pearson_correlation(r1, r2)
    if corr is None:
        return None

    # リターン格差（年率）
    ret_a = one_year_returns.get(ticker_a)
    ret_b = one_year_returns.get(ticker_b)
    return_gap = abs(ret_a - ret_b) if ret_a is not None and ret_b is not None else None

    # 年率追跡誤差
    te = None
    if min_len >= min_months_basic:
        diffs = [a - b for a, b in zip(r1, r2)]
        if len(diffs) >= 2:
            mean_diff = sum(diffs) / len(diffs)
            var_diff = sum((d - mean_diff) ** 2 for d in diffs) / (len(diffs) - 1)
            te = math.sqrt(var_diff) * math.sqrt(12)  # 年率換算

    # 相関安定性
    stability_label = "算出不可"
    if min_len >= min_months_full:
        half = min_len // 2
        corr_first = _pearson_correlation(r1[:half], r2[:half])
        corr_second = _pearson_correlation(r1[half:], r2[half:])
        if corr_first is not None and corr_second is not None:
            stability = abs(corr_first - corr_second)
            stability_label = "不安定" if stability > stability_diff_threshold else "安定"

    # 複合判定
    classification = _classify_pair(
        corr, return_gap, params["return_gap"]["threshold"],
        None,  # beta_diff: 市場代理ETFが必要（サブエージェントが補完）
        params["beta_diff"]["threshold"], params["beta_diff"]["high_risk_threshold"],
        te, params["tracking_error"]["threshold"],
        stability_label, params["correlation"]["high"], params["correlation"]["low"]
    )

    return {
        "ticker_1": ticker_a,
        "ticker_2": ticker_b,
        "correlation": round(corr, 4),
        "return_gap": round(return_gap, 4) if return_gap is not None else None,
        "tracking_error": round(te, 4) if te is not None else None,
        "stability": stability_label,
        "classification": classification,
        "data_points": min_len
    }


def calc_correlation_matrix(data: dict, params: dict) -> dict:
    """項目2: 相関分析

    月次価格データから月次リターンを計算し、相関係数を算出。
    複合判定ロジック含む。
    """
    price_data = data.get("price_data", {})
    if not price_data or len(price_data) < 2:
        return {"status": "skipped", "reason": "2銘柄未満のためスキップ"}

    monthly_returns = extract_monthly_returns(price_data)

    tickers = list(monthly_returns.keys())
    if len(tickers) < 2:
        return {"status": "skipped", "reason": "有効な月次リターンが2銘柄未満"}

    # 閾値取得（ループ内フィルタ用）
    min_months_basic = params["min_months"]["basic"]

    # performance_cacheから1年リターン取得
    perf_cache = data.get("performance_cache", {})
    one_year_returns = {}
    for ticker, periods in perf_cache.items():
        period_list = periods if isinstance(periods, list) else [periods]
        for p in period_list:
            if isinstance(p, dict) and p.get("period") == "1y":
                rr = p.get("return_rate")
                if rr is not None:
                    one_year_returns[ticker] = rr / 100
                break

    pairs = []
    data_months = 0

    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            r1 = monthly_returns[tickers[i]]
            r2 = monthly_returns[tickers[j]]
            min_len = min(len(r1), len(r2))
            if min_len < min_months_basic:
                continue
            data_months = max(data_months, min_len)

            pair_data = _calc_pair_metrics(
                tickers[i], tickers[j], r1, r2, one_year_returns, params
            )
            if pair_data is not None:
                pairs.append(pair_data)

    pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return {"status": "ok", "pairs": pairs, "data_months": data_months}


def calc_max_drawdown(data: dict) -> dict:
    """項目3: 最大ドローダウン＆回復期間"""
    valuation = data.get("valuation_history", {}).get("data", [])
    if not valuation or len(valuation) < 10:
        return {
            "status": "skipped",
            "reason": "データポイント不足（{}点、最低10点必要）".format(
                len(valuation) if valuation else 0
            )
        }

    # valuation_historyは "value" または "total_value" フィールドを使用
    def _get_val(point):
        return point.get("total_value", point.get("value", 0))

    peak = _get_val(valuation[0])
    max_dd = 0
    peak_date = valuation[0].get("date", "")
    dd_peak_date = peak_date
    dd_peak_value = peak
    trough_date = ""
    trough_value = peak

    for point in valuation:
        val = _get_val(point)
        if val > peak:
            peak = val
            peak_date = point.get("date", "")
        dd = (val - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd
            trough_date = point.get("date", "")
            trough_value = val
            dd_peak_date = peak_date
            dd_peak_value = peak

    # 回復日の特定
    recovery_date = None
    if trough_date:
        found_trough = False
        for point in valuation:
            if point.get("date", "") == trough_date:
                found_trough = True
                continue
            if found_trough and _get_val(point) >= dd_peak_value:
                recovery_date = point.get("date", "")
                break

    return {
        "status": "ok",
        "max_drawdown_pct": round(max_dd * 100, 2),
        "peak_date": dd_peak_date,
        "peak_value": dd_peak_value,
        "trough_date": trough_date,
        "trough_value": trough_value,
        "recovery_date": recovery_date
    }


def calc_weighted_scores(data: dict) -> dict:
    """項目5: 加重平均スコア表"""
    score_cache = data.get("score_cache", [])
    holdings, total_value = get_holdings_weights(data)

    if not score_cache or total_value == 0:
        return {"status": "skipped", "reason": "スコアデータまたは保有データなし"}

    # 銘柄ごとの5軸スコアを取得（視点によらず同一値）
    ticker_axes = {}
    ticker_perspectives = {}
    axes = [
        "dividend_power", "cost_efficiency", "scale_reliability",
        "trading_quality", "return_performance"
    ]

    for record in score_cache:
        ticker = str(record.get("ticker_code", ""))
        perspective = record.get("perspective", "")

        # 5軸スコア（最初に見つかったものを使用）
        if ticker not in ticker_axes:
            axis_scores = {}
            for ax in axes:
                val = record.get(ax)
                if val is not None:
                    axis_scores[ax] = val
            if len(axis_scores) == 5:
                ticker_axes[ticker] = axis_scores

        # 視点別総合スコア
        if ticker not in ticker_perspectives:
            ticker_perspectives[ticker] = {}
        total_score = record.get("total_score")
        if total_score is not None and perspective:
            ticker_perspectives[ticker][perspective] = total_score

    # 5軸加重平均
    weighted_axes = {ax: 0.0 for ax in axes}
    for holding in holdings:
        ticker = str(holding.get("ticker_code", ""))
        weight = holding.get("current_value", 0) / total_value
        if ticker in ticker_axes:
            for ax in axes:
                weighted_axes[ax] += ticker_axes[ticker].get(ax, 0) * weight

    weighted_axes = {k: round(v, 2) for k, v in weighted_axes.items()}

    # 最強軸・最弱軸
    max_axis = max(weighted_axes, key=weighted_axes.get)
    min_axis = min(weighted_axes, key=weighted_axes.get)

    # 視点別総合スコア加重平均
    all_perspectives = set()
    for p_dict in ticker_perspectives.values():
        all_perspectives.update(p_dict.keys())

    weighted_perspectives = {}
    for perspective in sorted(all_perspectives):
        total = 0.0
        for holding in holdings:
            ticker = str(holding.get("ticker_code", ""))
            weight = holding.get("current_value", 0) / total_value
            if ticker in ticker_perspectives and perspective in ticker_perspectives[ticker]:
                total += ticker_perspectives[ticker][perspective] * weight
        weighted_perspectives[perspective] = round(total, 2)

    return {
        "status": "ok",
        "axes_weighted": weighted_axes,
        "max_axis": max_axis,
        "min_axis": min_axis,
        "axis_gap": round(weighted_axes[max_axis] - weighted_axes[min_axis], 2),
        "perspectives_weighted": weighted_perspectives
    }


def calc_momentum_distribution(data: dict) -> dict:
    """項目6: モメンタム分布"""
    etf_data = data.get("etf_data", {})
    holdings, total_value = get_holdings_weights(data)

    if not etf_data:
        return {"status": "skipped", "reason": "ETFデータなし"}

    distribution = {}
    declining_tickers = []

    for holding in holdings:
        ticker = str(holding.get("ticker_code", ""))
        weight = holding.get("current_value", 0) / total_value if total_value > 0 else 0
        etf_info = etf_data.get(ticker, {})
        label = etf_info.get("momentum_label", "不明")

        if label not in distribution:
            distribution[label] = {"count": 0, "weight": 0.0, "tickers": []}
        distribution[label]["count"] += 1
        distribution[label]["weight"] += weight
        distribution[label]["tickers"].append(ticker)

        if label in ("下降中", "下降加速"):
            declining_tickers.append({
                "ticker": ticker,
                "label": label,
                "weight": round(weight * 100, 2)
            })

    # 比率を丸める
    for label in distribution:
        distribution[label]["weight"] = round(distribution[label]["weight"] * 100, 2)

    declining_ratio = sum(d["weight"] for d in declining_tickers) / 100

    return {
        "status": "ok",
        "distribution": distribution,
        "declining_tickers": declining_tickers,
        "declining_ratio": round(declining_ratio, 4)
    }


def calc_var_cvar(data: dict, params: dict) -> dict:
    """項目7: VaR/CVaR（ヒストリカル法）"""
    price_data = data.get("price_data", {})
    holdings, total_value = get_holdings_weights(data)
    summary = data.get("summary", {}).get("data", {})
    total_asset = summary.get("total_asset", total_value)

    if not price_data or not holdings:
        return {"status": "skipped", "reason": "データ不足"}

    min_points = params["var_cvar"]["min_data_points"]
    confidence = params["var_cvar"]["confidence_level"]
    reliable_points = params["var_cvar"]["reliable_data_points"]

    monthly_returns = extract_monthly_returns(price_data)

    if not monthly_returns:
        return {"status": "skipped", "reason": "月次リターン計算不可"}

    if total_value == 0:
        return {"status": "skipped", "reason": "総資産0"}

    min_len = min(len(v) for v in monthly_returns.values())
    if min_len < min_points:
        return {
            "status": "skipped",
            "reason": "データポイント不足（{}点、最低{}点必要）".format(min_len, min_points)
        }

    # ポートフォリオ月次リターン（加重平均）
    portfolio_returns = [0.0] * min_len
    for ticker, returns in monthly_returns.items():
        holding = next(
            (h for h in holdings if str(h.get("ticker_code", "")) == str(ticker)),
            None
        )
        weight = (holding.get("current_value", 0) / total_value) if holding else 0
        for i in range(min_len):
            portfolio_returns[i] += returns[i] * weight

    # VaR(95%) = 下位5%タイル
    sorted_returns = sorted(portfolio_returns)
    var_index = int(len(sorted_returns) * (1 - confidence))
    var_index = min(var_index, len(sorted_returns) - 1)  # 範囲外アクセス防止
    var_95 = sorted_returns[var_index]

    # CVaR = VaR以下の平均
    cvar_returns = [r for r in sorted_returns if r <= var_95]
    cvar_95 = sum(cvar_returns) / len(cvar_returns) if cvar_returns else var_95

    # 信頼度判定
    if min_len >= reliable_points:
        reliability = "高"
    elif min_len >= 24:
        reliability = "中"
    elif min_len >= 12:
        reliability = "中"
    else:
        reliability = "参考値"

    return {
        "status": "ok",
        "var_95_pct": round(var_95 * 100, 2),
        "cvar_95_pct": round(cvar_95 * 100, 2),
        "var_95_amount": round(total_asset * var_95),
        "cvar_95_amount": round(total_asset * cvar_95),
        "data_points": min_len,
        "confidence_level": confidence,
        "reliability": reliability
    }


def calc_expense_ratio_effect(data: dict) -> dict:
    """analyst-E向け: 信託報酬の長期複利効果テーブル"""
    etf_data = data.get("etf_data", {})
    holdings, _ = get_holdings_weights(data)

    if not etf_data or not holdings:
        return {"status": "skipped", "reason": "データ不足"}

    # 各銘柄の信託報酬を取得
    expense_data = []
    for holding in holdings:
        ticker = str(holding.get("ticker_code", ""))
        etf_info = etf_data.get(ticker, {})
        expense_ratio = etf_info.get("expense_ratio")
        if expense_ratio is not None:
            expense_data.append({
                "ticker": ticker,
                "name": etf_info.get("name", ""),
                "expense_ratio": expense_ratio
            })

    if not expense_data:
        return {"status": "skipped", "reason": "信託報酬データなし"}

    # 最低コスト銘柄を基準
    min_cost = min(expense_data, key=lambda x: x["expense_ratio"])
    min_expense = min_cost["expense_ratio"]

    results = []
    for item in expense_data:
        diff = item["expense_ratio"] - min_expense
        effect_5y = round(((1 - diff / 100) ** 5 - 1) * 100, 3)
        effect_10y = round(((1 - diff / 100) ** 10 - 1) * 100, 3)
        effect_20y = round(((1 - diff / 100) ** 20 - 1) * 100, 3)
        results.append({
            "ticker": item["ticker"],
            "name": item["name"],
            "expense_ratio": item["expense_ratio"],
            "diff_from_min": round(diff, 4),
            "effect_5y_pct": effect_5y,
            "effect_10y_pct": effect_10y,
            "effect_20y_pct": effect_20y
        })

    return {
        "status": "ok",
        "min_cost_ticker": min_cost["ticker"],
        "min_expense_ratio": min_expense,
        "effects": results
    }


def calc_hhi(data: dict) -> dict:
    """項目H: HHI集中度指数（銘柄別・セクター別・地域別）"""
    holdings, total_value = get_holdings_weights(data)
    if not holdings or total_value == 0:
        return {"status": "skipped", "reason": "保有データなし"}

    # 銘柄別HHI
    weights = [h.get("current_value", 0) / total_value for h in holdings]
    hhi_holdings = sum(w ** 2 for w in weights)

    # セクター別・地域別HHI（tag_dataから）
    tag_data = data.get("tag_data", {})

    def calc_category_hhi(category_key):
        """タグカテゴリ別のHHI算出"""
        category_weights = {}
        for holding in holdings:
            ticker = str(holding.get("ticker_code", ""))
            weight = holding.get("current_value", 0) / total_value
            tags = tag_data.get(ticker, [])
            if isinstance(tags, list):
                matched = [t for t in tags if isinstance(t, dict) and t.get("category") == category_key]
                if matched:
                    # 複数タグがある場合は均等配分
                    per_tag_weight = weight / len(matched)
                    for t in matched:
                        tag_name = t.get("tag_name", "不明")
                        category_weights[tag_name] = category_weights.get(tag_name, 0) + per_tag_weight
                else:
                    category_weights["未分類"] = category_weights.get("未分類", 0) + weight
            else:
                category_weights["未分類"] = category_weights.get("未分類", 0) + weight

        if not category_weights:
            return None, {}
        hhi = sum(v ** 2 for v in category_weights.values())
        return round(hhi, 4), {k: round(v, 4) for k, v in sorted(category_weights.items(), key=lambda x: -x[1])}

    hhi_sector, sector_weights = calc_category_hhi("sector")
    hhi_region, region_weights = calc_category_hhi("region")

    return {
        "status": "ok",
        "hhi_holdings": round(hhi_holdings, 4),
        "hhi_sector": hhi_sector,
        "hhi_region": hhi_region,
        "sector_weights": sector_weights,
        "region_weights": region_weights,
        "effective_n_holdings": round(1 / hhi_holdings, 1) if hhi_holdings > 0 else None
    }


def calc_cornish_fisher_var(data: dict, params: dict) -> dict:
    """項目CF: Cornish-Fisher VaR補正（歪度・尖度考慮）"""
    price_data = data.get("price_data", {})
    holdings, total_value = get_holdings_weights(data)
    summary = data.get("summary", {}).get("data", {})
    total_asset = summary.get("total_asset", total_value)

    if not price_data or not holdings or total_value == 0:
        return {"status": "skipped", "reason": "データ不足"}

    min_points = params["var_cvar"]["min_data_points"]
    monthly_returns = extract_monthly_returns(price_data)
    if not monthly_returns:
        return {"status": "skipped", "reason": "月次リターン計算不可"}

    min_len = min(len(v) for v in monthly_returns.values())
    if min_len < min_points:
        return {"status": "skipped", "reason": f"データポイント不足（{min_len}点、最低{min_points}点必要）"}

    # ポートフォリオ月次リターン
    portfolio_returns = [0.0] * min_len
    for ticker, returns in monthly_returns.items():
        holding = next(
            (h for h in holdings if str(h.get("ticker_code", "")) == str(ticker)),
            None
        )
        weight = (holding.get("current_value", 0) / total_value) if holding else 0
        for i in range(min_len):
            portfolio_returns[i] += returns[i] * weight

    n = len(portfolio_returns)
    mean = sum(portfolio_returns) / n
    variance = sum((r - mean) ** 2 for r in portfolio_returns) / (n - 1)
    std = math.sqrt(variance) if variance > 0 else 0

    if std == 0:
        return {"status": "skipped", "reason": "ボラティリティ0"}

    # 歪度・尖度
    skewness = sum((r - mean) ** 3 for r in portfolio_returns) / (n * std ** 3) if std > 0 else 0
    kurtosis_excess = sum((r - mean) ** 4 for r in portfolio_returns) / (n * std ** 4) - 3 if std > 0 else 0

    # Cornish-Fisher展開
    z = 1.6449  # 95%信頼水準
    z_cf = (z
            + (z**2 - 1) * skewness / 6
            + (z**3 - 3*z) * kurtosis_excess / 24
            - (2*z**3 - 5*z) * skewness**2 / 36)

    # VaR計算
    cf_var = mean - z_cf * std
    parametric_var = mean - z * std

    # 補正インパクト
    correction_pct = ((cf_var - parametric_var) / abs(parametric_var) * 100) if parametric_var != 0 else 0

    return {
        "status": "ok",
        "skewness": round(skewness, 4),
        "kurtosis_excess": round(kurtosis_excess, 4),
        "z_normal": round(z, 4),
        "z_cornish_fisher": round(z_cf, 4),
        "parametric_var_pct": round(parametric_var * 100, 2),
        "cornish_fisher_var_pct": round(cf_var * 100, 2),
        "cf_var_amount": round(total_asset * cf_var),
        "correction_impact_pct": round(correction_pct, 2),
        "data_points": n,
        "interpretation": "テール肥大（正規分布仮定は不適切）" if abs(correction_pct) > 20 else "概ね正規分布に適合"
    }


def try_load_rf_rate(work_dir: str):
    """0a_market_environment.md からリスクフリーレートを読み込む（存在しない場合None）"""
    market_file = PROJECT_ROOT / work_dir / "0a_market_environment.md"
    if not market_file.exists():
        return None
    try:
        content = market_file.read_text()
        # リスクフリーレートセクションから利回りを取得
        match = re.search(r'リスクフリーレート.*?(\d+\.?\d*)%', content, re.DOTALL)
        if match:
            return float(match.group(1)) / 100
        # フォールバック: 日本国債10年利回りを直接検索
        match = re.search(r'日本国債10年利回り.*?(\d+\.?\d*)%', content, re.DOTALL)
        if match:
            return float(match.group(1)) / 100
    except Exception:
        pass
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python phase05_shared_calc.py <work_dir>")
        print("Example: python phase05_shared_calc.py .tmp/pf_20260308_143000_abcd")
        sys.exit(1)

    work_dir = sys.argv[1]

    # パストラバーサル防止
    resolved_work_dir = (PROJECT_ROOT / work_dir).resolve()
    if not str(resolved_work_dir).startswith(str(PROJECT_ROOT.resolve())):
        print(f"エラー: 無効な作業ディレクトリ: {work_dir}", file=sys.stderr)
        sys.exit(1)

    params = load_params()
    data = load_portfolio_data(work_dir)

    # リスクフリーレート取得
    rf_rate = try_load_rf_rate(work_dir)

    # 計算実行
    results = {
        "sharpe_ratios": calc_sharpe_ratios(data, params, rf_rate),
        "correlation": calc_correlation_matrix(data, params),
        "max_drawdown": calc_max_drawdown(data),
        "weighted_scores": calc_weighted_scores(data),
        "momentum_distribution": calc_momentum_distribution(data),
        "var_cvar": calc_var_cvar(data, params),
        "expense_ratio_effect": calc_expense_ratio_effect(data),
        "hhi": calc_hhi(data),
        "cornish_fisher_var": calc_cornish_fisher_var(data, params),
        "params_used": {
            "correlation_high": params["correlation"]["high"],
            "correlation_low": params["correlation"]["low"],
            "sharpe_excellent": params["sharpe_ratio"]["excellent"],
            "sharpe_good": params["sharpe_ratio"]["good"],
            "return_gap_threshold": params["return_gap"]["threshold"],
            "beta_diff_threshold": params["beta_diff"]["threshold"],
            "tracking_error_threshold": params["tracking_error"]["threshold"],
            "min_months_basic": params["min_months"]["basic"],
            "min_months_full": params["min_months"]["full"]
        }
    }

    # 出力
    output_path = PROJECT_ROOT / work_dir / "_calc_temp.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("計算完了: {}".format(output_path))
    print("  シャープレシオ: {}銘柄".format(len(results['sharpe_ratios'].get('individual', []))))
    print("  相関分析: {}".format(results['correlation'].get('status', 'N/A')))
    print("  最大DD: {}".format(results['max_drawdown'].get('status', 'N/A')))
    print("  加重平均スコア: {}".format(results['weighted_scores'].get('status', 'N/A')))
    print("  モメンタム分布: {}".format(results['momentum_distribution'].get('status', 'N/A')))
    print("  VaR/CVaR: {}".format(results['var_cvar'].get('status', 'N/A')))
    print("  信託報酬複利効果: {}".format(results['expense_ratio_effect'].get('status', 'N/A')))
    print("  HHI集中度: {}".format(results['hhi'].get('status', 'N/A')))
    print("  Cornish-Fisher VaR: {}".format(results['cornish_fisher_var'].get('status', 'N/A')))


if __name__ == "__main__":
    main()
