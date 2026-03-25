# japan-etf-analyzer-sakura

## プロジェクト概要

日本のETF銘柄を探して分析するWebアプリケーション。さくらレンタルサーバー スタンダード対応。

## ドキュメント導線

| 目的 | 参照先 | 備考 |
|------|--------|------|
| 要件定義を確認したい | docs/01_要件定義.md | MVP機能、Phase 2機能 |
| アーキテクチャを確認したい | docs/02_アーキテクチャ設計.md | システム構成図、技術スタック詳細 |
| DB設計を確認したい | docs/03_データベース設計.md | ER図、テーブル定義 |
| API仕様を確認したい | docs/04_API設計.md | 基本仕様・エンドポイント一覧 |
| APIの詳細仕様を確認したい | docs/04a_エンドポイント詳細.md | リクエスト/レスポンス例 |
| API実装例を確認したい | docs/04b_実装サンプル.md | Flask/TypeScript実装例 |
| 画面設計の概要を確認したい | docs/05_画面設計.md | 画面一覧、遷移図 |
| 画面・モーダル仕様を確認したい | docs/05a_画面仕様.md | 各画面の詳細、ワイヤーフレーム |
| UIスタイルガイドを確認したい | docs/05b_UIスタイルガイド.md | コンポーネント、カラー、A11y |
| インフラ設計を確認したい | docs/06_インフラ設計.md | Docker構成、さくらサーバー対応 |
| テスト設計を確認したい | docs/07_テスト設計.md | テスト戦略・方針・概要 |
| テストケース詳細を確認したい | docs/07a_テストケース詳細.md | 個別テスト実装例 |
| おすすめ銘柄の評価設計を確認したい | docs/08_おすすめ銘柄設計.md | 5軸評価・6切り口・重み付けモデル |
| タグ付けルールを確認したい | docs/09_タグ付けルール.md | 6カテゴリ49タグ、付与基準 |
| バッチ処理設計を確認したい | docs/10_バッチ処理設計.md | スケジュール、依存関係、障害時対応 |
| デモユーザーの取引分析をしたい | reports/demo/PROMPT.md | portfolio-analysis-v2スキルによる日次運用 |
| ポートフォリオ分析v2をしたい | .claude/skills/portfolio-analysis-v2/SKILL.md | /pf-v2（ブレインストーミング方式） |
| 今日の東証見通し・振り返り | .claude/skills/market-outlook/SKILL.md | /market-outlook（AM:朝の見通し / PM:夕方の振り返り） |
| 東証見通し・振り返り v2 | .claude/skills/market-outlook-v2/SKILL.md | /market-outlook-v2（データ自動取得+バリデーション） |
| 分析レポートをノート記事にしたい | .claude/skills/publish-report/SKILL.md | /publish-reportスキルで記事化 |
| X投稿文を自動生成したい | .claude/skills/market-x-draft/SKILL.md | /market-x-draft（market-outlook-v2レポートから3投稿生成） |
| X投稿を実行したい | .claude/skills/x-publish/SKILL.md | /x-publish（tmp_x_posts_v2.mdをXに投稿） |
| 日中マーケット観察を投稿したい | .claude/skills/market-intraday/SKILL.md | /market-intraday（東証取引中の軽量観察投稿） |
| ノート記事のネタを記録したい | .claude/note-ideas.md | 独立記事ネタの蓄積・管理 |

## 開発環境

```bash
# Docker環境起動
docker compose up -d

# コマンド一覧
make help
```

## 技術スタック

| レイヤー | 開発環境 | 本番環境 |
|----------|----------|----------|
| バックエンド | Flask (Python 3.9) | Flask (Python 3.9.18) |
| フロントエンド | React + Vite | ビルド済み静的ファイル |
| データベース | SQLite | SQLite 3.37.2 (2022-01-06) |
| 環境 | Docker Compose | さくらレンタルサーバー スタンダード |
| OS | Debian (Docker) | FreeBSD 13.0 |
| OpenSSL | - | 1.0.2-chacha（重要制約） |

## 本番環境固有の設定

