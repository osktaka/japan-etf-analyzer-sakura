# API設計書

## 1. 基本仕様

### 1.1 概要

| 項目 | 内容 |
|------|------|
| APIスタイル | RESTful |
| データ形式 | JSON |
| 文字コード | UTF-8 |
| 認証 | なし（Phase 1） |

### 1.2 ベースURL

| 環境 | ベースURL |
|------|-----------|
| 開発環境 | `http://localhost:5000/api/v1` |
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

| メソッド | パス | 機能 | 対応機能ID |
|----------|------|------|------------|
| GET | /recommendations | おすすめ銘柄取得 | F-001 |
| GET | /perspectives | おすすめ観点一覧取得 | F-001 |
| GET | /etfs | ETF一覧・検索 | F-002 |
| GET | /etfs/{code} | ETF詳細取得 | F-003 |
| GET | /etfs/{code}/chart | チャートデータ取得 | F-004 |
| GET | /categories | カテゴリ一覧取得 | - |
| GET | /tags | タグ一覧取得 | - |

## 4. エンドポイント詳細

### 4.1 GET /recommendations - おすすめ銘柄取得

指定した観点（perspective）に基づくおすすめ銘柄を取得する。

#### クエリパラメータ

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|------|------|
| perspective | string | No | 観点ID（デフォルト: high-dividend） |
| limit | integer | No | 取得件数（デフォルト: 8、最大: 20） |

#### 指定可能な観点（perspective）

| 観点ID | 観点名 | 説明 | ソート基準 |
|--------|--------|------|-----------|
| high-dividend | 高配当 | 配当利回りが高い銘柄 | 配当利回り降順 |
| low-cost | 低コスト | 信託報酬が低い銘柄 | 信託報酬昇順 |
| domestic | 国内株式 | 日本株式に連動する銘柄 | 純資産降順 |
| foreign | 外国株式 | 海外株式に連動する銘柄 | 純資産降順 |
| emerging | 新興国 | 新興国に投資する銘柄 | 配当利回り降順 |
| esg | ESG | ESG投資関連の銘柄 | 純資産降順 |
| reit | REIT | 不動産関連の銘柄 | 配当利回り降順 |
| commodity | コモディティ | 金・原油等に連動する銘柄 | 出来高降順 |

#### リクエスト例

```
GET /api/v1/recommendations?perspective=high-dividend&limit=4
```

#### レスポンス

```json
{
  "data": {
    "perspective": {
      "id": "high-dividend",
      "name": "高配当",
      "description": "配当利回りが高く、安定した配当実績のある銘柄です"
    },
    "items": [
      {
        "code": "1489",
        "name": "NEXT FUNDS 日経平均高配当株50指数連動型上場投信",
        "category": {
          "id": 1,
          "name": "国内株式"
        },
        "tags": [
          { "id": 1, "name": "高配当", "color": "#EF4444" }
        ],
        "highlight_metric": {
          "label": "配当利回り",
          "value": 4.25,
          "unit": "%"
        },
        "expense_ratio": 0.28,
        "dividend_yield": 4.25,
        "market_price": 52800,
        "total_assets": 2850
      },
      {
        "code": "2564",
        "name": "グローバルX MSCIスーパーディビィデンド-日本株式 ETF",
        "highlight_metric": {
          "label": "配当利回り",
          "value": 3.82,
          "unit": "%"
        },
        ...
      }
    ]
  }
}
```

### 4.2 GET /perspectives - おすすめ観点一覧取得

利用可能なおすすめの観点一覧を取得する。

#### リクエスト例

```
GET /api/v1/perspectives
```

#### レスポンス

