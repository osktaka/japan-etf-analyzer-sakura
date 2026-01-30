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

## 開発環境

```bash
# Docker環境起動
docker compose up -d

# コマンド一覧
make help
```

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| バックエンド | Flask (Python 3.8) |
| フロントエンド | React + Vite |
| データベース | SQLite |
| 開発環境 | Docker Compose |
| 本番環境 | さくらレンタルサーバー スタンダード |

## ポート番号

| サービス | ホスト | コンテナ | URL |
|---------|--------|---------|-----|
| Frontend | 3902 | 3902 | http://localhost:3902 |
| Backend | 8902 | 8902 | http://localhost:8902 |

## テストユーザー

| Email | Password | Username |
|-------|----------|----------|
| test@example.com | testpass123 | test |

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
│   ├── api/            # APIクライアント
│   └── hooks/          # カスタムフック
└── public/             # 静的ファイル
```

## さくらレンタルサーバーへのデプロイ

### デプロイフロー

本番環境では以下の構成でデプロイ:

1. **ローカル**: frontend/src変更時、pre-commit hookで自動ビルド
2. **Git**: frontend/dist/をコミット・プッシュ（さくらサーバーにNode.js非インストール）
3. **本番**: `git pull` → `./setup.sh` で環境構築

```bash
# 初回セットアップ（開発環境）
./scripts/install-hooks.sh

# フロントエンド変更
# → git commitで自動ビルド・ステージング

# 本番デプロイ
ssh user@server
cd ~/www/japan-etf-analyzer
git pull
./setup.sh
# .envファイルを編集
# DBを初期化（初回のみ）
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

## 運用ルール

開発中に以下を発見した場合、CLAUDE.mdへの追記を提案すること:
- 大規模ファイル（1000行超）の存在と部分読み込み推奨
- 繰り返し発生するパターンや注意点
- 特殊な命名規則やディレクトリ構造
- 外部API/サービスの制約事項

## DBスキーマ変更ルール

**重要**: データ消失を防ぐため、以下のルールを厳守すること

### 変更前の必須手順
1. **バックアップ取得**: `docker compose exec backend cp /app/data/etf.db /app/data/etf.db.backup`
2. **現状確認**: 変更対象テーブルのレコード数を確認

### カラム追加
- `ALTER TABLE` を使用し、テーブル再作成を避ける
- SQLite例: `ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0`

### 禁止事項
- `db.drop_all()` の使用禁止（テスト環境を除く）
- テーブルの DROP & CREATE による再作成禁止
- 本番DBファイルの削除・上書き禁止

### データ復旧手順
マスターデータが消失した場合:
```bash
docker compose exec backend python scripts/seed_data.py
docker compose exec backend python scripts/sync_etf_master.py
```
