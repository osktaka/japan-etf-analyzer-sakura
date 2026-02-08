# UIスタイルガイド

本ドキュメントはUI実装における共通定義を定める。
全体構成については [05_画面設計.md](./05_画面設計.md) を参照。

---

## 1. コンポーネント設計

### 1.1 コンポーネント一覧

```
components/
├── common/
│   ├── Header.tsx           # ヘッダー
│   ├── Footer.tsx           # フッター
│   ├── Loading.tsx          # ローディングスピナー
│   ├── ErrorMessage.tsx     # エラー表示
│   ├── Pagination.tsx       # ページネーション
│   ├── Modal.tsx            # 汎用モーダル
│   └── Toast.tsx            # トースト通知
├── recommend/
│   ├── RecommendSection.tsx # おすすめセクション
│   ├── PerspectiveTabs.tsx  # 観点タブ
│   ├── RecommendCard.tsx    # おすすめカード
│   └── RecommendList.tsx    # おすすめ一覧
├── search/
│   ├── SearchSection.tsx    # 検索セクション
│   ├── SearchBar.tsx        # 検索バー
│   ├── FilterPanel.tsx      # フィルターパネル
│   ├── CategorySelect.tsx   # カテゴリドロップダウン
│   ├── TagFilter.tsx        # タグフィルター
│   ├── SortSelect.tsx       # ソート選択
│   └── SearchResults.tsx    # 検索結果コンテナ
├── etf/
│   ├── ETFCard.tsx          # ETFカード（一覧用）
│   ├── ETFDetailModal.tsx   # 銘柄詳細モーダル
│   ├── ETFHeader.tsx        # 詳細ヘッダー
│   ├── ETFInfo.tsx          # 基本情報セクション
│   ├── MetricTable.tsx      # 指標テーブル
│   ├── TagBadge.tsx         # タグバッジ
│   ├── FavoriteButton.tsx   # お気に入りボタン
│   └── CompareButton.tsx    # 比較追加ボタン
├── compare/
│   ├── ComparePage.tsx      # 比較画面
│   ├── CompareList.tsx      # 比較対象リスト
│   ├── ETFSearchInput.tsx   # 銘柄検索入力（インクリメンタルサーチ）
│   ├── CompareChart.tsx     # 比較チャート
│   └── CompareTable.tsx     # 指標比較テーブル
└── chart/
    ├── ChartContainer.tsx   # チャートコンテナ
    ├── PeriodSelector.tsx   # 期間選択
    ├── PriceChart.tsx       # 価格チャート
    ├── PerformanceBadge.tsx # パフォーマンス表示
    └── MomentumBadge.tsx   # 勢いバッジ（モメンタムラベル）
```

### 1.2 主要コンポーネント仕様

#### RecommendSection（おすすめセクション）

```typescript
interface RecommendSectionProps {
  perspectives: Perspective[];
  activePerspective: string;
  onPerspectiveChange: (id: string) => void;
  recommendations: ETFSummary[];
  onCardClick: (code: string) => void;
  onMoreClick: () => void;
}

interface Perspective {
  id: string;
  name: string;
  description: string;
}
```

#### FavoriteButton（お気に入りボタン）

```typescript
interface FavoriteButtonProps {
  code: string;
  size?: 'sm' | 'md' | 'lg';
  onLoginPrompt: () => void;  // Phase 1: ログイン促進モーダルを表示
}
```

#### CompareButton（比較追加ボタン）

```typescript
interface CompareButtonProps {
  code: string;
  isInCompareList: boolean;
  onToggle: (code: string) => void;
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;  // 上限到達時
}
```

#### ETFCard（一覧用カード）

```typescript
interface ETFCardProps {
  etf: {
    code: string;
    name: string;
    category: { id: number; name: string };
    tags: { id: number; name: string; color: string }[];
    dividend_yield: number;
    expense_ratio: number;
    market_price: number;
  };
  isInCompareList: boolean;
  onCompareToggle: (code: string) => void;
  onFavoriteClick: () => void;  // Phase 1: ログイン促進モーダル表示
  onClick: (code: string) => void;
  compareDisabled?: boolean;    // 比較リスト上限到達時
}
```

#### Modal（汎用モーダル）

```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  children: React.ReactNode;
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
}
```

### 1.3 カスタムフック

```typescript
// hooks/useFavorites.ts (Phase 2で実装)
interface UseFavoritesReturn {
  favorites: string[];
  isFavorite: (code: string) => boolean;
  addFavorite: (code: string) => void;
  removeFavorite: (code: string) => void;
  toggleFavorite: (code: string) => void;
  count: number;
}

// hooks/useCompareList.ts (Phase 1で実装)
interface UseCompareListReturn {
  compareList: string[];           // 比較リストのコード配列
  isInCompareList: (code: string) => boolean;
  addToCompare: (code: string) => void;
  removeFromCompare: (code: string) => void;
  toggleCompare: (code: string) => void;
  clearCompareList: () => void;
  count: number;
  isAtLimit: boolean;              // 上限（10件）到達フラグ
}

// hooks/useRecommendations.ts
interface UseRecommendationsReturn {
  recommendations: ETFSummary[];
  isLoading: boolean;
  error: Error | null;
  perspective: string;
  setPerspective: (id: string) => void;
}
```

---

## 2. スタイルガイド

### 2.1 カラーパレット

