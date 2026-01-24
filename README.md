# Japan ETF Analyzer (Sakura Edition)

日本のETF銘柄を探して分析するWebアプリケーション。

## セットアップ

### 前提条件

- Docker & Docker Compose
- Git

### インストール

```bash
# リポジトリのクローン
git clone <repository-url>
cd japan-etf-analyzer-sakura

# 環境変数の設定
cp .env.example .env

# Docker環境の起動
docker compose up -d
```

## 開発

```bash
# コマンド一覧
make help

# 環境起動
make up

# ログ確認
make logs

# リント
make lint

# テスト
make test
```

## アクセス

| サービス | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:5000 |

## 技術スタック

- **Frontend**: React + TypeScript + Vite
- **Backend**: Flask + Python 3.8
- **Database**: MySQL 8.x
- **Container**: Docker Compose

## ドキュメント

詳細は `docs/` ディレクトリを参照してください。

- [要件定義](./docs/01_要件定義.md)
