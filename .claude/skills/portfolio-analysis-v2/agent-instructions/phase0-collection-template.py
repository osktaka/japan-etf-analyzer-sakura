"""
Phase 0: データ収集テンプレートスクリプト

このファイルは phase0-data-collection.md のテンプレートスクリプトです。
サブエージェントがデータ収集スクリプトを実装する際の参考実装として使用します。

プレースホルダー:
  {USER_ID}   → 認証ユーザーID
  {PASSWORD}  → 認証パスワード
  {WORK_DIR}  → 作業ディレクトリパス

注意: このテンプレートをコピーして使う場合、上記プレースホルダーを実際の値に置換すること。
サブエージェントが実装する場合は、メインから渡された引数で動的に置換する。
株式分割検証コードは本テンプレート末尾に組込済み。検証失敗時はスクリプトが停止する。

全データはHTTP API経由で取得する。Flask import（create_app, db）は不要。
"""

import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import json
from pathlib import Path
import sys

# 作業ディレクトリ（引数から取得）
if len(sys.argv) < 2:
    print("Usage: python script.py <WORK_DIR>")
    sys.exit(1)
WORK_DIR = Path(sys.argv[1])
WORK_DIR.mkdir(parents=True, exist_ok=True)

# データソースの取得状態を記録
data_status = {}

def record_status(name, resp=None, data=None, error=None):
    """データソースの取得状態を記録"""
    if error:
        data_status[name] = {"status": "error", "error": str(error)[:200]}
    elif resp is not None and resp.status_code != 200:
        data_status[name] = {"status": "error", "http_status": resp.status_code, "error": resp.text[:200]}
    elif data is None or (isinstance(data, list) and len(data) == 0) or (isinstance(data, dict) and len(data) == 0):
        data_status[name] = {"status": "empty", "detail": "レスポンス200だが中身が空"}
    else:
        count = len(data) if isinstance(data, (list, dict)) else 1
        data_status[name] = {"status": "ok", "count": count}

# API認証（認証リクエストはリトライなし・即座に失敗）
session = requests.Session()
login_resp = session.post('http://localhost:8902/api/v1/auth/login', timeout=30,
                          json={'user_id': '{USER_ID}', 'password': '{PASSWORD}'})
if login_resp.status_code != 200:
    print(f"認証エラー: {login_resp.status_code} {login_resp.text}")
    sys.exit(1)
print(f"Login: {login_resp.status_code}")

# リトライ設定（認証成功後のデータ取得リクエストに適用）
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# 1. 保有銘柄取得
holdings_resp = session.get('http://localhost:8902/api/v1/portfolio/holdings')
if holdings_resp.status_code != 200:
    print(f"保有銘柄取得エラー: {holdings_resp.status_code} {holdings_resp.text}")
    sys.exit(1)
holdings = holdings_resp.json()
etf_codes = [h['etf_code'] for h in holdings['data']]
record_status('holdings', data=holdings.get('data', []))
print(f"保有銘柄数: {len(etf_codes)}")

# 2. サマリー取得
summary_resp = session.get('http://localhost:8902/api/v1/portfolio')
if summary_resp.status_code != 200:
    record_status('summary', resp=summary_resp)
    print(f"サマリー取得エラー: {summary_resp.status_code}")
    print("サマリーデータなしでは総資産検証が不可能。スクリプトを停止します。")
    sys.exit(1)
summary = summary_resp.json()
record_status('summary', data=summary.get('data'))

# 3. 資産推移取得
valuation_resp = session.get('http://localhost:8902/api/v1/portfolio/valuation-history?period=3y')
valuation_history = valuation_resp.json() if valuation_resp.status_code == 200 else None
record_status('valuation_history', resp=valuation_resp, data=valuation_history.get('data', []) if valuation_history else None)
if valuation_history is None:
    print(f"資産推移取得エラー: {valuation_resp.status_code}（スキップ）")

