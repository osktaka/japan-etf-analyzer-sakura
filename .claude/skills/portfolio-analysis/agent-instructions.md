# ポートフォリオ定量分析 - エージェント詳細指示

> このファイルは `SKILL.md` から参照される詳細情報です。
> 各Phaseの実行手順、計算方法、出力形式など、サブエージェントに渡す具体的な指示を記載しています。
>
> 前提情報:
> - データソース一覧・スキップ判断基準・株式分割の注意事項・APIアクセス方法は `SKILL.md` を参照
> - 作業ディレクトリ（WORK_DIR）の仕様は `SKILL.md` の「コンテキスト管理ルール」セクションを参照
> - 統合レポートの出力形式テンプレートは `report-template.md` を参照

---

## Phase 0a: 市場環境調査

### 収集手順

1. WebSearchで以下のキーワードを検索（3回程度に分けて並行実行）
   - 「日本 ETF 市場 最新動向」
   - 「日経平均 為替 金利 最新」
   - 「米国株 経済指標 最新」
2. 必要に応じてWebFetchで詳細情報を取得
3. 取得した情報を以下の形式でまとめる

### まとめ形式

- 主要指標（日経平均、TOPIX、ドル円、米10年債利回り）の直近値
- 最近の政治経済トピックを箇条書き5-10項目
- 分析への示唆（市場環境が保有銘柄に与える影響）
  - 例: 円安傾向なら外貨建て資産の評価額が上振れ、為替リスクにも注意
  - 例: 金利上昇局面なら債券ETFの価格下落リスク、金融セクターには追い風
  - 例: 地政学リスク高まりならディフェンシブ銘柄・ゴールドの評価を上方修正

### 収集結果の保存先

`{WORK_DIR}/market_environment.md` に保存する。Phase 1の各エージェントがこのファイルを直接読み込む。

**メインへの戻り値**: 「市場環境調査完了」の1行のみ。サマリー全文を返さないこと。

---

## Phase 0: データ収集

### データ収集スクリプト例

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
                          json={'user_id': 'test', 'password': 'testpass123'})
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

---

## Phase 1: 並行分析

TeamCreateでチームを作成し、以下の3名を並行起動する。

### エージェント1: quant-analyst（定量リスク・リターン分析）

**入力ファイル**:
- `{WORK_DIR}/portfolio_data.json` - 全収集データ
- `{WORK_DIR}/market_environment.md` - 市場環境サマリー

**出力ファイル**: `{WORK_DIR}/quant_analysis.md`

**メインへの戻り値**: 「quant-analyst分析完了」の1行のみ。分析結果全文を返さないこと。

**役割**: シャープレシオ、相関分析、最大ドローダウン、ストレスシナリオの計算

**共通指示**: Phase 0aで収集した市場環境サマリー（`{WORK_DIR}/market_environment.md`）の情報も分析の判断材料に含めること。特に金利動向、為替トレンド、地政学リスクがリスク・リターン評価に影響する場合は明示的に言及すること。

**分析項目**:

#### A. シャープレシオ分析
各銘柄の (1年リターン - 0.5%) / ボラティリティ を算出、ランキング作成。

**計算式**:
```
シャープレシオ = (年率リターン - リスクフリーレート) / 年率ボラティリティ
リスクフリーレート = 0.5%（日本国債10年利回りの近似）
```

**出力形式**:
| 銘柄コード | 銘柄名 | 1年リターン | ボラティリティ | シャープレシオ | ランク |
|-----------|--------|------------|--------------|--------------|--------|

#### B. 相関分析
月次リターン（月次変化率）から主要銘柄間の相関係数を推定。高相関ペア（>0.7）と低相関ペア（<0.3）を特定。

**計算方法**:
1. 月初価格から月次リターンを計算: `(P_n - P_{n-1}) / P_{n-1}`
2. 銘柄ペアごとにピアソン相関係数を計算
3. 高相関ペア（>0.7）と低相関ペア（<0.3）をリストアップ

**月初価格の抽出方法**:
- 各月の最初の取引日（各月で最も早いdateの行）のclosing_priceを月初価格とする
- SQLクエリでは全日次データを取得し、Python側で各月の最初のレコードを抽出

**出力形式**:
```
高相関ペア（リスク集中）:
- 1234 と 5678: 0.85（ともに米国テック）
- 9012 と 3456: 0.78（ともに国内高配当）

低相関ペア（分散効果あり）:
- 1234 と 7890: 0.12（米国テック vs 新興国債券）
- 5678 と 2345: -0.05（ゴールド vs 株式）
```

