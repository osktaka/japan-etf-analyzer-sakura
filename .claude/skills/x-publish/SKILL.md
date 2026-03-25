# X投稿実行スキル

```yaml
---
name: x-publish
description: tmp_x_posts_v2.mdの内容をXに投稿
user-invocable: true
allowed-tools: Read, Edit, Bash, Glob
aliases: ["/x-publish", "/xpub"]
---
```

## 概要

`reports/tmp_x_posts_v2.md` の投稿文をX（旧Twitter）に投稿する。
cron自動実行（`--auto`）・対話実行の両方に対応。

## 引数

| 引数 | 説明 | デフォルト |
|------|------|-----------|
| `--auto` | 確認なしで投稿（cron用） | なし（対話時はプレビュー確認） |
| `--production` | `[テスト]` タグを除去して投稿 | なし（テストタグ付き） |
| `--dry-run` | 投稿せずプレビューのみ表示 | なし（実投稿） |

**使用例**:
```
/x-publish                    # 対話モード（プレビュー→確認→投稿）
/x-publish --dry-run          # プレビューのみ
/x-publish --auto             # cron用（テストタグ付き）
/x-publish --auto --production  # cron本番用（テストタグ除去）
```

## 中間ファイルフォーマット（入力契約）

`reports/tmp_x_posts_v2_HHMM.md` は `/market-x-draft` または `/market-intraday` スキルが生成する。
ファイル名のHHMMは実行時の日本時間（例: `tmp_x_posts_v2_0700.md`, `tmp_x_posts_v2_1200.md`）。
フォーマット仕様は `.claude/skills/market-x-draft/SKILL.md` の「出力フォーマット」セクションを参照。

パース方法:
- `## 投稿N` 見出しで各投稿を識別
- `---` で投稿を区切る
- タイトル行（【...】）と本文・ハッシュタグを抽出

## 実行フロー

### Step 1: 投稿文読み込み

1. Globで `reports/tmp_x_posts_v2_*.md` を検索し、最新ファイル（更新日時順）を特定する
2. 最新ファイルをReadで読み込む
3. `## 投稿N` + `---` でパースし、投稿を抽出（AM/PM: 3投稿、日中観察: 1投稿）
4. ファイルが存在しない場合 → エラー通知して終了

### Step 2: プレビュー・確認

**対話モード（デフォルト）**:
- 3投稿のプレビューを表示
- `--production` 指定時は `[テスト]` 除去後のテキストを表示
- ユーザーの確認を待つ（投稿/キャンセル/編集）

**`--auto` モード**:
- プレビュー・確認をスキップ

**`--dry-run` モード**:
- プレビューのみ表示して終了

### Step 3: X投稿実行

各投稿について以下を順次実行:

1. `--production` 指定時: テキストから `[テスト]` を除去
2. `docker compose exec backend python scripts/x_post.py --text "投稿テキスト"` をBash実行
3. JSON結果を確認（`{"success": true, "tweet_id": "...", "url": "..."}`）
4. **投稿間隔: 90秒**（sleep 90）で次の投稿を実行（Bashタイムアウト: 180秒指定）

### Step 4: 履歴更新

投稿成功した投稿を `.claude/x-posts-history.md` に追記:

タイプは中間ファイルのヘッダー行から取得する:
- `# X投稿 YYYY-MM-DD AM（3投稿構成）` → AM
- `# X投稿 YYYY-MM-DD PM（3投稿構成）` → PM
- `# X投稿 YYYY-MM-DD 日中観察（1投稿構成）` → 日中観察
- `# X投稿 YYYY-MM-DD 米国観察（1投稿構成）` → 米国観察

投稿数は中間ファイルの内容に応じて可変（AM/PM: 3投稿、日中観察: 1投稿）。

```markdown
### YYYY-MM-DD（マーケット速報 {タイプ}）

- パターン: マーケット速報型
- 投稿1:
（投稿1全文）
```

## エラーハンドリング

| エラー | 対応 |
|--------|------|
| `tmp_x_posts_v2.md` 未存在 | エラー通知して終了 |
| API認証エラー（401/403） | 全投稿中止、認証情報の確認を促す |
| 個別投稿の失敗（レート制限等） | 失敗投稿をスキップして残りを続行 |
| Docker未起動 | エラー通知して終了 |

最終結果に成功/失敗の内訳を報告する。

## 依存ファイル

| ファイル | 役割 |
|----------|------|
| `reports/tmp_x_posts_v2_HHMM.md` | 入力（投稿文、Globで最新を検索） |
| `backend/scripts/x_post.py` | X API投稿スクリプト |
| `.claude/x-posts-history.md` | 投稿履歴（追記先） |
| `.env` | X API認証情報 |

## 完了条件

- [ ] `tmp_x_posts_v2.md` を正しくパースした
- [ ] 3投稿が順次投稿された（または--dry-runでプレビュー表示）
- [ ] 投稿間隔90秒が確保された
- [ ] 投稿結果（成功/失敗）が報告された
- [ ] 成功した投稿が履歴ファイルに追記された