# 4. バルク分析データAPI（performance_cache, score_cache, etfs, tags, price_data）
performance_data = []
score_data = []
etf_data = []
tag_data = []
price_data = []
price_data_daily_30d = []
price_data_close_250d = []

try:
    analysis_resp = session.get('http://localhost:8902/api/v1/portfolio/analysis-data')
    if analysis_resp.status_code == 200:
        analysis = analysis_resp.json().get('data', {})
        performance_data = analysis.get('performance_cache', [])
        score_data = analysis.get('score_cache', [])
        etf_data = analysis.get('etf_data', [])
        tag_data = analysis.get('tag_data', [])
        price_data = analysis.get('price_data', [])
        price_data_daily_30d = analysis.get('price_data_daily_30d', [])
        price_data_close_250d = analysis.get('price_data_close_250d', [])
        record_status('performance_cache', data=performance_data)
        record_status('score_cache', data=score_data)
        record_status('etf_data', data=etf_data)
        record_status('tag_data', data=tag_data)
        record_status('price_data', data=price_data)
        record_status('price_data_daily_30d', data=price_data_daily_30d)
        record_status('price_data_close_250d', data=price_data_close_250d)
    else:
        print(f"分析データAPI取得エラー: {analysis_resp.status_code} {analysis_resp.text[:200]}")
        for name in ['performance_cache', 'score_cache', 'etf_data', 'tag_data', 'price_data', 'price_data_daily_30d', 'price_data_close_250d']:
            record_status(name, resp=analysis_resp)
except Exception as e:
    print(f"分析データAPI接続エラー: {e}")
    for name in ['performance_cache', 'score_cache', 'etf_data', 'tag_data', 'price_data', 'price_data_daily_30d', 'price_data_close_250d']:
        if name not in data_status:
            record_status(name, error=e)

# 5. おすすめAPI
recommendations = {}
for perspective in ['balance', 'dividend', 'low-cost']:
    rec_resp = session.get(f'http://localhost:8902/api/v1/recommendations?perspective={perspective}')
    if rec_resp.status_code == 200:
        recommendations[perspective] = rec_resp.json()
        record_status(f'recommendations_{perspective}', data=recommendations[perspective].get('data', []))
    else:
        print(f"おすすめAPI取得エラー（{perspective}）: {rec_resp.status_code}（スキップ）")
        recommendations[perspective] = None
        record_status(f'recommendations_{perspective}', resp=rec_resp)

# 6. 比較API（保有銘柄同士、5銘柄ずつ分割して取得）
compare_performance_list = []
compare_scores_list = []
if len(etf_codes) >= 2:
    for i in range(0, len(etf_codes), 5):
        chunk = etf_codes[i:i+5]
        if len(chunk) >= 2:
            compare_codes = ','.join(chunk)
            compare_perf_resp = session.get(f'http://localhost:8902/api/v1/compare/performance?codes={compare_codes}')
            if compare_perf_resp.status_code == 200:
                perf_json = compare_perf_resp.json()
                compare_performance_list.append(perf_json)
                record_status('compare_performance', data=perf_json.get('data', {}))
            else:
                print(f"比較API（performance）エラー: {compare_perf_resp.status_code}（スキップ）")
                compare_performance_list.append(None)
                record_status('compare_performance', resp=compare_perf_resp)
            compare_score_resp = session.get(f'http://localhost:8902/api/v1/compare/scores?codes={compare_codes}')
            if compare_score_resp.status_code == 200:
                score_json = compare_score_resp.json()
                compare_scores_list.append(score_json)
                record_status('compare_scores', data=score_json.get('data', {}))
            else:
                print(f"比較API（scores）エラー: {compare_score_resp.status_code}（スキップ）")
                compare_scores_list.append(None)
                record_status('compare_scores', resp=compare_score_resp)