```json
{
  "data": [
    {
      "id": "high-dividend",
      "name": "高配当",
      "description": "配当利回りが高く、安定した配当実績のある銘柄です",
      "icon": "dividend"
    },
    {
      "id": "low-cost",
      "name": "低コスト",
      "description": "信託報酬が低く、長期保有に適した銘柄です",
      "icon": "cost"
    },
    {
      "id": "domestic",
      "name": "国内株式",
      "description": "日本の株式市場に連動する銘柄です",
      "icon": "japan"
    },
    {
      "id": "foreign",
      "name": "外国株式",
      "description": "海外の株式市場に連動する銘柄です",
      "icon": "global"
    },
    {
      "id": "emerging",
      "name": "新興国",
      "description": "新興国市場に投資する成長期待の銘柄です",
      "icon": "emerging"
    },
    {
      "id": "esg",
      "name": "ESG",
      "description": "環境・社会・ガバナンスに配慮した銘柄です",
      "icon": "leaf"
    },
    {
      "id": "reit",
      "name": "REIT",
      "description": "不動産投資信託に連動する銘柄です",
      "icon": "building"
    },
    {
      "id": "commodity",
      "name": "コモディティ",
      "description": "金・原油等の商品に連動する銘柄です",
      "icon": "commodity"
    }
  ]
}
```

### 4.3 GET /etfs - ETF一覧・検索

ETF銘柄を検索・絞り込み・一覧取得する。

#### リクエスト

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|------|------|
| q | string | No | 検索キーワード（コード、名前、説明） |
| category_id | integer | No | カテゴリIDでフィルタ |
| tag_ids | string | No | タグIDでフィルタ（カンマ区切り） |
| sort | string | No | ソート項目（code, name, dividend_yield, expense_ratio） |
| order | string | No | ソート順（asc, desc）デフォルト: asc |
| page | integer | No | ページ番号（デフォルト: 1） |
| per_page | integer | No | 1ページあたり件数（デフォルト: 20） |

#### リクエスト例

```
GET /api/v1/etfs?q=TOPIX&category_id=1&sort=dividend_yield&order=desc&page=1&per_page=10
```

#### レスポンス

```json
{
  "data": [
    {
      "code": "1306",
      "name": "NEXT FUNDS TOPIX連動型上場投信",
      "description": "TOPIXに連動する国内最大級のETF",
      "category": {
        "id": 1,
        "name": "国内株式"
      },
      "tags": [
        { "id": 3, "name": "TOPIX連動", "color": "#3B82F6" },
        { "id": 2, "name": "低コスト", "color": "#10B981" }
      ],
      "expense_ratio": 0.088,
      "dividend_yield": 2.15,
      "market_price": 2345.00,
      "total_assets": 187500,
      "updated_at": "2025-01-24T10:00:00Z"
    }
  ],
  "meta": {
    "total": 150,
    "page": 1,
    "per_page": 10,
    "total_pages": 15
  }
}
```

### 4.4 GET /etfs/{code} - ETF詳細取得

指定した銘柄コードのETF詳細情報を取得する。

#### パスパラメータ

| パラメータ | 型 | 説明 |
|------------|-----|------|
| code | string | 銘柄コード |

#### リクエスト例

```
GET /api/v1/etfs/1306
```

#### レスポンス

```json
{
  "data": {
    "code": "1306",
    "name": "NEXT FUNDS TOPIX連動型上場投信",
    "description": "TOPIXに連動する国内最大級のETF。東証一部上場銘柄全体の動きを表す指数に連動することを目指す。",
    "category": {
      "id": 1,
      "name": "国内株式"
    },
    "tags": [
      { "id": 3, "name": "TOPIX連動", "color": "#3B82F6" },
      { "id": 2, "name": "低コスト", "color": "#10B981" }
    ],
    "metrics": {
      "expense_ratio": 0.088,
      "dividend_yield": 2.15,
      "nav": 2340.50,
      "market_price": 2345.00,
      "deviation_rate": 0.19,
      "total_assets": 187500
    },
    "listing_date": "2001-07-13",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-24T10:00:00Z"
  }
}
```

#### エラーレスポンス（404）

```json
{
  "error": {
    "code": "ERR_NOT_FOUND",
    "message": "指定された銘柄が見つかりません",
    "details": {
      "code": "9999"
    }
  }
}
```

