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

## `_metadata`セクションの出力（必須）

`portfolio_data.json` の先頭に `_metadata` キーを追加し、各データセクションのスキーマ情報を含めること。アナリストエージェントはこの `_metadata` を最初に読み、正しいフィールド名を確定してからスクリプトを書く。

**`_metadata`に含める情報（各データセクション）**:
- `count`: データ件数（`len(data)`）
- `columns`: 最初のレコードのキー一覧
- `sample`: 最初のレコードをそのまま出力
- セクション固有の情報（`perspectives`, `periods`等はユニーク値を抽出）

### `_data_status`セクション（必須）

`_metadata` に `_data_status` キーを追加し、全データソースの取得状態を記録すること。Phase 1アナリストはこの情報を使ってスキップ判断を行う。

**記録対象**: holdings, summary, valuation_history, performance_cache, score_cache, etf_data, tag_data, price_data, recommendations_balance, recommendations_dividend, recommendations_low-cost, compare_performance, compare_scores

**ステータス値**:
- `"ok"`: 正常取得（件数付き）
- `"empty"`: HTTP 200だがデータが空
- `"error"`: 取得失敗（エラー詳細付き）

**対象セクション**: `score_cache`, `performance_cache`, `price_data`, `etf_data`, `tag_data`, `etf_codes`, `_data_status`

**出力例**:
```json
{
  "_metadata": {
    "score_cache": {
      "count": 30,
      "perspectives": ["balance", "dividend", "low-cost", "stability", "volume", "growth"],
      "axes": ["dividend_power", "cost_efficiency", "scale_reliability", "trading_quality", "return_performance"],
      "columns": ["etf_code", "perspective", "total_score", "dividend_power", "cost_efficiency", "scale_reliability", "trading_quality", "return_performance"],
      "sample": { "etf_code": "1475", "perspective": "balance", "total_score": 76.4 }
    },
    "performance_cache": {
      "count": 40,
      "periods": ["1m", "3m", "6m", "1y", "3y", "5y", "10y", "20y"],
      "columns": ["etf_code", "period", "return_rate", "volatility", "regression_rate"],
      "sample": { "etf_code": "1475", "period": "1y", "return_rate": 0.4014 }
    },
    "price_data": {
      "count": 65,
      "columns": ["etf_code", "date", "close"]
    },
    "etf_data": {
      "count": 5,
      "columns": ["code", "momentum_label", "manager", "listing_date", "deviation_rate"]
    },
    "tag_data": {
      "count": 25,
      "columns": ["etf_code", "name", "category"]
    },
    "etf_codes": ["1475", "1329", "1615", "1489", "1597"],
    "_data_status": {
      "holdings": {"status": "ok", "count": 5},
      "summary": {"status": "ok", "count": 1},
      "valuation_history": {"status": "empty", "detail": "レスポンス200だが中身が空"},
      "performance_cache": {"status": "ok", "count": 40},
      "score_cache": {"status": "ok", "count": 30},
      "etf_data": {"status": "ok", "count": 5},
      "tag_data": {"status": "ok", "count": 25},
      "price_data": {"status": "ok", "count": 65},
      "recommendations_balance": {"status": "ok", "count": 10},
      "recommendations_dividend": {"status": "ok", "count": 10},
      "recommendations_low-cost": {"status": "error", "http_status": 500, "error": "Internal Server Error"},
      "compare_performance": {"status": "ok", "count": 1},
      "compare_scores": {"status": "ok", "count": 1}
    }
  },
  "holdings": { ... },
  ...
}
```

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
etf_codes = [h['etf_code'] for h in holdings['data']]
record_status('holdings', data=holdings.get('data', []))
print(f"保有銘柄数: {len(etf_codes)}")

# 2. サマリー取得
summary_resp = session.get('http://localhost:8902/api/v1/portfolio')
summary = summary_resp.json() if summary_resp.status_code == 200 else None
record_status('summary', resp=summary_resp, data=summary.get('data') if summary else None)
if summary is None:
    print(f"サマリー取得エラー: {summary_resp.status_code}（スキップ）")