# 7. yfinance配当データ取得（3年分、年別集計）
dividend_data = {}
try:
    import yfinance as yf
    from datetime import datetime, timedelta
    three_years_ago = datetime.now() - timedelta(days=3*365)
    dividend_fetch_errors = []

    for code in etf_codes:
        try:
            ticker = yf.Ticker(f"{code}.T")
            dividends = ticker.dividends
            if dividends is not None and len(dividends) > 0:
                # 3年以内のデータに絞り込み
                recent = dividends[dividends.index >= three_years_ago.strftime('%Y-%m-%d')]
                if len(recent) > 0:
                    yearly = {}
                    for idx, val in recent.items():
                        year = str(idx.year)
                        yearly[year] = yearly.get(year, 0) + float(val)
                    dividend_data[code] = yearly
                else:
                    dividend_data[code] = {}
            else:
                dividend_data[code] = {}
        except Exception as e:
            print(f"配当データ取得エラー（{code}）: {e}（スキップ）")
            dividend_fetch_errors.append(f"{code}: {str(e)[:100]}")
            dividend_data[code] = {}

    if dividend_data and any(len(v) > 0 for v in dividend_data.values()):
        record_status('dividend_data', data=dividend_data)
    elif dividend_fetch_errors:
        record_status('dividend_data', error=f"一部取得失敗: {'; '.join(dividend_fetch_errors[:3])}")
    else:
        record_status('dividend_data', data={})
        print("配当データ: 全銘柄で配当データなし")
except ImportError:
    print("yfinanceがインストールされていません。配当データをスキップします。")
    dividend_data = None
    record_status('dividend_data', error="yfinanceモジュールが利用不可")
except Exception as e:
    print(f"配当データ取得で予期しないエラー: {e}")
    dividend_data = None
    record_status('dividend_data', error=str(e)[:200])

# _metadata生成（アナリストがフィールド名を正確に把握するため）
def build_metadata(data, extra_info=None):
    if not data:
        return {"count": 0, "columns": [], "sample": None}
    first = data[0] if isinstance(data, list) else data
    meta = {"count": len(data), "columns": list(first.keys()), "sample": {k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v for k, v in first.items()}}
    if extra_info:
        meta.update(extra_info)
    return meta

_metadata = {
    "score_cache": build_metadata(score_data, {
        "perspectives": sorted(set(r['perspective'] for r in score_data)) if score_data else [],
        "axes": ["dividend_power", "cost_efficiency", "scale_reliability", "trading_quality", "return_performance"]
    }),
    "performance_cache": build_metadata(performance_data, {
        "periods": sorted(set(r['period'] for r in performance_data)) if performance_data else []
    }),
    "price_data": build_metadata(price_data),
    "price_data_daily_30d": build_metadata(price_data_daily_30d),
    "price_data_close_250d": build_metadata(price_data_close_250d),
    "dividend_data": {
        "count": len(dividend_data) if dividend_data else 0,
        "columns": ["etf_code"],
        "sample": {k: v for k, v in list(dividend_data.items())[:1]} if dividend_data and len(dividend_data) > 0 else None
    },
    "etf_data": build_metadata(etf_data),
    "tag_data": build_metadata(tag_data),
    "etf_codes": etf_codes,
    "holding_count": len(etf_codes),
    "_data_status": data_status
}

# === API系データ全失敗チェック ===
api_sources = ['performance_cache', 'score_cache', 'etf_data', 'tag_data', 'price_data', 'price_data_daily_30d', 'price_data_close_250d']
api_all_failed = all(data_status.get(s, {}).get('status') == 'error' for s in api_sources)
if api_all_failed:
    print("分析データが全て取得失敗。有用な分析レポートを生成できません。")
    print("推奨: Docker環境・APIサーバーの状態を確認してください。")
    sys.exit(1)

