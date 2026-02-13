# Phase 0: データ収集 指示書

## 前提

- 作業ディレクトリ: `{WORK_DIR}`（メインエージェントから渡される）
- Docker内パス: `/app/{WORK_DIR}`
- 認証情報: user_id=`{USER_ID}`, password=`{PASSWORD}`（メインエージェントから渡される）
- APIベースURL: `http://localhost:8902`

## データ受け渡しルール

- **入力**: なし（API/DB直接アクセス）
- **出力**: 収集データを `{WORK_DIR}/portfolio_data.json` に保存
- **メインへの戻り値**: 完了メッセージ1行のみ。データ全文やテーブル全体を返さないこと

## スキップ判断基準

このフェーズにスキップ条件はない。常に実行する。

---

## データ収集スクリプト例

```python
import requests
import json
import os
from pathlib import Path
import sys

# 作業ディレクトリ（引数から取得）
if len(sys.argv) < 2:
    print("Usage: python script.py <WORK_DIR>")
    sys.exit(1)
WORK_DIR = Path(sys.argv[1])
WORK_DIR.mkdir(parents=True, exist_ok=True)

# プロジェクトルート設定
PROJECT_ROOT = Path('/app')
sys.path.insert(0, str(PROJECT_ROOT))

from src.app import create_app
from src.models import db

# API認証
session = requests.Session()
login_resp = session.post('http://localhost:8902/api/v1/auth/login',
                          json={'user_id': '{USER_ID}', 'password': '{PASSWORD}'})
if login_resp.status_code != 200:
    print(f"認証エラー: {login_resp.status_code} {login_resp.text}")
    sys.exit(1)
print(f"Login: {login_resp.status_code}")

# 1. 保有銘柄取得
holdings_resp = session.get('http://localhost:8902/api/v1/portfolio/holdings')
if holdings_resp.status_code != 200:
    print(f"保有銘柄取得エラー: {holdings_resp.status_code} {holdings_resp.text}")
    sys.exit(1)
holdings = holdings_resp.json()
etf_codes = [h['code'] for h in holdings['holdings']]
print(f"保有銘柄数: {len(etf_codes)}")

# 2. サマリー取得
summary_resp = session.get('http://localhost:8902/api/v1/portfolio')
summary = summary_resp.json() if summary_resp.status_code == 200 else None
if summary is None:
    print(f"サマリー取得エラー: {summary_resp.status_code}（スキップ）")

# 3. 資産推移取得
valuation_resp = session.get('http://localhost:8902/api/v1/portfolio/valuation-history?period=3y')
valuation_history = valuation_resp.json() if valuation_resp.status_code == 200 else None
if valuation_history is None:
    print(f"資産推移取得エラー: {valuation_resp.status_code}（スキップ）")

# 安全なIN句の構築ヘルパー
def build_in_clause(etf_codes):
    placeholders = ', '.join([f':code_{i}' for i in range(len(etf_codes))])
    params = {f'code_{i}': code for i, code in enumerate(etf_codes)}
    return placeholders, params

# 4. DBクエリ（performance_cache, score_cache, etfs, tags）
performance_data = []
score_data = []
etf_data = []
tag_data = []
price_data = []

try:
    app = create_app()
    with app.app_context():
        placeholders, params = build_in_clause(etf_codes)

        # performance_cache
        perf_result = db.session.execute(db.text(f"""
            SELECT etf_code, period, return_rate, volatility, regression_rate
            FROM performance_cache
            WHERE etf_code IN ({placeholders})
        """), params)
        performance_data = perf_result.fetchall()

        # score_cache
        score_result = db.session.execute(db.text(f"""
            SELECT etf_code, perspective,
                   dividend_score, cost_score, scale_score, liquidity_score, return_score
            FROM score_cache
            WHERE etf_code IN ({placeholders})
        """), params)
        score_data = score_result.fetchall()

        # etfs
        etf_result = db.session.execute(db.text(f"""
            SELECT code, momentum_label, manager, listing_date, deviation_rate
            FROM etfs
            WHERE code IN ({placeholders})
        """), params)
        etf_data = etf_result.fetchall()

        # tags
        tag_params = {f'code_{i}': code for i, code in enumerate(etf_codes)}
        tag_placeholders = ', '.join([f':code_{i}' for i in range(len(etf_codes))])
        tag_result = db.session.execute(db.text(f"""
            SELECT etr.etf_code, t.name, t.category
            FROM etf_tag_relations etr
            JOIN tags t ON etr.tag_id = t.id
            WHERE etr.etf_code IN ({tag_placeholders})
        """), tag_params)
        tag_data = tag_result.fetchall()

        # price_histories（月次リターン用）
        price_params = {f'code_{i}': code for i, code in enumerate(etf_codes)}
        price_placeholders = ', '.join([f':code_{i}' for i in range(len(etf_codes))])
        price_result = db.session.execute(db.text(f"""
            SELECT etf_code, date, closing_price
            FROM price_histories
            WHERE etf_code IN ({price_placeholders})
            AND date >= date('now', '-13 months')
            ORDER BY etf_code, date
        """), price_params)
        price_data = price_result.fetchall()
except Exception as e:
    print(f"DB接続エラー: {e}（DBデータはスキップ）")

# 5. おすすめAPI
recommendations = {}
for perspective in ['balance', 'dividend', 'low-cost']:
    rec_resp = session.get(f'http://localhost:8902/api/v1/recommend/recommendations?perspective={perspective}')
    if rec_resp.status_code == 200:
        recommendations[perspective] = rec_resp.json()
    else:
        print(f"おすすめAPI取得エラー（{perspective}）: {rec_resp.status_code}（スキップ）")
        recommendations[perspective] = None

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
                compare_performance_list.append(compare_perf_resp.json())
            else:
                print(f"比較API（performance）エラー: {compare_perf_resp.status_code}（スキップ）")
                compare_performance_list.append(None)
            compare_score_resp = session.get(f'http://localhost:8902/api/v1/compare/scores?codes={compare_codes}')
            if compare_score_resp.status_code == 200:
                compare_scores_list.append(compare_score_resp.json())
            else:
                print(f"比較API（scores）エラー: {compare_score_resp.status_code}（スキップ）")
                compare_scores_list.append(None)

# データ保存
output = {
    'holdings': holdings,
    'summary': summary,
    'valuation_history': valuation_history,
    'performance_data': [dict(row._mapping) for row in performance_data] if performance_data else None,
    'score_data': [dict(row._mapping) for row in score_data] if score_data else None,
    'etf_data': [dict(row._mapping) for row in etf_data] if etf_data else None,
    'tag_data': [dict(row._mapping) for row in tag_data] if tag_data else None,
    'price_data': [dict(row._mapping) for row in price_data] if price_data else None,
    'recommendations': recommendations,
    'compare_performance': compare_performance_list if compare_performance_list else None,
    'compare_scores': compare_scores_list if compare_scores_list else None,
}

output_path = WORK_DIR / 'portfolio_data.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

# メインへの要約出力（この1行のみがメインのコンテキストに入る）
total_value = summary.get('total_valuation', 0) if summary else 0
print(f"データ収集完了: {len(etf_codes)}銘柄、総評価額{total_value:,.0f}円")
```