| 項目 | 開発環境 | 本番環境 |
|------|---------|---------|
| データベースパス | backend/data/etf.db | ./data/etf.db |
| 作業ディレクトリ | /app (コンテナ内) | ~/www/japan-etf-analyzer |
| Pythonスクリプト実行 | `docker compose exec backend python scripts/xxx.py` | `cd ~/www/japan-etf-analyzer && source backend/venv/bin/activate && python backend/scripts/xxx.py` |

**重要**: 本番環境でPythonスクリプトを実行する際は、必ず以下の2点を守ること:
1. プロジェクトルート（~/www/japan-etf-analyzer）から実行（データベースパスが相対パスのため）
2. venvをアクティベート（`source backend/venv/bin/activate`）してから実行

## ポート番号

| サービス | ホスト | コンテナ | URL |
|---------|--------|---------|-----|
| Frontend | 3902 | 3902 | http://localhost:3902 |
| Backend | 8902 | 8902 | http://localhost:8902 |

## テストユーザー

| User ID | Password | Username | 備考 |
|---------|----------|----------|------|
| test | testpass123 | test | テスト用 |
| demo | （スクリプト内定義） | demo | デモ表示用（ログイン不要） |

## ディレクトリ構成

```
backend/
├── src/
│   ├── app.py          # Flaskアプリケーション
│   ├── routes/         # ルーティング
│   ├── services/       # ビジネスロジック
│   ├── models/         # データモデル
│   └── config/         # 設定
└── tests/              # テスト

frontend/
├── src/
│   ├── components/     # Reactコンポーネント
│   ├── pages/          # ページコンポーネント
│   ├── content/notes/  # ノート記事（Markdown + ローダー）
│   ├── api/            # APIクライアント
│   └── hooks/          # カスタムフック
└── public/             # 静的ファイル
```

## さくらレンタルサーバーへのデプロイ

### デプロイフロー

本番環境では以下の構成でデプロイ:

1. **ローカル**: frontend/src変更時、pre-commit hookで自動ビルド
2. **Git**: frontend/dist/をコミット・プッシュ（さくらサーバーにNode.js非インストール）
3. **本番**: `git pull` → `./setup.sh` で環境構築（シンボリックリンク自動作成）

```bash
# 初回セットアップ（開発環境）
./scripts/install-hooks.sh

# フロントエンド変更
# → git commitで自動ビルド・ステージング

# 本番デプロイ
ssh user@server
cd ~/www/japan-etf-analyzer
git pull
./setup.sh     # venv構築、シンボリックリンク作成（初回のみ）
./migrate.sh   # DBマイグレーション（スキーマ変更時）
# .envファイルを編集（初回のみ）
```

### frontend/dist/ のGit管理ポリシー

**重要**: frontend/dist/は.gitignoreで除外せず、Git管理に含める

**理由**:
- さくらレンタルサーバーにNode.jsインストール不可
- ビルド済みアセットをgit pullで配信
- pre-commit hookで自動ビルド → 手動ビルド忘れ防止

**運用ルール**:
- frontend/src変更時: hookが自動ビルド・ステージング
- dist/のみ変更時: コミット不要（hookで再生成される）
- hookインストール: `./scripts/install-hooks.sh` を実行

### CGI環境の技術的注意点

#### 1. PATH_INFO調整
CGI環境では、RewriteRule後のPATH_INFOがFlaskルート定義と一致しない問題があります。

- リクエスト: `/japan-etf-analyzer/api/v1/health`
- RewriteRule後: `/japan-etf-analyzer/api/index.cgi/v1/health`
- PATH_INFO: `/v1/health`（`/api`プレフィックスなし）
- Flaskルート: `/api/v1/health`（`/api`プレフィックスあり）

**解決策**: `api/index.cgi`でWSGI middlewareを使用し、PATH_INFOに`/api`を追加。

#### 2. .htaccessの無限リダイレクト対策
`RewriteRule ^api/(.*)$ api/index.cgi/$1`は、`api/index.cgi/v1/health`も再度マッチしてループします。

**解決策**: RewriteCondで`index.cgi`を除外。
```apache
RewriteCond %{REQUEST_URI} !index\.cgi
RewriteRule ^api/(.*)$ api/index.cgi/$1 [L,QSA]
```

