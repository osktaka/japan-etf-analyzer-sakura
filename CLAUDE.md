# japan-etf-analyzer-sakura

## プロジェクト概要

日本のETF銘柄を探して分析するWebアプリケーション。さくらレンタルサーバー スタンダード対応。

## ドキュメント導線

| 目的 | 参照先 |
|------|--------|
| 要件定義を確認したい | docs/01_要件定義.md |

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

| サービス | ホスト | コンテナ |
|---------|--------|---------|
| Frontend | 3000 | 3000 |
| Backend | 5000 | 5000 |

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

本番環境では以下の構成でデプロイ:

1. **フロントエンド**: Reactをビルドし、静的ファイルとして配置
2. **バックエンド**: Flask + CGI/FastCGI

```bash
# フロントエンドビルド
cd frontend && npm run build

# ビルド結果を転送
scp -r dist/* user@server:/home/user/www/
```

## 運用ルール

開発中に以下を発見した場合、CLAUDE.mdへの追記を提案すること:
- 大規模ファイル（1000行超）の存在と部分読み込み推奨
- 繰り返し発生するパターンや注意点
- 特殊な命名規則やディレクトリ構造
- 外部API/サービスの制約事項
