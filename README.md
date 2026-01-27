# Japan ETF Analyzer (Sakura Edition)

日本のETF銘柄を探して分析するWebアプリケーション。

## 開発環境のセットアップ

### 前提条件

- Docker & Docker Compose
- Git
- ポート 3902, 8902 が利用可能

### インストール手順

```bash
# 1. リポジトリのクローン
git clone <repository-url>
cd japan-etf-analyzer-sakura

# 2. 環境変数の設定
cp .env.example .env

# 3. Docker環境の起動
docker compose up -d
```

### 動作確認

環境が正常に起動したら、以下のURLでアクセスできます。

| サービス | URL |
|---------|-----|
| Frontend | http://localhost:3902 |
| Backend API | http://localhost:8902 |

### よくあるトラブルシューティング

**ポート競合**
```bash
# ポートが使用中の場合、使用しているプロセスを確認
lsof -i :3902
lsof -i :8902
```

**Docker daemonが起動していない**
```bash
# Docker daemonの状態を確認
docker info
```

**コンテナが正常に起動しない**
```bash
# ログを確認
docker compose logs -f
```

### 次のステップ

```bash
# 利用可能なコマンド一覧を確認
make help
```

## 開発コマンド

```bash
# 環境起動
make up

# ログ確認
make logs

# リント
make lint

# テスト
make test
```

## 技術スタック

- **Frontend**: React + TypeScript + Vite
- **Backend**: Flask + Python 3.8
- **Database**: SQLite
- **Container**: Docker Compose

## ドキュメント

詳細は `docs/` ディレクトリを参照してください。

- [要件定義](./docs/01_要件定義.md)
