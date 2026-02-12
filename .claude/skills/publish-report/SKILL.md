---
name: publish-report
description: ポートフォリオ分析レポートをノート記事に変換・公開
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Bash, AskUserQuestion
aliases: ["/publish-report", "/pub-report"]
---

## 概要

- `/portfolio-analysis` スキルの出力レポート（600行超）を、一般読者向けの1500-2000字のノート記事に変換
- 記事は `frontend/src/content/notes/` に配置（Viteのimport.meta.globで自動認識）

## 使用方法

```
/publish-report                 # 最新のdemoレポートを自動検出して記事化
/publish-report [レポートパス]   # 指定レポートを記事化
```

## 記事トーン

- 丁寧語ベース（です・ます調）
- 専門用語には簡潔な補足を添える
- データを示した後に視点を提示する形
- 投資判断は読者に委ねる（推奨・助言にならない表現）
- 「〇〇すべき」「〇〇が有望」のような断定は避ける

## 実行フロー（4Phase）

### Phase 1 - 素材収集（Read only）

1. Globで `reports/*_portfolio_analysis_demo.md` を検索し、引数指定がなければ最新を使用
2. レポート全文をReadで読み込む（重点セクション: エグゼクティブサマリー、市場環境、シャープレシオ、モメンタム、アロケーション、最適化提案）
3. `reports/demo/HISTORY.md` をReadで読み込み、前回比の変化点を特定
4. `frontend/src/content/notes/` の直近ポートフォリオ記事を確認（内容の重複回避）

### Phase 2 - 記事構成の決定

- レポートの §10最適化提案 から改善ポイントを抽出
- 改善提案の根拠として最も説得力のあるデータをレポートから選定
- 改善点がない週は「現状維持が最善である根拠」を記事にする
- 初回構築レポートの場合: 「なぜこの銘柄構成にしたか」の構築根拠を記事にする（前回比は使わない）

### Phase 3 - 記事生成 → プレビュー（まだ書き込まない）

- `article-template.md` に従い1500-2000字の記事を生成
- slugはSEO重視形式（例: `20260212_demo-portfolio-bank-etf-momentum.md`）
- frontmatter: title, summary, publishedAt
- 記事末尾に免責文を必ず含める
- AskUserQuestionで全文プレビューを提示 → OK/修正指示を判断

### Phase 4 - 保存・検証（ユーザーOK後）

- `frontend/src/content/notes/` にWrite
- ビルド確認: `docker compose exec frontend npm run build`

## タイトルの付け方

- 具体的なアクション・テーマを先に、補足説明を後に置く
- 例: 「デモポートフォリオ構築 - 100万円で始める成長志向のETF投資」
- 例: 「銀行ETF追加でリスク効率改善 - デモポートフォリオ週次レポート」

## 記事作成のポイント

- **銘柄一覧は表にする**: 保有銘柄や提案銘柄は表形式で示すとわかりやすい
- **システムのデータを根拠に含める**: 5軸スコア・シャープレシオ・モメンタム等、当サイトの分析機能で得られるデータを判断根拠として明示する
- **「マイページ（デモ）」への誘導**: まとめでデモポートフォリオの確認先として言及する
- **初回記事のみ**: 「この取り組みについて」セクションで、システム×生成AI（Claude Code）による実験的な運用であることを説明する

## ノート記事のfrontmatter仕様

記事ファイルは以下の形式でなければならない（`frontend/src/content/notes/index.ts` のパーサーが読む）:

```yaml
---
title: 記事タイトル
summary: 記事の要約（80字以内）
publishedAt: YYYY-MM-DD
---
```

## 免責文テンプレート

記事末尾に必ず以下の趣旨の免責文を含める（表現は毎回変えてよい）:

```
---
*この記事はデモポートフォリオの分析記録です。特定の銘柄の売買を推奨するものではありません。投資判断はご自身の責任でお願いいたします。*
```

## 完了条件

- レポートの数値を正確に引用している
- 1500-2000字の範囲内
- frontmatterが正しいYAML形式
- Viteビルドが通る

## 出力形式

```markdown
## /publish-report 結果

### 生成記事
- ファイル: `frontend/src/content/notes/{ファイル名}`
- タイトル: {タイトル}
- 文字数: {N}字

### 品質チェック
| 項目 | 結果 |
|------|------|
| frontmatter形式 | OK/NG |
| 文字数範囲 | OK/NG（N字） |
| 数値正確性 | OK/NG |
| ビルド確認 | OK/NG |
```

## 関連スキル

- `/portfolio-analysis` - 分析レポートの生成
- `/commit` - 記事生成後のコミット

## 関連ファイル

| ファイル | 役割 |
|----------|------|
| `reports/*_portfolio_analysis_demo.md` | 入力レポート |
| `reports/demo/HISTORY.md` | ポートフォリオ履歴 |
| `frontend/src/content/notes/` | 出力先ディレクトリ |
| `frontend/src/content/notes/index.ts` | ノートローダー（frontmatter形式の制約元） |