#### C. 最大ドローダウン
資産推移データからピーク→ボトムを特定。回復期間も算出。

**計算方法**:
1. 資産評価額の累積最大値を計算
2. 各時点のドローダウン = (累積最大値 - 現在値) / 累積最大値
3. 最大ドローダウン = max(ドローダウン)
4. 回復期間 = ボトムから累積最大値を更新するまでの日数

**出力形式**:
```
最大ドローダウン: -18.5%
発生期間: 2025-03-15（ピーク）→ 2025-06-20（ボトム）
回復期間: 95日（2025-09-23に回復）
```

#### D. ストレスシナリオ
最悪月次リターンを再現。テック-20%時のポートフォリオ影響を試算。

**シナリオ例**:
- シナリオ1: 米国テック-20%
- シナリオ2: 全世界株式-15%
- シナリオ3: 円高進行（USD/JPY 130→110、ヘッジなし外貨建て資産-15%）

**出力形式**:
| シナリオ | 対象銘柄 | 評価額変化 | ポートフォリオ影響 |
|---------|---------|-----------|-------------------|
| 米国テック-20% | 1234, 5678 | -45万円 | -8.2% |
| 全世界株式-15% | 全銘柄 | -82万円 | -15.0% |
| 円高進行 | 9012, 3456 | -28万円 | -5.1% |

#### E. リスク調整後ランキング
全銘柄をシャープレシオ順にランク付け。非効率銘柄（ハイリスク・ローリターン）を特定。

**出力形式**:
| ランク | 銘柄コード | 銘柄名 | シャープレシオ | 判定 |
|-------|-----------|--------|--------------|------|
| 1 | 1234 | ABC ETF | 1.25 | 優秀 |
| 2 | 5678 | XYZ ETF | 0.95 | 良好 |
| ... | ... | ... | ... | ... |
| 8 | 9012 | DEF ETF | 0.15 | 非効率（見直し推奨） |

---

### エージェント2: score-analyst（スコア・モメンタム分析）

**入力ファイル**:
- `{WORK_DIR}/portfolio_data.json` - 全収集データ
- `{WORK_DIR}/market_environment.md` - 市場環境サマリー

**出力ファイル**: `{WORK_DIR}/score_analysis.md`

**メインへの戻り値**: 「score-analyst分析完了」の1行のみ。分析結果全文を返さないこと。

**役割**: 5軸スコア分析、モメンタム分析、代替銘柄提案

**共通指示**: Phase 0aで収集した市場環境サマリー（`{WORK_DIR}/market_environment.md`）の情報も分析の判断材料に含めること。特に市場テーマ（AI・半導体ブーム、高配当人気等）やセクターローテーションの動向がスコア評価・代替銘柄選定に影響する場合は明示的に言及すること。

**分析項目**:

#### A. 加重平均スコア
保有比率で加重した5軸別・6視点別のポートフォリオスコア。弱い軸を特定。

**計算式**:
```
ポートフォリオスコア（軸X、視点Y） = Σ(銘柄iのスコア × 銘柄iの保有比率)
```

**出力形式**:
| 視点 | 配当力 | コスト効率 | 規模信頼性 | 売買品質 | リターン |
|------|-------|-----------|-----------|---------|---------|
| バランス | 72 | 65 | 88 | 75 | 58 |
| 高配当 | 85 | 60 | 80 | 70 | 50 |
| 低コスト | 70 | 90 | 85 | 78 | 60 |

**弱い軸の特定**:
- リターンスコアが全視点で低い（50-60）→ 高リターン銘柄の追加を検討
- コスト効率がバランス視点で低い（65）→ 低コスト銘柄への入れ替えを検討

#### B. モメンタム分析
失速/上昇中の銘柄のグルーピング。失速銘柄の合計比率と影響度。

**分類基準（momentum_label）**:
- 上昇加速: 勢いが強まっている
- 上昇中: 安定的に上昇
- 横ばい: 明確なトレンドなし
- 下降中: 下落トレンド
- 下降加速: 下落が加速

