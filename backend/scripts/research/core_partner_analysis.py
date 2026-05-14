"""1547 (S&P500 ETF) のコア・パートナー候補分析（使い捨て調査用）.

testユーザーA群（コア・逆相関）3スロット見直しのため、1547と相関の低い・
リターン指標の高いパートナー候補をDB既存データのみで抽出する。
"""

import json
import math
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルート特定
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 環境変数（本番互換）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))

sys.path.insert(0, str(BACKEND_DIR / "scripts"))
# Docker環境用に /app/scripts も追加
sys.path.insert(0, "/app/scripts")

# 既存ロジック流用
from phase05_shared_calc import (  # noqa: E402
    _pearson_correlation,
    extract_monthly_returns,  # noqa: F401  # 参考用
)

# DBパス（コンテナ内）
DB_PATH = "/app/data/etf.db"

# 既存指定候補プール（戦略書のA群/B群＋類似銘柄）
PINNED_CODES = [
    "1547",  # ベンチマーク
    "2559", "200A", "1540", "1542", "2621", "1487", "1482",
    "1357", "1571", "1671", "1545", "2513",
    "1306", "1615", "1629", "2646", "1618",
]

# 出力先（Docker環境では /app/reports/ がホスト側 reports/ にマップされている）
TODAY = datetime.now().strftime("%Y%m%d")
if Path("/app/reports").exists():
    REPORT_DIR = Path("/app/reports") / "research"
else:
    REPORT_DIR = PROJECT_ROOT / "reports" / "research"
REPORT_MD = REPORT_DIR / f"core_partner_analysis_{TODAY}.md"
REPORT_JSON = REPORT_DIR / f"core_partner_analysis_{TODAY}.json"


def get_conn():
    return sqlite3.connect(DB_PATH)