#### 3. フロントエンドのシンボリックリンク
ApacheのDocumentRootから`frontend/dist/`内のファイルにアクセスするため、シンボリックリンクが必要。

- `index.html` → `frontend/dist/index.html`
- `assets/` → `frontend/dist/assets/`
- `robots.txt` → `frontend/dist/robots.txt`
- `sitemap.xml` → `frontend/dist/sitemap.xml`
- `notes/` → `frontend/dist/notes/`

`setup.sh`で自動作成されます。

#### 4. スクリプト作成時の環境変数設定

`backend/scripts/`にPythonスクリプトを作成する場合、**本番環境で直接実行できるよう環境変数を設定する必要がある**。

CGI（`api/index.cgi`）経由ではなくスクリプト直接実行時は、`APP_BASE_DIR`や`DATABASE_URL`が設定されないため、デフォルトの`/app`（Docker用）が使われてDBが見つからないエラーになる。

**必須テンプレート**（スクリプト冒頭に追加）:
```python
import os
import sys
from pathlib import Path

# プロジェクトルートを特定（backend/scripts/ → backend/ → project root）
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 環境変数設定（本番環境用）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

# この後に from src.app import create_app 等を記述
```

**参考実装**: `backend/scripts/seed_data.py`, `backend/scripts/auto_tag_etfs.py`

### 依存ライブラリのバージョン制約

#### OpenSSL 1.0.2互換性
FreeBSD 13.0のOpenSSL 1.0.2により、以下のバージョン制約が必要:
- `urllib3 < 2.0`: v2.0以降はOpenSSL 1.1.1+が必要
- `requests < 2.29.0`: urllib3 v2依存を避けるため

#### FreeBSDビルド制約
- `numpy==1.19.5`: メモリ消費が少なく、FreeBSD環境でビルド可能
- `pandas==1.3.5`: numpy 1.19.5との互換性
- `yfinance==0.1.63`: cryptography 2.x系と互換性あり
- `CRYPTOGRAPHY_DONT_BUILD_RUST=1`: setup.shで自動設定

**重要**: requirements.txtの変更後は必ずvenvを再構築:
```bash
rm -rf backend/venv && ./setup.sh
```

## 内部構造ガイド

### アーキテクチャパターン（詳細は02を参照）

- **バックエンド**: Repository-Service-Route の4層構造
- **フロントエンド**: Barrel Export パターン（index.ts）

### ファイルサイズ上限（実績）

| レイヤー | 最大行数 | 備考 |
|---------|---------|------|
| backend/routes/ | 128行 | favorite_routes.py |
| backend/services/ | 116行 | compare_service.py |
| backend/repositories/ | 135行 | etf_repository.py |
| frontend/components/ | 161行 | Header.tsx |

### API設計書セクション早見表

| ファイル | 内容 |
|---------|------|
| 04_API設計.md | 基本仕様・共通仕様・エンドポイント一覧 |
| 04a_エンドポイント詳細.md | 各APIの詳細仕様 |
| 04b_実装サンプル.md | Flask/TypeScript実装例 |

### 外部API

- Yahoo Finance: `backend/src/external/yahoo_finance.py` (106行)

## 株式分割の管理

このシステムでは株式分割を2つの独立したフラグで管理している:

### 1. `is_applied`: ポートフォリオ損益計算で分割を考慮するか
- **True**: 取引数量を分割比率で調整して計算（例: 2分割なら分割前購入分は数量×2）
- **SplitAdjustmentService**が取引日以降の適用済み分割を全て乗算

### 2. `is_chart_applied`: チャート表示で分割を考慮するか
- **True**: yfinanceのauto_adjust=Trueに加えて、追加の分割調整を適用
- **ChartService**が分割日前の価格データを分割比率で除算

### yfinanceとの関係
- yfinanceは`auto_adjust=True`で取得しているため、価格データは基本的に分割調整済み
- ただし、yfinanceの調整タイミングと実際の分割タイミングにズレがある場合がある
- `is_chart_applied`フラグで追加調整することで、このズレを吸収