**出力形式**:
```
モメンタム分布:
- 上昇加速: 2銘柄（保有比率25%）
- 上昇中: 3銘柄（保有比率35%）
- 横ばい: 1銘柄（保有比率10%）
- 下降中: 2銘柄（保有比率30%）← 要注意

下降中銘柄の詳細:
- 9012 DEF ETF（20%）: 3ヶ月で-8.5%
- 3456 GHI ETF（10%）: 3ヶ月で-5.2%
```

#### C. 低スコア銘柄の深掘り
各銘柄の弱い軸を特定、改善可能性を評価。

**分析方法**:
1. 各銘柄の5軸スコアを取得（バランス視点）
2. 平均スコア未満の軸を抽出
3. 同一カテゴリの高スコア銘柄と比較

**出力形式**:
```
低スコア銘柄: 9012 DEF ETF

弱い軸:
- コスト効率: 45点（平均65点）
  → 信託報酬0.55%（カテゴリ平均0.35%）
- リターン: 38点（平均58点）
  → 1年リターン2.5%（カテゴリ平均8.2%）

改善可能性:
- 同一カテゴリの代替候補（1357 国内株式ETF）:
  - コスト効率: 85点（信託報酬0.15%）
  - リターン: 72点（1年リターン9.8%）
  - 入れ替えでポートフォリオスコア +12点
```

#### D. 代替銘柄提案
おすすめAPIの結果と比較し、低スコア銘柄の代替候補を提案。スコア改善シミュレーション。

**提案フォーマット**:
```
入れ替え提案:

1. 9012 DEF ETF → 1357 国内株式ETF
   - スコア改善: +12点（58→70）
   - コスト削減: 年間約2,000円（信託報酬差）
   - リターン改善期待: +7.3%ポイント

2. 3456 GHI ETF → 2558 海外株式ETF
   - スコア改善: +8点（62→70)
   - 相関低下: 0.85→0.45（分散効果向上）
   - リスク調整後リターン改善
```

#### E. 運用会社集中リスク
manager別の銘柄数・評価額比率。

**出力形式**:
| 運用会社 | 銘柄数 | 評価額 | 比率 | 判定 |
|---------|-------|--------|------|------|
| 野村アセットマネジメント | 3 | 250万円 | 45% | 高リスク |
| 三菱UFJ国際投信 | 2 | 150万円 | 27% | 中リスク |
| その他 | 3 | 150万円 | 28% | - |

**推奨**: 単一運用会社の比率が40%超の場合、分散を検討。

#### F. タグベース分散度
地域/セクター/経済環境タグの分布評価。

**出力形式**:
```
地域分散:
- 国内: 40%
- 米国: 35%
- 先進国: 15%
- 新興国: 10%
評価: 良好（4地域に分散）

セクター分散:
- テクノロジー: 50%（集中リスク）
- 金融: 20%
- ヘルスケア: 15%
- その他: 15%
評価: テクノロジーへの過度な集中

経済環境:
- 円安: 55%（為替ヘッジなし外貨建て）
- 円高: 5%（為替ヘッジあり）
- 中立: 40%
評価: 円安に偏り（円高時のダウンサイドリスク大）
```

---

### エージェント3: allocation-analyst（アセットアロケーション分析）

**入力ファイル**:
- `{WORK_DIR}/portfolio_data.json` - 全収集データ
- `{WORK_DIR}/market_environment.md` - 市場環境サマリー

**出力ファイル**: `{WORK_DIR}/allocation_analysis.md`

**メインへの戻り値**: 「allocation-analyst分析完了」の1行のみ。分析結果全文を返さないこと。

**役割**: 地域・セクター・テーマ別の配分分析、欠落アセットクラスの特定

**共通指示**: Phase 0aで収集した市場環境サマリー（`{WORK_DIR}/market_environment.md`）の情報も分析の判断材料に含めること。特に為替動向（円安/円高）が地域配分の評価に、政策動向（金融緩和/引き締め）がアセットクラス推奨に影響する場合は明示的に言及すること。

**分析項目**:

#### A. 地域別配分
タグ情報から地域別の評価額・比率を算出。

**出力形式**:
| 地域 | 評価額 | 比率 | 推奨比率 | 判定 |
|------|-------|------|---------|------|
| 国内 | 220万円 | 40% | 30-50% | 適正 |
| 米国 | 195万円 | 35% | 30-40% | 適正 |
| 先進国 | 83万円 | 15% | 10-20% | 適正 |
| 新興国 | 55万円 | 10% | 5-15% | 適正 |

