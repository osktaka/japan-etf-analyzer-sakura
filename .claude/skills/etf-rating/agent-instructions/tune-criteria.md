# tune-criteria: 観点（criteria YAML）見直し対話

## 目的

`/etf-rating tune <code>` から呼ばれる対話フロー。指定銘柄の観点 YAML
（`criteria/{code}.yaml`）を、採点履歴の傾向を踏まえて見直し提案・更新する。

観点劣化（半年で陳腐化）への対策。月初強制 tune を運用ルールとし、
メールフッタに version 表示・90日経過で黄/180日で赤を出すことで強制力を担保する。

**自動実行モード（`ETF_RATING_NONINTERACTIVE=1` または `--send-mail`）では
このフローを起動禁止**。対話必須。

## 入力パラメータ

| パラメータ | 説明 | 例 |
|------------|------|-----|
| `CODE` | 対象 ETF コード | `1629` |
| `CRITERIA_PATH` | 観点 YAML | `.claude/skills/etf-rating/criteria/1629.yaml` |
| `HISTORY_PATH` | 採点履歴 jsonl | `data/etf-rating/history/1629.jsonl` |
| `CALC_PARAMS_PATH` | 共通閾値 JSON | `.claude/skills/etf-rating/calc_params.json` |
| `RUN_DATE` | 実行日（YYYY-MM-DD） | `2026-05-22` |

## 手順

### 1. 履歴読み込み・統計集計

`HISTORY_PATH` の直近30日（最大30行）を集計する。Bash で末尾30行を抽出して
jq で統計値を算出:

```bash
HIST_FILE="data/etf-rating/history/{CODE}.jsonl"
if [ ! -f "${HIST_FILE}" ]; then
  echo "履歴ファイルなし: 初回 tune 扱い"
else
  # 直近30日のネットスコア統計
  tail -n 30 "${HIST_FILE}" \
    | jq -s '{
        n: length,
        avg_net: (map(.net_score) | add / length),
        max_net: (map(.net_score) | max),
        min_net: (map(.net_score) | min),
        latest: .[-1]
      }'
fi
```

以下を集計:

- ネットスコアの平均・標準偏差・最大・最小
- ネットスコアの前日比絶対値の平均（=ボラティリティ指標）
- 上昇条件・下落条件それぞれのスコア平均（条件IDごと、Phase 1 サマリJSONをアーカイブしている場合のみ）
- 「ほぼ常に同じスコア」の条件IDを抽出（過去30回の標準偏差<5）

### 2. 観点 YAML 読み込み

`CRITERIA_PATH` を Read し、以下を確認:

- 現行 `version` と経過日数
- `top5_drivers` / `top5_risk_drivers` の一覧
- `upside_conditions` / `downside_conditions` の各項目（id, description, thresholds, type, data_sources, past_cases）
- `revision_history` の過去ログ

### 3. 改善候補の提案生成

以下のヒューリスティックで改善提案を作成:

| パターン | 提案 |
|----------|------|
| 標準偏差 <5 の条件 | 「常に同スコアの条件は実質無効。閾値を細分化するか削除を検討」 |
| Top5 ドライバーがスコアに寄与していない（平均60点未満が継続） | 「Top5 から外し、別ドライバーに昇格させる候補は？」 |
| ボラティリティが極端に大きい（前日比平均 >10pp） | 「`thresholds` の数値化を進めて LLM 採点ブレを抑制」 |
| 経過日数 ≥ 90日 | 「黄色警告中。観点の全体棚卸しを推奨」 |
| 経過日数 ≥ 180日 | 「赤警告。早急に更新必須」 |

提案は `{N}件` リスト化して整形。

### 4. AskUserQuestion で承認確認

提案ごとに以下を質問（最大5〜7件、まとめて1回でも可）:

| カテゴリ | 質問例 |
|----------|--------|
| 条件追加 | 「{新条件案} を A-{N} として追加しますか？」 |
| 条件削除 | 「{条件ID} は実質スコア固定（標準偏差{X}）です。削除しますか？」 |
| 閾値調整 | 「{条件ID} の thresholds を{現在}→{提案}に変更しますか？」 |
| Top5 入替 | 「Top5 ドライバー {旧} を {新} に置き換えますか？」 |
| シナリオ更新 | 「base/upside/downside のレンジを {現在}→{提案} に変更しますか？」 |

各質問で「変更しない」も選択肢に含める。

### 5. YAML 編集

承認された変更を Edit ツールで YAML に反映:

- `upside_conditions` / `downside_conditions` の項目追加・削除・閾値更新
- `top5_drivers` / `top5_risk_drivers` の入替
- `scenarios` の調整
- `version` を `{RUN_DATE}` で更新
- `revision_history` に1エントリ追記:
  ```yaml
  - date: "2026-05-22"
    note: "条件A-6の閾値を{旧}→{新}に変更。Top5から{旧}を外して{新}を追加（履歴30日でボラ低下のため）"
  ```

複数条件の同時更新は **1コミット相当の単位**でまとめる（Edit を複数回実行）。

### 6. 整合性チェック

更新後、以下を確認:

- `upside_conditions` が10件、`downside_conditions` が10件を維持しているか
- `top5_drivers` / `top5_risk_drivers` が各5件か（増減NG）
- 各条件IDが一意か（A-1〜A-10, B-1〜B-10）
- `scenarios.base` / `upside` / `downside` がすべて定義済みか

不整合があれば AskUserQuestion で再修正を促す。

### 7. 完了サマリ提示

ユーザーに以下を提示:

```
{CODE} 観点更新完了

変更点:
- A-6: thresholds {旧}→{新}
- B-3: 削除（実質無効）
- Top5 ドライバー: A-2 を外し A-9 を追加

新 version: 2026-05-22
次回 `/etf-rating {CODE}` 実行時に新観点で採点されます
```

## 出力

| ファイル | 変更内容 |
|----------|----------|
| `{CRITERIA_PATH}` | 観点 YAML（条件追加/削除/閾値更新、version 更新、revision_history 追記） |

## メインへの戻り値

完了時1行:
```
{CODE} 観点更新完了（version {NEW_VERSION}, {N}件変更）
```

変更なし:
```
{CODE} 観点更新スキップ（変更なし）
```

失敗時1行:
```
{CODE} tune 失敗: {理由}
```

## 注意事項

- **自動実行モードでは起動禁止**。`ETF_RATING_NONINTERACTIVE=1` を検知したら
  即座に「tune は対話モードでのみ実行可能」と返して停止
- YAML 編集は **Edit ツール**を使う（Write による全面書換は禁止、差分を最小化）
- `revision_history` は append-only。過去エントリの編集・削除禁止
- 採点履歴 jsonl は読み取り専用。本フローでは更新しない
- pytest / commit は人手。本フローでは実行しない

## 自己修正ルール

- 履歴が30日に満たない場合 → 利用可能な範囲で集計し、その旨を冒頭に明記
- 履歴 jsonl が空（初回実行） → 統計に基づく提案はスキップし、経過日数のみで判断