| 用途 | 変数名 | 値 |
|------|--------|-----|
| プライマリ | --color-primary | #3B82F6 |
| プライマリホバー | --color-primary-hover | #2563EB |
| セカンダリ | --color-secondary | #6B7280 |
| 成功 | --color-success | #10B981 |
| 警告 | --color-warning | #F59E0B |
| エラー | --color-error | #EF4444 |
| お気に入り | --color-favorite | #FBBF24 |
| 背景 | --color-bg | #F9FAFB |
| 背景白 | --color-bg-white | #FFFFFF |
| テキスト | --color-text | #111827 |
| テキスト薄 | --color-text-muted | #6B7280 |
| ボーダー | --color-border | #E5E7EB |
| オーバーレイ | --color-overlay | rgba(0, 0, 0, 0.5) |

#### モメンタムカラー

勢いバッジ（MomentumBadge）で使用する8色。インラインスタイルで `color` / `backgroundColor` を動的に設定する。枠線: `border: 1px solid currentColor`。維持判定の閾値: 比率ベース判定（ratio = |1M年率| / |3M年率|）で RATIO_UPPER=1.45 超なら「加速」、RATIO_LOWER=0.55 未満なら「減速」、0.55〜1.45なら「維持」。

| ラベル | カラーコード | 説明 |
|--------|-------------|------|
| 上昇加速 | #059669 | 濃い緑 |
| 上昇維持 | #10b981 | 緑 |
| 上昇減速 | #6ee7b7 | 薄い緑 |
| 反転上昇 | #2563eb | 青 |
| 失速 | #f59e0b | 黄 |
| 下降減速 | #fca5a5 | 薄い赤 |
| 下降維持 | #ef4444 | 赤 |
| 下降加速 | #dc2626 | 濃い赤 |

### 2.2 タイポグラフィ

| 用途 | サイズ | ウェイト |
|------|--------|---------|
| H1（ページタイトル） | 24px | 700 |
| H2（セクション） | 20px | 600 |
| H3（カード名） | 16px | 600 |
| 本文 | 14px | 400 |
| 補足 | 12px | 400 |

### 2.3 スペーシング

| 名前 | 値 |
|------|-----|
| xs | 4px |
| sm | 8px |
| md | 16px |
| lg | 24px |
| xl | 32px |
| 2xl | 48px |

### 2.4 シャドウ

| 名前 | 用途 | 値 |
|------|------|-----|
| sm | カード | 0 1px 2px rgba(0,0,0,0.05) |
| md | ホバー | 0 4px 6px rgba(0,0,0,0.1) |
| lg | ドロップダウン | 0 10px 15px rgba(0,0,0,0.1) |
| xl | モーダル | 0 25px 50px rgba(0,0,0,0.25) |

### 2.5 角丸

| 名前 | 値 |
|------|-----|
| sm | 4px |
| md | 8px |
| lg | 12px |
| xl | 16px |
| full | 9999px |

### 2.6 Z-index

| 用途 | 値 |
|------|-----|
| ドロップダウン | 10 |
| ヘッダー（固定時） | 50 |
| オーバーレイ | 100 |
| モーダル | 110 |
| トースト通知 | 200 |

---

## 3. インタラクション

### 3.1 ホバー状態

- カード: 影が強くなる + 微小な上移動
- ボタン: 背景色が濃くなる
- リンク: 下線表示
- お気に入りボタン: 背景が薄く表示

### 3.2 フォーカス状態

- 入力フィールド: プライマリカラーの輪郭線
- ボタン: プライマリカラーの輪郭線
- モーダル内要素: フォーカストラップ適用

### 3.3 ローディング

- 全体: 中央にスピナー
- 部分: スケルトンスクリーン
- モーダル内: モーダル中央にスピナー

### 3.4 トランジション

| 対象 | 時間 | イージング |
|------|------|----------|
| ホバー | 150ms | ease-in-out |
| モーダル表示 | 200ms | ease-out |
| モーダル非表示 | 150ms | ease-in |
| オーバーレイ | 200ms | ease |
| お気に入り登録 | 300ms | ease-out |

### 3.5 お気に入りアニメーション

```css
/* お気に入り登録時 */
@keyframes favorite-pop {
  0% { transform: scale(1); }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); }
}

.favorite-button.active {
  animation: favorite-pop 300ms ease-out;
}
```

---

## 4. アクセシビリティ

### 4.1 キーボード操作

| キー | アクション |
|------|-----------|
| Tab | フォーカス移動 |
| Enter | 選択/決定 |
| Space | お気に入りトグル |
| Escape | モーダルを閉じる |
| ↑↓ | リスト内移動 |
| ←→ | 観点タブ移動 |

### 4.2 モーダルのアクセシビリティ

| 項目 | 実装 |
|------|------|
| フォーカストラップ | モーダル内でTabがループ |
| 初期フォーカス | 閉じるボタンに自動フォーカス |
| aria-modal | true |
| role | dialog |
| aria-labelledby | モーダルタイトルを参照 |
| 背景スクロール | モーダル表示中は無効化 |

### 4.3 スクリーンリーダー対応

- 適切なセマンティックHTML使用
- aria-label属性の付与
- お気に入りボタン: 「お気に入りに追加」「お気に入りから削除」
- 画像にalt属性
- モーダル開閉時のアナウンス

### 4.4 コントラスト比

- テキスト: 最低4.5:1（WCAG AA準拠）
- 大きいテキスト: 最低3:1