### 重要な注意点
- DBの生の取引データ（tradesテーブル）は**分割前の元の数量・単価**で記録されている
- 正確な損益を見るには、PortfolioService（API）経由で取得する必要がある
- SQLiteの直接クエリでは分割が考慮されないため、損益計算が不正確になる
- 管理画面（Admin → Splits）で各ETFの分割フラグのオン/オフを制御可能

### 関連ファイル

| ファイル | 役割 |
|---------|------|
| backend/src/models/stock_split.py | 分割データモデル |
| backend/src/services/split_adjustment_service.py | 調整係数計算 |
| backend/src/services/portfolio_service.py | 分割考慮の損益計算 |
| backend/src/services/chart_service.py | チャート分割調整 |
| backend/src/external/yahoo_finance.py | yfinance取得（auto_adjust=True） |

## デモユーザー

デモユーザー（user_id='demo'）は未ログインユーザーにMyPageのプレビューを提供するための特殊ユーザー。

### デモデータの投入

```bash
# 開発環境
docker compose exec backend python scripts/seed_demo_data.py

# 本番環境
cd ~/www/japan-etf-analyzer
source backend/venv/bin/activate
python backend/scripts/seed_demo_data.py
```

- スクリプトは冪等（既存データがあれば削除して再作成）
- デモユーザーのパスワードはスクリプト内にハードコードされている（ログイン用途ではない）

### デモAPI

- パス: `/api/v1/demo/*`（全て認証不要・GET only）
- 実装: `backend/src/routes/demo_routes.py`
- デモユーザーが存在しない場合は空データを返す（エラーにならない）

## 運用ルール

開発中に以下を発見した場合、CLAUDE.mdへの追記を提案すること:
- 大規模ファイル（1000行超）の存在と部分読み込み推奨
- 繰り返し発生するパターンや注意点
- 特殊な命名規則やディレクトリ構造
- 外部API/サービスの制約事項

## DBスキーマ変更ルール

**重要**: データ消失を防ぐため、以下のルールを厳守すること

### マイグレーション実行（本番デプロイ時）

```bash
# 本番環境
ssh user@server
cd ~/www/japan-etf-analyzer
git pull
./migrate.sh  # バックアップ → マイグレーション → 結果表示
```

`migrate.sh` は以下を自動実行:
1. DBバックアップ（`data/backups/etf.db.backup_YYYYMMDD_HHMMSS`）
2. SQLマイグレーションファイル実行（`scripts/migrations/*.sql`）
3. Flaskモデル同期（新規テーブル作成）

### マイグレーションファイルの作成方法

新しいDBスキーマ変更が必要な場合、`scripts/migrations/` にSQLファイルを追加:

```bash
# 命名規則: 連番_説明.sql
scripts/migrations/001_create_user_settings.sql  # 既存
scripts/migrations/002_add_is_admin_to_users.sql # 新規追加例
```

**SQLファイル例（カラム追加）**:
```sql
-- Migration: 002_add_is_admin_to_users
-- Description: usersテーブルに管理者フラグを追加
-- Date: 2026-02-XX

ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0;
```

**ルール**:
- `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` を使用（冪等性確保）
- 番号は既存の最大値+1
- 実行済みマイグレーションは `migrations_applied` テーブルで管理され、再実行時はスキップ

### 禁止事項
- `db.drop_all()` の使用禁止（テスト環境を除く）
- テーブルの DROP & CREATE による再作成禁止
- 本番DBファイルの削除・上書き禁止
- マイグレーションファイルの番号重複

### データ復旧手順

マイグレーション失敗時:
```bash
# バックアップから復元
cp data/backups/etf.db.backup_YYYYMMDD_HHMMSS data/etf.db
```

マスターデータが消失した場合:
```bash
docker compose exec backend python scripts/seed_data.py
docker compose exec backend python scripts/sync_etf_from_jpx.py
```

## 外部リンク

| リンク | URL |
|--------|-----|
| 本番サイト | https://kima3.net/japan-etf-analyzer/ |
| X アカウント | https://x.com/ETF_Analyzer |
