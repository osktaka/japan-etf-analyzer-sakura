# ETF タグ付けスキル

```yaml
---
name: etf-tag
description: ETF銘柄の分析とタグ付け
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, WebSearch, WebFetch, Edit
aliases: ["/etf-tag"]
---
```

## 概要

このスキルは、ETF銘柄を分析し適切なタグを付与するワークフローを提供する。
6カテゴリ43タグから適切なタグを選択し、`etf_tags_data.py`にマッピングを追加する。

## タグカテゴリ一覧

| カテゴリ | タグ数 | タグ例 |
|----------|--------|--------|
| 業種(sector) | 9 | 金融, テクノロジー, ヘルスケア, エネルギー, 素材, 消費, 機械・製造, 通信, 公益 |
| テーマ(theme) | 12 | AI・半導体, EV・自動運転, クリーンエネルギー, DX, 高配当, ESG, 小型株, バリュー, グロース, インデックス, レバレッジ, インバース |
| 地域(region) | 8 | 国内, 米国, 先進国, 新興国, 全世界, アジア, ヨーロッパ, 中国 |
| 資産(asset) | 4 | 株式, 債券, REIT, コモディティ |
| 経済情勢(economic) | 7 | 円安, 円高, 金利上昇, 金利低下, インフレヘッジ, 景気敏感, ディフェンシブ |
| 政策(policy) | 3 | 防衛関連, インフラ, 半導体政策 |

## 実行手順

### Step 1: タグなし銘柄の抽出

DBからタグが付いていない銘柄を抽出する。

```bash
docker compose exec backend python -c "
from pathlib import Path
import sys
sys.path.insert(0, '/app')
from src.app import create_app
from src.models import db

app = create_app()
with app.app_context():
    result = db.session.execute(db.text('''
        SELECT e.code, e.name, c.name as category
        FROM etfs e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.code NOT IN (SELECT DISTINCT etf_code FROM etf_tag_relations)
        ORDER BY e.code
    '''))
    rows = result.fetchall()
    print(f'タグなし銘柄: {len(rows)}件')
    for code, name, category in rows:
        print(f'{code}: {name} [{category}]')
"
```

### Step 2: 銘柄分析

以下の観点で銘柄を分析する。

#### 2.1 銘柄名からの判断

| キーワード | 付与タグ |
|-----------|---------|
| TOPIX, 日経225 | インデックス, 国内, 株式 |
| S&P500 | インデックス, 米国, 株式 |
| 高配当 | 高配当 |
| 為替ヘッジあり | 円高 |
| 為替ヘッジなし | 円安 |
| レバレッジ, 2倍, ブル | レバレッジ（スキップ対象） |
| インバース, ベア, ダブルインバース | インバース（スキップ対象） |

#### 2.2 連動指数からの判断

- 連動する指数の構成銘柄の業種
- 指数の選定基準（配当重視、ESG重視等）
- 対象地域・市場

#### 2.3 Web調査（必要に応じて）

銘柄名・連動指数から判断できない場合、以下を調査:

- 運用会社サイト（目論見書、ファクトシート）
- JPX（東京証券取引所）
- Yahoo Finance Japan

### Step 3: タグ付けルール確認

`docs/09_タグ付けルール.md`を参照し、付与基準を確認する。

**必須ルール:**
1. 各銘柄に最低2つ以上のタグを付与
2. 地域タグと資産クラスタグは原則付与
3. 該当するテーマ・業種・経済情勢タグを適宜付与
4. レバレッジ/インバース銘柄はスキップ（マッピングに追加しない）

### Step 4: ETF_TAG_MAPPINGへの追加コード生成

`backend/scripts/etf_tags_data.py`の`ETF_TAG_MAPPING`に追加するコードを生成する。

```python
# 追加コード例
ETF_TAG_MAPPING = {
    # 既存のマッピング...

    # ===== 新規追加 =====
    "XXXX": ["地域", "資産", "テーマ"],  # 銘柄名
}
```

### Step 5: DB反映

マッピング追加後、以下のコマンドでDBに反映する。

```bash
# 開発環境
docker compose exec backend python scripts/auto_tag_etfs.py

# 本番環境
cd ~/www/japan-etf-analyzer && python backend/scripts/auto_tag_etfs.py
```

## 分析観点チェックリスト

### 地域判断