### 4.5 GET /etfs/{code}/chart - チャートデータ取得

指定した銘柄の価格チャートデータを取得する。

#### パスパラメータ

| パラメータ | 型 | 説明 |
|------------|-----|------|
| code | string | 銘柄コード |

#### クエリパラメータ

| パラメータ | 型 | 必須 | 説明 |
|------------|-----|------|------|
| periods | string | No | 取得期間（カンマ区切り） |

**periodsの指定可能値:**
- `1m`: 1ヶ月
- `3m`: 3ヶ月
- `6m`: 6ヶ月
- `1y`: 1年
- `3y`: 3年
- `5y`: 5年
- `10y`: 10年
- `all`: すべての期間（デフォルト）

#### リクエスト例

```
GET /api/v1/etfs/1306/chart?periods=1m,3m,1y
```

#### レスポンス

```json
{
  "data": {
    "code": "1306",
    "name": "NEXT FUNDS TOPIX連動型上場投信",
    "charts": {
      "1m": {
        "period": "1m",
        "start_date": "2024-12-24",
        "end_date": "2025-01-24",
        "data_points": [
          { "date": "2024-12-24", "close": 2280.00, "volume": 1500000 },
          { "date": "2024-12-25", "close": 2295.00, "volume": 1200000 },
          ...
        ],
        "performance": {
          "start_price": 2280.00,
          "end_price": 2345.00,
          "change": 65.00,
          "change_percent": 2.85
        }
      },
      "3m": {
        "period": "3m",
        "start_date": "2024-10-24",
        "end_date": "2025-01-24",
        "data_points": [ ... ],
        "performance": { ... }
      },
      "1y": {
        "period": "1y",
        "start_date": "2024-01-24",
        "end_date": "2025-01-24",
        "data_points": [ ... ],
        "performance": { ... }
      }
    }
  }
}
```

#### 注意事項

- yfinance経由でリアルタイム取得するため、レスポンスに時間がかかる場合がある
- データ取得に失敗した期間は、該当期間のデータに `error` フラグを含める

### 4.6 GET /categories - カテゴリ一覧取得

ETFカテゴリの一覧を取得する。

#### リクエスト例

```
GET /api/v1/categories
```

#### レスポンス

```json
{
  "data": [
    {
      "id": 1,
      "name": "国内株式",
      "description": "日本の株式市場に連動するETF",
      "etf_count": 45
    },
    {
      "id": 2,
      "name": "国内債券",
      "description": "日本の債券市場に連動するETF",
      "etf_count": 12
    },
    {
      "id": 3,
      "name": "外国株式",
      "description": "海外の株式市場に連動するETF",
      "etf_count": 38
    }
  ]
}
```

### 4.7 GET /tags - タグ一覧取得

ETFタグの一覧を取得する。

#### リクエスト例

```
GET /api/v1/tags
```

#### レスポンス

```json
{
  "data": [
    {
      "id": 1,
      "name": "高配当",
      "color": "#EF4444",
      "etf_count": 25
    },
    {
      "id": 2,
      "name": "低コスト",
      "color": "#10B981",
      "etf_count": 60
    },
    {
      "id": 3,
      "name": "TOPIX連動",
      "color": "#3B82F6",
      "etf_count": 15
    }
  ]
}
```

## 5. エラーコード一覧

| コード | HTTPステータス | 説明 |
|--------|---------------|------|
| ERR_VALIDATION | 400 | バリデーションエラー |
| ERR_INVALID_PARAM | 400 | 無効なパラメータ |
| ERR_NOT_FOUND | 404 | リソース未検出 |
| ERR_EXTERNAL_API | 500 | 外部API（yfinance）エラー |
| ERR_INTERNAL | 500 | 内部エラー |

## 6. レート制限

### 6.1 Phase 1（個人利用）