#### B. セクター別配分
タグ情報からセクター別の評価額・比率を算出。

**出力形式**:
| セクター | 評価額 | 比率 | 判定 |
|---------|-------|------|------|
| テクノロジー | 275万円 | 50% | 過度な集中 |
| 金融 | 110万円 | 20% | 適正 |
| ヘルスケア | 83万円 | 15% | 適正 |
| その他 | 83万円 | 15% | - |

**推奨**: テクノロジーの比率を40%以下に抑制。

#### C. テーマ別配分
タグ情報からテーマ別の評価額・比率を算出。

**出力形式**:
| テーマ | 評価額 | 比率 |
|-------|-------|------|
| AI・半導体 | 165万円 | 30% |
| 高配当 | 110万円 | 20% |
| インデックス | 83万円 | 15% |
| ESG | 55万円 | 10% |
| その他 | 140万円 | 25% |

#### D. 欠落アセットクラス
資産クラスタグから未保有の資産を特定。

**出力形式**:
```
保有資産クラス:
- 株式: 95%
- REIT: 5%

欠落資産クラス:
- 債券: 0%（推奨: 10-20%、安定性向上）
- コモディティ: 0%（推奨: 5-10%、インフレヘッジ）

推奨銘柄例:
- 債券: 2621（iShares 米国債20年）
- コモディティ: 1540（金価格連動型ETF）
```

#### E. 現金比率の妥当性評価
cash_flowsテーブルから現金残高を算出、適正比率と比較。

**計算式**:
```
現金残高 = Σ(入金額) - Σ(出金額) - Σ(取引額)
現金比率 = 現金残高 / (評価額 + 現金残高)
```

**出力形式**:
```
現金残高: 50万円
現金比率: 8.3%（推奨: 5-10%）
判定: 適正
```

#### F. 集中度ヒートマップ
地域×セクターのマトリクスで集中度を可視化。

**出力形式（テキスト表現）**:
```
地域×セクター集中度:

        テック  金融  ヘルスケア  その他
国内      5%   15%      5%      15%
米国     35%    5%      5%       5%
先進国   10%    -       5%        -
新興国    -     -        -       10%

リスク集中: 米国×テック（35%）← 要注意
```

**注意**: 銘柄数が少なくスコープが軽い場合、allocation-analystはquant-analystまたはscore-analystに統合可。

---

## Phase 2: クロスレビュー

Phase 1の結果を各エージェントに送り、相手の分析をレビューさせる。

### quant-analyst → score-analyst の結果をレビュー

**レビュー観点**:

1. **スコア評価と定量指標（シャープレシオ）に矛盾はないか**
   - 例: スコア高いがシャープレシオ低い銘柄 → 品質は高いがリターン/リスクが悪い
   - 例: スコア低いがシャープレシオ高い銘柄 → コスト・配当は劣るが効率的

2. **代替銘柄提案は定量的に合理的か**
   - 提案銘柄のシャープレシオを確認
   - 相関係数を確認（入れ替えで分散効果が改善するか）

3. **失速銘柄のリスクはボラティリティデータと整合的か**
   - 失速銘柄のボラティリティが高い場合、リスク増大を警告
   - ボラティリティが低い場合、一時的な調整の可能性

**出力形式**:
```
=== quant-analystによるスコア分析レビュー ===

1. スコアとシャープレシオの整合性:
   - 9012 DEF ETF: スコア58点（低）、シャープレシオ0.15（非効率）
     → 一致: 品質・効率ともに劣る。入れ替え推奨。
   - 1234 ABC ETF: スコア65点（中）、シャープレシオ1.25（優秀）
     → 乖離: スコアは平均的だがリスク調整後リターンは優秀。
       コスト・配当は劣るが効率的。保有継続推奨。

2. 代替銘柄提案の検証:
   - 提案: 9012 → 1357
     - 1357のシャープレシオ: 0.95（良好）
     - 相関係数: 0.65（中程度）
     - 評価: 定量的に合理的。入れ替え支持。

3. 失速銘柄のリスク評価:
   - 9012 DEF ETF: 下降中、ボラティリティ18%（高）
     → リスク増大。早期の入れ替えを推奨。
   - 3456 GHI ETF: 下降中、ボラティリティ8%（低）
     → 一時的な調整の可能性。1-2ヶ月様子見も選択肢。
```

### score-analyst → quant-analyst の結果をレビュー

**レビュー観点**:

1. **シャープレシオとスコアの乖離がある銘柄の解釈**
   - スコア低いがシャープ高い → 品質vs効率のトレードオフ
   - スコア高いがシャープ低い → 高品質だが市場環境に合わない

2. **相関分析はタグ分類と整合的か**
   - 高相関ペアは同一地域/セクターか
   - 低相関ペアは異なる地域/セクターか

3. **定量分析で見落としているスコア上の問題はないか**
   - シャープレシオは高いが、信託報酬が高い
   - シャープレシオは高いが、純資産が小さい（流動性リスク）

**出力形式**:
```
=== score-analystによる定量分析レビュー ===

1. シャープレシオとスコアの乖離分析:
   - 1234 ABC ETF: スコア65点、シャープ1.25
     → 解釈: コスト効率45点（信託報酬0.55%）が足を引っ張るが、
       リターンスコア85点（1年リターン12.5%）で挽回。
       短期的には保有継続、長期的には低コスト銘柄への入れ替え検討。

2. 相関分析とタグ分類の整合性:
   - 高相関ペア（1234 と 5678、相関0.85）
     → タグ: ともに「米国」「テクノロジー」→ 整合的
   - 低相関ペア（1234 と 7890、相関0.12）
     → タグ: 1234「米国・テック」、7890「新興国・債券」→ 整合的

3. 見落としリスク:
   - 5678 XYZ ETF: シャープ0.95（良好）だが、
     - 純資産50億円（規模信頼性スコア55点、小規模）
     - 流動性リスクあり。大口売却時にスリッページの可能性。
     → 推奨: 純資産100億円以上の銘柄への入れ替えを検討。
```

---

## 議論重視モード: 独立分析の指示

### 各エージェント共通指示

**入力ファイル（全エージェント共通）**:
- `{WORK_DIR}/portfolio_data.json` - 全収集データ
- `{WORK_DIR}/market_environment.md` - 市場環境サマリー

**出力ファイル**:
- analyst-A: `{WORK_DIR}/analyst_a_analysis.md`
- analyst-B: `{WORK_DIR}/analyst_b_analysis.md`
- analyst-C: `{WORK_DIR}/analyst_c_analysis.md`

**メインへの戻り値**: 「{analyst名}分析完了」の1行のみ。

議論重視モードでは、各エージェント（analyst-A, analyst-B, analyst-C）が**同じデータセット**を受け取り、独立に全項目を分析する。

**分析項目**（全エージェント共通）:
1. シャープレシオ分析・リスク調整後ランキング
2. 相関分析
3. 最大ドローダウン
4. ストレスシナリオ
5. 加重平均スコア・弱い軸の特定
6. モメンタム分析
7. 低スコア銘柄の深掘り・代替銘柄提案
8. 運用会社集中リスク
9. タグベース分散度
10. 地域・セクター・テーマ別配分
11. 欠落アセットクラスの特定
12. 現金比率の妥当性評価

**出力要件**:
- 各分析項目の結果に加え、**総合判断**を必ず記載する
- 総合判断には以下を含める:
  - 最も改善効果の高いアクション（トップ3）
  - 最大のリスク要因（トップ3）
  - ポートフォリオの総合評価（100点満点）
- 他のエージェントと事前に相談せず、独立した判断を下すこと

各分析項目の計算方法・出力形式は、上記の Phase 1 各エージェントの詳細指示（quant-analyst, score-analyst, allocation-analyst）を参照。

---

## Phase 2: クロスレビュー（議論重視モード）

議論重視モードでは、クロスレビューを2ラウンド実施する。

### 第1ラウンド: 相互レビュー

各エージェントが他のエージェントの分析結果を受け取り、以下の観点でレビュー:

1. **見解の相違点**: 自分の分析と異なる結論がある箇所を指摘
2. **見落としの指摘**: 相手が見落としているリスクや機会を指摘
3. **データ解釈の妥当性**: 相手のデータ解釈が正しいか検証
4. **総合判断の優先順位**: アクション優先度の違いとその理由

**出力形式**:
```
=== analyst-X による analyst-Y の分析レビュー ===

1. 見解の相違:
   - [具体的な相違点と自分の根拠]

2. 見落としの指摘:
   - [相手が見落としている点]

3. 同意する点:
   - [相手の分析で優れている点]

4. 総合判断の比較:
   - 自分のトップ3アクション vs 相手のトップ3アクション
   - 相違の理由
```