- [ ] 日本国内の資産? → `国内`
- [ ] 米国市場? → `米国`
- [ ] 先進国全般（除く日本含む）? → `先進国`
- [ ] 新興国市場? → `新興国`
- [ ] グローバル分散? → `全世界`
- [ ] アジア地域（インド、東南アジア等）? → `アジア`
- [ ] 欧州市場? → `ヨーロッパ`
- [ ] 中国市場（本土、香港）? → `中国`

### 資産クラス判断

- [ ] 株式? → `株式`
- [ ] 国債・社債等? → `債券`
- [ ] 不動産投資信託? → `REIT`
- [ ] 金・原油等の商品? → `コモディティ`

### テーマ・業種判断

- [ ] 高配当戦略? → `高配当`
- [ ] ESG関連? → `ESG`
- [ ] AI・半導体関連? → `AI・半導体`
- [ ] EV・自動運転関連? → `EV・自動運転`
- [ ] クリーンエネルギー関連? → `クリーンエネルギー`
- [ ] DX関連? → `DX`
- [ ] 小型株? → `小型株`
- [ ] バリュー投資? → `バリュー`
- [ ] グロース投資? → `グロース`
- [ ] 市場全体指数? → `インデックス`

### 経済情勢判断

- [ ] 為替ヘッジなし外貨建て? → `円安`
- [ ] 為替ヘッジあり? → `円高`
- [ ] 金利上昇で恩恵（銀行等）? → `金利上昇`
- [ ] 金利低下で恩恵（REIT、長期債券等）? → `金利低下`
- [ ] インフレ時に価値維持（金、REIT等）? → `インフレヘッジ`
- [ ] 景気変動の影響大? → `景気敏感`
- [ ] 景気変動の影響小? → `ディフェンシブ`

### 政策判断

- [ ] 防衛・安全保障関連? → `防衛関連`
- [ ] 社会インフラ・建設関連? → `インフラ`
- [ ] 半導体産業政策関連? → `半導体政策`

## 出力形式例

### 実行結果出力

```
=== ETFタグ付け分析結果 ===

## タグなし銘柄一覧
| コード | 銘柄名 | カテゴリ |
|--------|--------|----------|
| 123A | XXX ETF | 国内株式 |
| 456A | YYY ETF | 外国株式 |

## 分析結果

### 123A: XXX ETF
- カテゴリ: 国内株式
- 連動指数: TOPIX
- 付与タグ: 国内, 株式, インデックス, 景気敏感

### 456A: YYY ETF
- カテゴリ: 外国株式
- 連動指数: S&P500
- 付与タグ: 米国, 株式, インデックス, 円安

## 追加コード

以下を `backend/scripts/etf_tags_data.py` の ETF_TAG_MAPPING に追加してください:

\`\`\`python
    # ===== 新規追加（YYYY-MM-DD） =====
    "123A": ["国内", "株式", "インデックス", "景気敏感"],  # XXX ETF
    "456A": ["米国", "株式", "インデックス", "円安"],  # YYY ETF
\`\`\`

## 反映コマンド

\`\`\`bash
docker compose exec backend python scripts/auto_tag_etfs.py
\`\`\`
```

## スキップ対象

以下のキーワードを含む銘柄はタグ付けをスキップする:

- ブル（ただし「ブルームバーグ」「ブルサ」は除外対象外）
- レバレッジ
- 2倍
- ベア
- インバース
- ダブル

これらはリスクが高く、一般投資家向けではないため。

## 関連ファイル

| ファイル | 役割 |
|----------|------|
| `docs/09_タグ付けルール.md` | タグ付与基準の詳細 |
| `backend/scripts/etf_tags_data.py` | ETFコード→タグ名のマッピング定義 |
| `backend/scripts/auto_tag_etfs.py` | 自動タグ付け実行スクリプト |
| `backend/scripts/seed_data.py` | タグ・カテゴリのマスターデータ定義 |

## 完了条件

- [ ] タグなし銘柄を全て確認した
- [ ] 各銘柄に2つ以上のタグを付与した
- [ ] 地域タグと資産クラスタグを付与した
- [ ] レバレッジ/インバース銘柄をスキップした
- [ ] `etf_tags_data.py`にマッピングを追加した
- [ ] `auto_tag_etfs.py`を実行してDBに反映した
- [ ] エラーが発生していないことを確認した