# 3. 資産推移取得
valuation_resp = session.get('http://localhost:8902/api/v1/portfolio/valuation-history?period=3y')
valuation_history = valuation_resp.json() if valuation_resp.status_code == 200 else None
record_status('valuation_history', resp=valuation_resp, data=valuation_history.get('data', []) if valuation_history else None)
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
        try:
            perf_result = db.session.execute(db.text(f"""
                SELECT etf_code, period, return_rate, volatility, regression_rate
                FROM performance_cache
                WHERE etf_code IN ({placeholders})
            """), params)
            performance_data = perf_result.fetchall()
            record_status('performance_cache', data=performance_data)
        except Exception as e:
            print(f"performance_cache取得エラー: {e}")
            record_status('performance_cache', error=e)

        # score_cache
        try:
            score_result = db.session.execute(db.text(f"""
                SELECT etf_code, perspective, total_score,
                       dividend_power, cost_efficiency, scale_reliability, trading_quality, return_performance
                FROM score_cache
                WHERE etf_code IN ({placeholders})
            """), params)
            score_data = score_result.fetchall()
            record_status('score_cache', data=score_data)
        except Exception as e:
            print(f"score_cache取得エラー: {e}")
            record_status('score_cache', error=e)

        # etfs
        try:
            etf_result = db.session.execute(db.text(f"""
                SELECT code, momentum_label, manager, listing_date, deviation_rate
                FROM etfs
                WHERE code IN ({placeholders})
            """), params)
            etf_data = etf_result.fetchall()
            record_status('etf_data', data=etf_data)
        except Exception as e:
            print(f"etf_data取得エラー: {e}")
            record_status('etf_data', error=e)

        # tags
        try:
            tag_params = {f'code_{i}': code for i, code in enumerate(etf_codes)}
            tag_placeholders = ', '.join([f':code_{i}' for i in range(len(etf_codes))])
            tag_result = db.session.execute(db.text(f"""
                SELECT etr.etf_code, t.name, t.category
                FROM etf_tag_relations etr
                JOIN tags t ON etr.tag_id = t.id
                WHERE etr.etf_code IN ({tag_placeholders})
            """), tag_params)
            tag_data = tag_result.fetchall()
            record_status('tag_data', data=tag_data)
        except Exception as e:
            print(f"tag_data取得エラー: {e}")
            record_status('tag_data', error=e)

        # price_histories（月次リターン用）
        try:
            price_params = {f'code_{i}': code for i, code in enumerate(etf_codes)}
            price_placeholders = ', '.join([f':code_{i}' for i in range(len(etf_codes))])
            price_result = db.session.execute(db.text(f"""
                SELECT etf_code, date, close
                FROM price_histories
                WHERE etf_code IN ({price_placeholders})
                AND date >= date('now', '-13 months')
                ORDER BY etf_code, date
            """), price_params)
            price_data = price_result.fetchall()
            record_status('price_data', data=price_data)
        except Exception as e:
            print(f"price_data取得エラー: {e}")
            record_status('price_data', error=e)
except Exception as e:
    print(f"DB接続エラー: {e}（DBデータはスキップ）")
    for name in ['performance_cache', 'score_cache', 'etf_data', 'tag_data', 'price_data']:
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

# _metadata生成（アナリストがフィールド名を正確に把握するため）
def build_metadata(data, extra_info=None):
    if not data:
        return {"count": 0, "columns": [], "sample": None}
    first = data[0] if isinstance(data, list) else data
    first_dict = dict(first._mapping) if hasattr(first, '_mapping') else first
    meta = {"count": len(data), "columns": list(first_dict.keys()), "sample": {k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v for k, v in first_dict.items()}}
    if extra_info:
        meta.update(extra_info)
    return meta

_metadata = {
    "score_cache": build_metadata(score_data, {
        "perspectives": sorted(set(dict(r._mapping)['perspective'] for r in score_data)) if score_data else [],
        "axes": ["dividend_power", "cost_efficiency", "scale_reliability", "trading_quality", "return_performance"]
    }),
    "performance_cache": build_metadata(performance_data, {
        "periods": sorted(set(dict(r._mapping)['period'] for r in performance_data)) if performance_data else []
    }),
    "price_data": build_metadata(price_data),
    "etf_data": build_metadata(etf_data),
    "tag_data": build_metadata(tag_data),
    "etf_codes": etf_codes,
    "_data_status": data_status
}

# データ保存
output = {
    '_metadata': _metadata,
    'holdings': holdings,
    'summary': summary,
    'valuation_history': valuation_history,
    'performance_cache': [dict(row._mapping) for row in performance_data] if performance_data else None,
    'score_cache': [dict(row._mapping) for row in score_data] if score_data else None,
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
summary_data = summary.get('data', {}) if summary else {}
total_value = summary_data.get('total_value', 0)
print(f"データ収集完了: {len(etf_codes)}銘柄、総評価額{total_value:,.0f}円")
```