### 第2ラウンド: 反論・合意形成

第1ラウンドのレビュー結果を受けて、各エージェントが反論または同意を表明。

**出力形式**:
```
=== analyst-X の第2ラウンド回答 ===

1. 受け入れる指摘:
   - [指摘内容と修正後の見解]

2. 反論する指摘:
   - [指摘内容と反論の根拠]

3. 修正後の総合判断:
   - 最も改善効果の高いアクション（トップ3）
   - 合意度: [各アクションについて合意/部分合意/不合意]
```

### 合意形成ルール

- **全エージェント合意**: そのアクションを「合意度100%」としてレポートに記載
- **過半数合意**: 「合意度XX%」として記載。反対意見も併記
- **全エージェント不合意**: 各見解を併記し、ユーザーに判断を委ねる

---

## Phase 3+4: 統合レポート作成・保存

### 統合エージェントの役割

統合エージェント（general-purpose）は、`{WORK_DIR}` 配下の全分析結果ファイルを読み込み、`report-template.md` のテンプレートに従ってレポートを作成・保存する。

### 入力ファイル

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/market_environment.md` | 市場環境サマリー |
| `{WORK_DIR}/portfolio_data.json` | 全収集データ |
| `{WORK_DIR}/quant_analysis.md` | 定量リスク・リターン分析結果 |
| `{WORK_DIR}/score_analysis.md` | スコア・モメンタム分析結果 |
| `{WORK_DIR}/allocation_analysis.md` | アセットアロケーション分析結果（存在する場合） |
| `{WORK_DIR}/timing.json` | 各フェーズの実行時間記録 |
| `{skill_dir}/report-template.md` | レポート出力形式テンプレート |

議論重視モードの場合:

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/analyst_a_analysis.md` | analyst-A分析結果 |
| `{WORK_DIR}/analyst_b_analysis.md` | analyst-B分析結果 |
| `{WORK_DIR}/analyst_c_analysis.md` | analyst-C分析結果（存在する場合） |

### クロスレビュー（統合エージェント内で実施）

**速度重視モード**: スキップ。セクション9に「速度重視モードのためスキップ」と記載。

**ノーマルモード**: 以下の観点で分析結果間の矛盾・整合性を検証し、セクション9に記載:

1. **スコアとシャープレシオの乖離**: スコア高/シャープ低、またはその逆のケースを特定し、解釈を記載
2. **代替銘柄提案の定量的妥当性**: 提案銘柄のシャープレシオ・相関係数を確認
3. **失速銘柄のリスク整合性**: モメンタムとボラティリティの整合性を確認
4. **相関分析とタグ分類の整合性**: 高相関ペアが同一地域/セクターか確認
5. **スコア上の見落としリスク**: シャープは高いが信託報酬が高い、純資産が小さい等

**議論重視モード**: 各独立分析者（analyst-A/B/C）の見解の相違・合意点を特定し、セクション9に議論の経緯を詳細に記載:
- 見解の相違点とその根拠
- 合意された点
- 各アクションの合意度（100%/過半数/不合意）

### 出力

1. レポートファイル: `./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`
2. **メインへの戻り値**: 「レポート保存完了: ./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md」の1行のみ

### レポート作成手順

1. `{WORK_DIR}/` 配下の全ファイルを読み込む
2. `{skill_dir}/report-template.md` を読み込む
3. テンプレートに従い、各セクションを実データで埋める
4. クロスレビュー（該当モードの場合）を実施し、セクション9に記載
5. `{WORK_DIR}/timing.json` を読み込み、Phase 3+4の開始時刻（phase_3_start）と完了時刻（phase_3_end, skill_end）を自身で記録した上で、所要時間を計算し「実行時間」セクション（セクション14）に記載する
6. `./reports/` ディレクトリを作成（存在しない場合）
7. レポートを保存
8. メインに保存先パスのみ返す

**実行時間の計算方法**:
- 各フェーズの所要時間 = end - start（秒単位で計算し、X分XX秒で表示）
- Phase 0a+0 合計 = max(phase_0a_end, phase_0_end) - min(phase_0a_start, phase_0_start)（並行実行のため）
- 合計 = skill_end - skill_start
- phase_3_start: timing.jsonを読み込んだ直後に現在時刻を記録
- phase_3_end / skill_end: レポート保存直前に現在時刻を記録