| 制限 | 値 |
|------|-----|
| リクエスト制限 | なし |
| 同時接続数 | 制限なし |

### 6.2 将来（公開時）

| 制限 | 値 |
|------|-----|
| リクエスト制限 | 100リクエスト/分 |
| チャートAPI | 10リクエスト/分（外部API制約） |

## 7. Flaskルーティング実装例

```python
# routes/recommend_routes.py
from flask import Blueprint, request, jsonify
from services.recommend_service import RecommendService

recommend_bp = Blueprint('recommend', __name__, url_prefix='/api/v1')

@recommend_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    """おすすめ銘柄取得"""
    perspective = request.args.get('perspective', 'high-dividend')
    limit = request.args.get('limit', 8, type=int)
    result = RecommendService.get_recommendations(perspective, limit)
    return jsonify({'data': result})

@recommend_bp.route('/perspectives', methods=['GET'])
def get_perspectives():
    """おすすめ観点一覧取得"""
    perspectives = RecommendService.get_perspectives()
    return jsonify({'data': perspectives})
```

```python
# routes/etf_routes.py
from flask import Blueprint, request, jsonify
from services.etf_service import ETFService
from utils.validators import validate_search_params

etf_bp = Blueprint('etf', __name__, url_prefix='/api/v1/etfs')

@etf_bp.route('', methods=['GET'])
def search_etfs():
    """ETF一覧・検索"""
    params = validate_search_params(request.args)
    result = ETFService.search(params)
    return jsonify({
        'data': result['items'],
        'meta': result['meta']
    })

@etf_bp.route('/<code>', methods=['GET'])
def get_etf_detail(code: str):
    """ETF詳細取得"""
    etf = ETFService.get_by_code(code)
    if not etf:
        return jsonify({
            'error': {
                'code': 'ERR_NOT_FOUND',
                'message': '指定された銘柄が見つかりません',
                'details': {'code': code}
            }
        }), 404
    return jsonify({'data': etf})

@etf_bp.route('/<code>/chart', methods=['GET'])
def get_etf_chart(code: str):
    """チャートデータ取得"""
    periods = request.args.get('periods', 'all')
    charts = ETFService.get_charts(code, periods.split(','))
    return jsonify({'data': charts})
```

## 8. フロントエンドAPIクライアント例

```typescript
// api/recommend.ts
import { apiClient } from './client';

export interface Perspective {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface RecommendationItem {
  code: string;
  name: string;
  category: { id: number; name: string };
  tags: { id: number; name: string; color: string }[];
  highlight_metric: { label: string; value: number; unit: string };
  expense_ratio: number;
  dividend_yield: number;
  market_price: number;
  total_assets: number;
}

export const recommendApi = {
  getRecommendations: async (perspective: string = 'high-dividend', limit: number = 8) => {
    const response = await apiClient.get('/recommendations', {
      params: { perspective, limit }
    });
    return response.data;
  },

  getPerspectives: async () => {
    const response = await apiClient.get('/perspectives');
    return response.data;
  }
};
```

```typescript
// api/etf.ts
import { apiClient } from './client';

export interface ETF {
  code: string;
  name: string;
  description: string;
  category: { id: number; name: string };
  tags: { id: number; name: string; color: string }[];
  expense_ratio: number;
  dividend_yield: number;
  market_price: number;
}

export interface SearchParams {
  q?: string;
  category_id?: number;
  tag_ids?: number[];
  sort?: string;
  order?: 'asc' | 'desc';
  page?: number;
  per_page?: number;
}

export const etfApi = {
  search: async (params: SearchParams) => {
    const response = await apiClient.get('/etfs', { params });
    return response.data;
  },

  getDetail: async (code: string) => {
    const response = await apiClient.get(`/etfs/${code}`);
    return response.data;
  },

  getChart: async (code: string, periods: string[]) => {
    const response = await apiClient.get(`/etfs/${code}/chart`, {
      params: { periods: periods.join(',') }
    });
    return response.data;
  }
};
```