# === 株式分割調整データの検証（必須） ===
# 重要: holdings/summaryデータは全て /api/v1/portfolio/holdings および
# /api/v1/portfolio/summary API経由で取得された値であること。
# APIはSplitAdjustmentServiceを経由して株式分割調整済みデータを返す。
# average_cost, quantity等はAPIレスポンスの値をそのまま使用しており、
# DB（tradesテーブル）への直接クエリは一切含まれていない。
#
# 【禁止】tradesテーブルへの直接クエリ（SELECT * FROM trades等）は
# 分割前の元の数量・単価が返されるため、絶対に使用しないこと。
# 詳細: phase0-data-collection.md「禁止パターン」セクション参照
print("--- データ整合性検証 ---")
holdings_data_v = (holdings or {}).get('data', [])
if not holdings_data_v:
    print("検証エラー: holdingsデータが空です。スキル全体を中止します。")
    sys.exit(1)
summary_data_v = (summary or {}).get('data', {})
cash_v = summary_data_v.get('cash_balance', 0)
total_asset_v = summary_data_v.get('total_asset', 0)

validation_errors = []
total_cv_v = 0
for h in holdings_data_v:
    qty = h.get('quantity', 0)
    price = h.get('current_price', 0)
    cv = h.get('current_value', 0)
    calc_cv = qty * price
    if abs(calc_cv - cv) > 1:  # 1円以上の誤差
        validation_errors.append(
            f"評価額不整合: {h['etf_code']} {qty}口×{price}円={calc_cv}円 ≠ {cv}円"
        )
    avg_cost = h.get('average_cost', 0)
    total_cost_h = h.get('total_cost', 0)
    calc_tc = round(avg_cost * qty, 2)
    if abs(calc_tc - total_cost_h) > 1:
        validation_errors.append(
            f"取得原価不整合: {h['etf_code']} {avg_cost}円×{qty}口={calc_tc}円 ≠ {total_cost_h}円"
        )
    total_cv_v += cv

calc_total_v = total_cv_v + cash_v
if abs(calc_total_v - total_asset_v) > 10:  # 10円以上の誤差
    validation_errors.append(
        f"総資産不整合: 銘柄合計{total_cv_v}円 + 現金{cash_v}円 "
        f"= {calc_total_v}円 ≠ サマリー{total_asset_v}円"
    )

if validation_errors:
    print("データ検証エラー:")
    for err in validation_errors:
        print(f"  - {err}")
    print("不正確なデータでの分析を防止するため、スクリプトを停止します。")
    sys.exit(1)

print(f"検証OK: 総資産{total_asset_v:,.0f}円"
      f"（銘柄{total_cv_v:,.0f}円 + 現金{cash_v:,.0f}円）")

# データ保存
output = {
    'user_id': '{USER_ID}',
    '_metadata': _metadata,
    'holdings': holdings,
    'summary': summary,
    'valuation_history': valuation_history,
    'performance_cache': performance_data if performance_data else None,
    'score_cache': score_data if score_data else None,
    'etf_data': etf_data if etf_data else None,
    'tag_data': tag_data if tag_data else None,
    'price_data': price_data if price_data else None,
    'price_data_daily_30d': price_data_daily_30d if price_data_daily_30d else None,
    'price_data_close_250d': price_data_close_250d if price_data_close_250d else None,
    'dividend_data': dividend_data,
    'recommendations': recommendations,
    'compare_performance': compare_performance_list if compare_performance_list else None,
    'compare_scores': compare_scores_list if compare_scores_list else None,
}

output_path = WORK_DIR / '00_portfolio_data.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

# 00_portfolio_reference.md の生成（レポートのセクション1・11.2で使用するmarkdownテーブル）
holdings_data = holdings.get('data', [])
summary_data = summary.get('data', {}) if summary else {}
cash = summary_data.get('cash_balance', 0)
total_asset_from_summary = summary_data.get('total_asset', 0)

