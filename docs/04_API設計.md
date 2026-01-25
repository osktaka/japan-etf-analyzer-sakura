# API設計書

> **分割ファイル**
> - [04a_エンドポイント詳細.md](./04a_エンドポイント詳細.md) - 各APIの詳細仕様（リクエスト/レスポンス例）
> - [04b_実装サンプル.md](./04b_実装サンプル.md) - Flask/TypeScript実装例

## 1. 基本仕様

### 1.1 概要

| 項目 | 内容 |
|------|------|
| APIスタイル | RESTful |
| データ形式 | JSON |
| 文字コード | UTF-8 |
| 認証 | セッションベース認証（Flask-Login） |

### 1.2 ベースURL

| 環境 | ベースURL |
|------|-----------|
| 開発環境 | `http://localhost:8902/api/v1` |
| 本番環境 | `https://example.sakura.ne.jp/api/v1` |

### 1.3 APIバージョニング

- URLパス方式: `/api/v1/...`
- 将来の破壊的変更時は `/api/v2/...` を追加

## 2. 共通仕様

### 2.1 リクエストヘッダー

| ヘッダー | 必須 | 値 |
|----------|------|-----|
| Content-Type | Yes（POST/PUT時） | application/json |
| Accept | No | application/json |

### 2.2 レスポンス形式

#### 成功時

```json
{
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

#### エラー時

```json
{
  "error": {
    "code": "ERR_VALIDATION",
    "message": "検証エラーが発生しました",
    "details": {
      "field": "category_id",
      "reason": "無効なカテゴリIDです"
    }
  }
}
```

### 2.3 HTTPステータスコード

| コード | 意味 | 使用場面 |
|--------|------|----------|
| 200 | OK | 正常レスポンス |
| 400 | Bad Request | リクエスト不正 |
| 404 | Not Found | リソース未検出 |
| 500 | Internal Server Error | サーバー内部エラー |

### 2.4 ページネーション

クエリパラメータでページングを制御する。

| パラメータ | 型 | デフォルト | 説明 |
|------------|-----|------------|------|
| page | integer | 1 | ページ番号 |
| per_page | integer | 20 | 1ページあたりの件数（最大100） |

## 3. エンドポイント一覧

### 3.1 Phase 1（認証不要）

| メソッド | パス | 機能 | 対応機能ID |
|----------|------|------|------------|
| GET | /recommendations | おすすめ銘柄取得 | F-001 |
| GET | /perspectives | おすすめ観点一覧取得 | F-001 |
| GET | /etfs | ETF一覧・検索 | F-002 |
| GET | /etfs/{code} | ETF詳細取得 | F-003 |
| GET | /etfs/{code}/chart | チャートデータ取得 | F-004 |
| GET | /categories | カテゴリ一覧取得 | - |
| GET | /tags | タグ一覧取得 | - |

### 3.2 Phase 2（認証関連）

| メソッド | パス | 機能 | 対応機能ID | 認証 |
|----------|------|------|------------|------|
| POST | /auth/register | ユーザー登録 | F-101 | 不要 |
| POST | /auth/login | ログイン | F-101 | 不要 |
| POST | /auth/logout | ログアウト | F-101 | 必要 |
| GET | /auth/me | 現在のユーザー情報取得 | F-101 | 必要 |
| GET | /favorites | お気に入り一覧取得 | F-102 | 必要 |
| POST | /favorites | お気に入り追加 | F-102 | 必要 |
| DELETE | /favorites/{etf_code} | お気に入り削除 | F-102 | 必要 |
| GET | /favorites/codes | お気に入りETFコード一覧取得 | F-102 | 必要 |
| GET | /favorites/check/{etf_code} | お気に入り登録確認 | F-102 | 必要 |
| GET | /trades | 売買履歴一覧取得 | F-103 | 必要 |
| POST | /trades | 売買履歴登録 | F-103 | 必要 |
| GET | /trades/{id} | 売買履歴詳細取得 | F-103 | 必要 |
| PUT | /trades/{id} | 売買履歴更新 | F-103 | 必要 |
| DELETE | /trades/{id} | 売買履歴削除 | F-103 | 必要 |
| GET | /portfolio | ポートフォリオ概要取得 | F-105 | 必要 |
| GET | /portfolio/holdings | 保有銘柄一覧取得 | F-105 | 必要 |
| GET | /compare/performance | パフォーマンス比較取得 | F-107 | 不要 |
| GET | /compare/performance/{code} | 個別パフォーマンス取得 | F-107 | 不要 |

> 各エンドポイントの詳細仕様は [04a_エンドポイント詳細.md](./04a_エンドポイント詳細.md) を参照

## 4. エラーコード一覧

| コード | HTTPステータス | 説明 |
|--------|---------------|------|
| ERR_VALIDATION | 400 | バリデーションエラー |
| ERR_INVALID_PARAM | 400 | 無効なパラメータ |
| ERR_NOT_FOUND | 404 | リソース未検出 |
| ERR_EXTERNAL_API | 500 | 外部API（yfinance）エラー |
| ERR_INTERNAL | 500 | 内部エラー |

## 5. レート制限

### 5.1 Phase 1（個人利用）

| 制限 | 値 |
|------|-----|
| リクエスト制限 | なし |
| 同時接続数 | 制限なし |

### 5.2 将来（公開時）

| 制限 | 値 |
|------|-----|
| リクエスト制限 | 100リクエスト/分 |
| チャートAPI | 10リクエスト/分（外部API制約） |