def fetch_top_10y_returns(conn, limit=30):
    """performance_cacheから10y_return上位30銘柄を取得."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pc.etf_code, pc.return_rate
        FROM performance_cache pc
        WHERE pc.period = '10y'
          AND pc.return_rate IS NOT NULL
          AND pc.etf_code IN (
              SELECT etf_code FROM price_histories
              GROUP BY etf_code
              HAVING COUNT(*) >= 1200  -- 約5年 (250営業日 * 5)
          )
        ORDER BY pc.return_rate DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [row[0] for row in cur.fetchall()]


def fetch_etf_names(conn, codes):
    """ETF名を取得."""
    if not codes:
        return {}
    placeholders = ",".join(["?"] * len(codes))
    cur = conn.cursor()
    cur.execute(f"SELECT code, name FROM etfs WHERE code IN ({placeholders})", codes)
    return {row[0]: row[1] for row in cur.fetchall()}


def fetch_price_history(conn, code, since_date=None):
    """銘柄の日次クローズ価格を取得し、phase05形式 [{date, close}, ...]に整形."""
    cur = conn.cursor()
    if since_date:
        cur.execute(
            "SELECT date, close FROM price_histories WHERE etf_code = ? "
            "AND date >= ? ORDER BY date ASC",
            (code, since_date),
        )
    else:
        cur.execute(
            "SELECT date, close FROM price_histories WHERE etf_code = ? "
            "ORDER BY date ASC",
            (code,),
        )
    return [{"date": r[0], "close": float(r[1])} for r in cur.fetchall() if r[1] is not None]


def fetch_performance(conn, code):
    """各期間のreturn_rate/volatilityを取得."""
    cur = conn.cursor()
    cur.execute(
        "SELECT period, return_rate, volatility FROM performance_cache WHERE etf_code = ?",
        (code,),
    )
    perf = {}
    for period, ret, vol in cur.fetchall():
        perf[period] = {"return_rate": ret, "volatility": vol}
    return perf


def calc_correlation_with_benchmark(bench_returns, target_returns):
    """ベンチマークと候補の月次リターンを共通月で揃えて相関を計算."""
    # 月インデックスで揃える: returnsはリストなので、月キー再構築
    if not bench_returns or not target_returns:
        return None, 0
    # 単純に末尾から共通長を取る
    min_len = min(len(bench_returns), len(target_returns))
    if min_len < 36:  # 3年未満は不足扱い
        return None, min_len
    # 末尾揃え（直近データを使う前提）
    b = bench_returns[-min_len:]
    t = target_returns[-min_len:]
    return _pearson_correlation(b, t), min_len


def extract_monthly_returns_aligned(price_data: dict):
    """各銘柄について {month_key: return} の辞書を返す（日付揃え用）."""
    result = {}
    for ticker, prices in price_data.items():
        if not isinstance(prices, list) or len(prices) < 2:
            continue
        # 月最終営業日価格（より安定）を使う: 同月内で日付最大のcloseを保持
        monthly_prices = {}
        for p in prices:
            date_str = p.get("date", "")
            if not date_str:
                continue
            month_key = date_str[:7]
            # 上書きで月内最終日が残る（dateは昇順前提）
            monthly_prices[month_key] = p.get("close", 0)
        sorted_months = sorted(monthly_prices.keys())
        m_returns = {}
        for i in range(1, len(sorted_months)):
            prev_p = monthly_prices[sorted_months[i - 1]]
            curr_p = monthly_prices[sorted_months[i]]
            if prev_p > 0:
                m_returns[sorted_months[i]] = (curr_p - prev_p) / prev_p
        result[ticker] = m_returns
    return result


def calc_corr_two_spans(bench_monthly: dict, target_monthly: dict, latest_month: str):
    """直近10年(120ヶ月)・直近5年(60ヶ月)の相関を計算."""
    # 共通月キーで揃える
    common_months = sorted(set(bench_monthly.keys()) & set(target_monthly.keys()))
    if not common_months:
        return None, None, 0

    # 直近月でカット
    common_months = [m for m in common_months if m <= latest_month]
    n_common = len(common_months)

    def calc_for_span(months_count):
        if n_common < months_count:
            return None
        recent = common_months[-months_count:]
        b = [bench_monthly[m] for m in recent]
        t = [target_monthly[m] for m in recent]
        return _pearson_correlation(b, t)

    # 最低36ヶ月でないと相関値の信頼性が低い
    rho_10y = calc_for_span(120) if n_common >= 120 else (
        _pearson_correlation(
            [bench_monthly[m] for m in common_months],
            [target_monthly[m] for m in common_months],
        ) if n_common >= 36 else None
    )
    rho_5y = calc_for_span(60) if n_common >= 60 else None
    return rho_10y, rho_5y, n_common


def calc_annual_return(total_return_pct, years):
    """累積リターン(%)から年率リターン(%)を計算."""
    if total_return_pct is None or years <= 0:
        return None
    r = total_return_pct / 100.0
    if 1 + r <= 0:
        return None
    return (math.pow(1 + r, 1.0 / years) - 1) * 100


def calc_sharpe(annual_return_pct, volatility_pct):
    """簡易シャープ. volatilityは月次基準を仮定（phase05慣例）して年率化."""
    if annual_return_pct is None or volatility_pct is None or volatility_pct <= 0:
        return None
    # performance_cacheのvolatilityが年率%なのか月次%なのか明示されていないので、
    # 慣例（phase05_shared_calc）に合わせ「月次stdev*sqrt(12)」を仮定して年率化する用に
    # volatility_pct を月次ボラとみなす実装。年率化:
    annual_vol = volatility_pct * math.sqrt(12)
    return annual_return_pct / annual_vol


def calc_annualized_vol_from_monthly(monthly_returns_dict, window_months=120,
                                       outlier_abs_threshold=0.7):
    """月次リターン辞書から年率ボラ(%)を計算（標本標準偏差*sqrt(12)*100）.

    window_months 件分の直近月を使う。データ不足なら全期間で計算（最低36ヶ月）.
    |月次リターン| > outlier_abs_threshold（既定0.7=70%）は株式併合・分割未調整による
    価格ジャンプ疑いの外れ値として除外する。除外件数も返す.
    """
    if not monthly_returns_dict:
        return None, 0, 0
    sorted_months = sorted(monthly_returns_dict.keys())
    if len(sorted_months) < 36:
        return None, len(sorted_months), 0
    use_months = sorted_months[-window_months:] if len(sorted_months) >= window_months else sorted_months
    raw = [monthly_returns_dict[m] for m in use_months]
    rets = [r for r in raw if abs(r) <= outlier_abs_threshold]
    n_excluded = len(raw) - len(rets)
    n = len(rets)
    if n < 2:
        return None, n, n_excluded
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)  # 標本分散
    monthly_std = math.sqrt(var)
    annual_vol_pct = monthly_std * math.sqrt(12) * 100
    return annual_vol_pct, n, n_excluded


def calc_sharpe_v2(annual_return_pct, annual_vol_pct):
    """年率リターン(%) / 年率ボラ(%) ; rf=0仮定."""
    if annual_return_pct is None or annual_vol_pct is None or annual_vol_pct <= 0:
        return None
    return annual_return_pct / annual_vol_pct


def build_candidate_pool(conn):
    """pinned ＋ 自動抽出（10y上位30）→ 重複排除."""
    auto = fetch_top_10y_returns(conn, limit=30)
    seen = set()
    pool = []
    for c in PINNED_CODES + auto:
        if c not in seen:
            seen.add(c)
            pool.append(c)
    return pool


def main():
    conn = get_conn()
    print("[INFO] volatility: 価格データから自前計算（年率%）", file=sys.stderr)

    pool = build_candidate_pool(conn)
    print(f"[INFO] candidate pool size: {len(pool)}", file=sys.stderr)

    names = fetch_etf_names(conn, pool)

    # 価格データ取得（過去11年程度を遡る; 余裕を持って2014-01-01から）
    since = "2014-01-01"
    price_data = {}
    for code in pool:
        prices = fetch_price_history(conn, code, since_date=since)
        if prices:
            price_data[code] = prices

    # 月次リターン抽出（共通月マッピング）
    monthly = extract_monthly_returns_aligned(price_data)

    if "1547" not in monthly:
        print("[ERROR] 1547 monthly returns missing", file=sys.stderr)
        sys.exit(1)

    bench_monthly = monthly["1547"]
    latest_month = max(bench_monthly.keys())

    # パフォーマンスデータ取得 & 各候補のメトリクス計算
    rows = []
    for code in pool:
        perf = fetch_performance(conn, code)
        target_monthly = monthly.get(code, {})
        rho_10y, rho_5y, n_common = calc_corr_two_spans(
            bench_monthly, target_monthly, latest_month
        )

        # 価格データ年数
        if target_monthly:
            data_years = len(target_monthly) / 12.0
        else:
            data_years = 0

        # リターン指標
        ret_10y_raw = perf.get("10y", {}).get("return_rate")
        ret_5y_raw = perf.get("5y", {}).get("return_rate")

        # 異常値検出（10y累積リターン > 1000% は分割未調整等のキャッシュバグ疑いとして除外）
        ret_anomaly = False
        if ret_10y_raw is not None and ret_10y_raw > 1000:
            ret_anomaly = True
            ret_10y = None
        else:
            ret_10y = ret_10y_raw
        ret_5y = ret_5y_raw if (ret_5y_raw is None or ret_5y_raw <= 1000) else None

        ann_ret_10y = calc_annual_return(ret_10y, 10) if ret_10y is not None else None
        ann_ret_5y = calc_annual_return(ret_5y, 5) if ret_5y is not None else None

        # 年率ボラを月次リターンから自前計算（外れ値除外あり）
        vol_10y, _, n_excl_10y = calc_annualized_vol_from_monthly(target_monthly, window_months=120)
        vol_5y, _, n_excl_5y = calc_annualized_vol_from_monthly(target_monthly, window_months=60)

        # 多数の外れ値が混入（>3ヶ月）した銘柄は価格データ不正確として除外フラグ
        price_anomaly = (n_excl_10y > 3 or n_excl_5y > 2)
        if price_anomaly:
            vol_10y = None
            vol_5y = None

        # 異常値の場合はボラ・シャープも信頼できないので除外
        if ret_anomaly:
            vol_10y = None
            vol_5y = None

        sharpe_10y = calc_sharpe_v2(ann_ret_10y, vol_10y)
        sharpe_5y = calc_sharpe_v2(ann_ret_5y, vol_5y)

        rows.append({
            "code": code,
            "name": names.get(code, "(名称不明)"),
            "rho_10y": rho_10y,
            "rho_5y": rho_5y,
            "data_years": round(data_years, 1),
            "n_common_months": n_common,
            "total_return_10y_pct": ret_10y,
            "annual_return_10y_pct": ann_ret_10y,
            "volatility_10y_pct": vol_10y,
            "sharpe_10y": sharpe_10y,
            "total_return_5y_pct": ret_5y,
            "annual_return_5y_pct": ann_ret_5y,
            "volatility_5y_pct": vol_5y,
            "sharpe_5y": sharpe_5y,
            "ret_anomaly_flag": ret_anomaly,
            "price_anomaly_flag": price_anomaly,
            "n_outlier_months_10y": n_excl_10y,
        })

    # 複合スコア = (1-|ρ10y|)*0.5 + sharpe/max_sharpe*0.5
    valid_sharpe = [r["sharpe_10y"] for r in rows if r["sharpe_10y"] is not None]
    max_sharpe = max(valid_sharpe) if valid_sharpe else 1.0

    for r in rows:
        rho = r["rho_10y"]
        s = r["sharpe_10y"]
        if rho is None or s is None:
            r["composite_score"] = None
        else:
            r["composite_score"] = (1 - abs(rho)) * 0.5 + (s / max_sharpe) * 0.5

    # 1547自身は除外したランキング
    ranking = [r for r in rows if r["code"] != "1547"]
    ranking_sorted = sorted(
        ranking,
        key=lambda x: (x["composite_score"] is None, -(x["composite_score"] or 0)),
    )

    top15 = ranking_sorted[:15]

    # 推薦条件: ρ(10y) < 0.5 かつ 年率リターン > 5% かつ データ年数 ≥ 5
    recommended = []
    for r in ranking_sorted:
        rho = r["rho_10y"]
        ar = r["annual_return_10y_pct"]
        dy = r["data_years"]
        if rho is None or ar is None:
            continue
        if rho < 0.5 and ar > 5.0 and dy >= 5:
            recommended.append(r)
        if len(recommended) >= 5:
            break

    # 既存A群比較
    a_group_codes = ["2559", "200A", "1540"]
    a_group_rows = [r for r in rows if r["code"] in a_group_codes]

    # 1547 自身の行（参照用）
    bench_row = next((r for r in rows if r["code"] == "1547"), None)

    # JSON出力
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "benchmark": "1547",
            "analysis_date": TODAY,
            "since": since,
            "vol_calc_method": "monthly_std * sqrt(12) * 100 (annualized, from price_histories)",
            "candidate_pool_size": len(pool),
            "pinned_codes": PINNED_CODES,
            "latest_common_month": latest_month,
        },
        "benchmark_row": bench_row,
        "all_rows": rows,
        "top15_by_composite": top15,
        "recommended_top5": recommended,
        "a_group_comparison": a_group_rows,
    }
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)

    # Markdown出力
    write_markdown(out)

    print(f"[OK] JSON: {REPORT_JSON}", file=sys.stderr)
    print(f"[OK] MD : {REPORT_MD}", file=sys.stderr)


def fmt(x, digits=3, suffix=""):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{digits}f}{suffix}"
    return f"{x}{suffix}"


def write_markdown(out):
    md = []
    md.append("# 1547コア・パートナー候補分析レポート\n")
    md.append(f"**生成日**: {out['metadata']['generated_at']}  ")
    md.append(f"**ベンチマーク**: 1547 (上場インデックスファンド米国株式 S&P500)  ")
    md.append(f"**候補プール**: {out['metadata']['candidate_pool_size']} 銘柄（pinned + 10y上位30 重複排除後）  ")
    md.append(f"**価格データ取得開始**: {out['metadata']['since']}  ")
    md.append(f"**共通最新月**: {out['metadata']['latest_common_month']}  ")
    md.append(f"**volatility算出**: 月次リターンの標本標準偏差 × √12 × 100（年率%）\n")

    md.append("## サマリ\n")
    rec = out["recommended_top5"]
    if rec:
        rec_codes = ", ".join([f"{r['code']}（ρ={fmt(r['rho_10y'],2)}, 年率={fmt(r['annual_return_10y_pct'],1,'%')}）" for r in rec])
        md.append(f"- 1547に対し相関<0.5・年率リターン>5%・データ5年以上を満たす推薦パートナー候補は **{len(rec)}件**: {rec_codes}")
    else:
        md.append("- 推薦条件を満たす候補は見つかりませんでした。条件を緩める検討要。")
    md.append("- 複合スコア（相関の低さ50% + シャープ正規化50%）で上位15銘柄を抽出。")
    md.append("- 既存A群（2559/200A/1540）との比較を本文表に含めています。\n")

    md.append("## データソース・分析期間\n")
    md.append("- DB: `price_histories`（日次クローズ）, `performance_cache`（期間別リターン・ボラティリティ）, `etfs`（名称）")
    md.append("- 月次リターン: 各月の最終営業日クローズ価格から算出")
    md.append("- 相関: ピアソン（`phase05_shared_calc._pearson_correlation` 流用）。共通月で揃え、直近120ヶ月=10y, 直近60ヶ月=5y")
    md.append("- 年率リターン: `(1 + total_return_pct/100)^(1/years) - 1`")
    md.append(f"- 年率ボラ: 月次リターンの標本標準偏差 × √12 × 100（DB側にlong-spanボラが無いため自前計算）")
    md.append(f"- シャープ: 年率リターン(%) / 年率ボラ(%)（rf=0% 仮定）\n")

    md.append("## マトリクス（上位15: 複合スコア降順）\n")
    md.append("| 順位 | コード | 名称 | ρ(10y) | ρ(5y) | 年率Ret(10y) | ボラ(10y) | シャープ(10y) | データ年数 | 複合スコア |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(out["top15_by_composite"], 1):
        md.append(
            f"| {i} | {r['code']} | {r['name'][:24]} | "
            f"{fmt(r['rho_10y'],2)} | {fmt(r['rho_5y'],2)} | "
            f"{fmt(r['annual_return_10y_pct'],2,'%')} | "
            f"{fmt(r['volatility_10y_pct'],2,'%')} | "
            f"{fmt(r['sharpe_10y'],3)} | "
            f"{fmt(r['data_years'],1)}年 | "
            f"{fmt(r['composite_score'],3)} |"
        )
    md.append("")

    md.append("## ベンチマーク（1547）の指標\n")
    b = out["benchmark_row"]
    if b:
        md.append(f"- 名称: {b['name']}")
        md.append(f"- 10y 累積リターン: {fmt(b['total_return_10y_pct'],2,'%')}, 年率: {fmt(b['annual_return_10y_pct'],2,'%')}, ボラ: {fmt(b['volatility_10y_pct'],2,'%')}, シャープ: {fmt(b['sharpe_10y'],3)}")
        md.append(f"- 5y 累積リターン: {fmt(b['total_return_5y_pct'],2,'%')}, 年率: {fmt(b['annual_return_5y_pct'],2,'%')}, ボラ: {fmt(b['volatility_5y_pct'],2,'%')}, シャープ: {fmt(b['sharpe_5y'],3)}")
        md.append(f"- データ年数: {fmt(b['data_years'],1)}年\n")

    md.append("## 推薦パートナー候補 上位5\n")
    if not out["recommended_top5"]:
        md.append("該当なし。推薦条件（ρ<0.5, 年率>5%, データ5年以上）を緩める検討を推奨します。\n")
    else:
        for i, r in enumerate(out["recommended_top5"], 1):
            md.append(f"### {i}. {r['code']} — {r['name']}\n")
            md.append(f"- ρ(10y)={fmt(r['rho_10y'],3)}, ρ(5y)={fmt(r['rho_5y'],3)}, 年率Ret(10y)={fmt(r['annual_return_10y_pct'],2,'%')}, ボラ(10y)={fmt(r['volatility_10y_pct'],2,'%')}, シャープ(10y)={fmt(r['sharpe_10y'],3)}, データ={fmt(r['data_years'],1)}年")
            # トレーダー視点コメント
            md.append(f"- **解釈**: {_trader_comment(r)}")
            md.append("")

    md.append("## 既存A群との比較\n")
    md.append("| コード | 名称 | ρ(10y) | ρ(5y) | 年率Ret(10y) | ボラ(10y) | シャープ(10y) | データ年数 | 複合スコア |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for r in out["a_group_comparison"]:
        md.append(
            f"| {r['code']} | {r['name'][:30]} | "
            f"{fmt(r['rho_10y'],2)} | {fmt(r['rho_5y'],2)} | "
            f"{fmt(r['annual_return_10y_pct'],2,'%')} | "
            f"{fmt(r['volatility_10y_pct'],2,'%')} | "
            f"{fmt(r['sharpe_10y'],3)} | "
            f"{fmt(r['data_years'],1)}年 | "
            f"{fmt(r['composite_score'],3)} |"
        )
    md.append("")

    md.append("## 制約・留意点\n")
    md.append("- **データ期間不足**: データ年数<5年の銘柄は推薦から除外。ρ計算も共通月36ヶ月未満は `—` 扱い。")
    md.append("- **月次リターンの限界**: 日次より粗いため、急変動局面の連動性を過小評価する可能性あり。")
    md.append("- **リスクフリーレート**: rf=0% 仮定（簡易シャープ）。日本のJGB10y利回りで補正する場合はシャープが0.05〜0.1程度小さくなる。")
    md.append("- **volatility算出**: `performance_cache.volatility` は1y期間のみ記録があり10y/5yは未計算。本分析では `price_histories` の月次リターン標本標準偏差を年率化（×√12）して使用した。スポット日次データから直接算出する方法と比べると、月次粒度で測定するためボラ値はやや低めに出る傾向（粒度効果）。順位への影響は限定的。")
    md.append("- **相関の安定性**: 直近5年と10年で乖離がある銘柄は「相関レジーム変化」の可能性あり。低リスク資産が金融危機以降に株式と連動性を増したケース等は要監視。")
    md.append("- **異常値除外（リターン側）**: 10y累積リターンが>1000%の銘柄（WisdomTreeコモディティETFの1676/1692/1697等）は `performance_cache` の算出時に分割未調整キャッシュバグの疑いがあるため、ボラ・シャープ・推薦対象から除外している。")
    md.append("- **異常値除外（ボラ側）**: 単月リターン|>70%|の月が10年内で3件超ある銘柄（株式併合・分割未調整による価格ジャンプ）は、その異常月を計算から除外。除外しても多数残る場合（1672/1357等）はボラ・シャープを `—` で表示。`price_histories` 側のデータ品質改善（分割調整パイプライン）が抜本対策。")
    md.append("- **本分析はDB既存データのみ**。新規yfinance呼び出しなし。\n")

    REPORT_MD.write_text("\n".join(md), encoding="utf-8")


def _trader_comment(r):
    """プロのトレーダー視点で1-2文の解釈."""
    code = r["code"]
    rho = r["rho_10y"]
    ar = r["annual_return_10y_pct"]
    vol = r["volatility_10y_pct"]
    name = r["name"]

    # 既知銘柄の特性をハードコードコメント補強
    known = {
        "1540": "金は株式とほぼ無相関のディフェンシブ資産で、株式急落時の保険として機能してきた歴史を持つ",
        "1542": "銀は金より産業需要連動が強くβがやや高いが、米株とは依然低相関",
        "2621": "米国超長期債（円ヘッジ）は金利低下局面で株式と逆相関化する典型的な分散資産",
        "2559": "全世界株式は1547と高相関（米国比率6割超）になりやすく、純粋なパートナーとしては機能が弱い",
        "200A": "日本半導体は世界半導体サイクルに連動し、S&P500（特にNDX寄与）と中〜高相関の傾向",
        "1306": "TOPIXは1547と中相関（為替・グローバル景気経由）。国内分散として標準的",
        "1671": "WTI原油はインフレヘッジになる一方ボラが極端に高く、シャープは低くなりやすい",
        "1357": "日経ダブルインバースは構造的な逓減効果でロング保有はNG（短期ヘッジ専用）",
    }
    base = known.get(code, "")

    parts = []
    if rho is not None:
        if rho < 0.2:
            parts.append(f"ρ={rho:.2f}と極低相関で純粋な分散効果が期待できる")
        elif rho < 0.5:
            parts.append(f"ρ={rho:.2f}と中低相関、部分的な分散効果")
        elif rho < 0.7:
            parts.append(f"ρ={rho:.2f}と中相関、分散効果は限定的")
        else:
            parts.append(f"ρ={rho:.2f}と高相関、コア重複の懸念")

    if ar is not None and vol is not None:
        if ar > 10 and vol < 20:
            parts.append("リターン・リスクのバランスが良好")
        elif ar > 5:
            parts.append("ミドルリターン水準")

    comment = "。".join(parts)
    if base:
        comment = f"{comment}。{base}"
    return comment + "。"


if __name__ == "__main__":
    main()