total_cv = sum(h.get('current_value', 0) for h in holdings_data)
total_pnl = sum(h.get('unrealized_pnl', 0) for h in holdings_data)
total_cost = sum(h.get('total_cost', 0) for h in holdings_data)
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

ref_lines = []
ref_lines.append("# ポートフォリオ参照データ（プログラマティック生成）")
ref_lines.append("")
ref_lines.append("> このファイルはPhase 0のPythonスクリプトで自動生成されました。")
ref_lines.append("> Phase 3+4統合エージェントは、セクション1.1/1.2/11.2をこのファイルからそのまま転記してください。")
ref_lines.append("> 数値の丸め・フォーマット変更は禁止です。")
ref_lines.append("")

# セクション1.1用テーブル
ref_lines.append("## セクション1.1: 銘柄別保有状況")
ref_lines.append("")
ref_lines.append("| コード | 銘柄名 | 保有数量 | 平均取得単価 | 現在価格 | 評価額 | 損益 | 損益率 | 保有比率 |")
ref_lines.append("|-------|--------|---------|------------|---------|-------|------|-------|---------|")
for h in holdings_data:
    code = h['etf_code']
    etf_info = h.get('etf', {})
    name = etf_info.get('name', code) if isinstance(etf_info, dict) else code
    qty = h.get('quantity', 0)
    avg_cost = h.get('average_cost', 0)
    price = h.get('current_price', 0)
    cv = h.get('current_value', 0)
    pnl = h.get('unrealized_pnl', 0)
    pnl_pct = h.get('unrealized_pnl_percent', 0)
    ratio = (cv / total_cv * 100) if total_cv > 0 else 0
    pnl_sign = "+" if pnl >= 0 else ""
    pnl_pct_sign = "+" if pnl_pct >= 0 else ""
    ref_lines.append(
        f"| {code} | {name} | {qty:,.0f}口 | {avg_cost:,.1f}円 | {price:,.0f}円 | {cv:,.0f}円 | {pnl_sign}{pnl:,.0f}円 | {pnl_pct_sign}{pnl_pct:.1f}% | {ratio:.1f}% |"
    )
ref_lines.append("")

# セクション1.2用サマリー
ref_lines.append("## セクション1.2: サマリー")
ref_lines.append("")
ref_lines.append("```")
ref_lines.append(f"合計評価額: {total_cv:,.0f}円")
ref_lines.append(f"現金残高: {cash:,.0f}円")
ref_lines.append(f"総資産: {total_asset_from_summary:,.0f}円")
pnl_sign = "+" if total_pnl >= 0 else ""
pnl_pct_sign = "+" if total_pnl_pct >= 0 else ""
ref_lines.append(f"含み損益合計: {pnl_sign}{total_pnl:,.0f}円（{pnl_pct_sign}{total_pnl_pct:.1f}%）")
ref_lines.append("```")
ref_lines.append("")

# セクション11.2用注記
ref_lines.append("## セクション11.2: 現行ポートフォリオ（改善前）")
ref_lines.append("")
ref_lines.append("> セクション1.1のテーブルと同一内容をそのまま転記してください。")
ref_lines.append("")

# チェック値（検証用）
ref_lines.append("## チェック値")
ref_lines.append("")
ref_lines.append(f"- 銘柄数: {len(holdings_data)}")
ref_lines.append(f"- 合計評価額: {total_cv:,.0f}円")
ref_lines.append(f"- 現金残高: {cash:,.0f}円")
ref_lines.append(f"- 総資産: {total_asset_from_summary:,.0f}円")

ref_path = WORK_DIR / '00_portfolio_reference.md'
with open(ref_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(ref_lines))
print(f"参照データ生成: {ref_path}")

# メインへの要約出力（この1行のみがメインのコンテキストに入る）
summary_data = summary.get('data', {}) if summary else {}
total_value = summary_data.get('total_value', 0)
print(f"データ収集完了: {len(etf_codes)}銘柄、総評価額{total_value:,.0f}円")
