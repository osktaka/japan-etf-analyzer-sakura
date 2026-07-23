# Phase 3: メールペイロード生成

## 目的

Phase 2 サマリ + 全銘柄 Phase 1 レポートを統合し、Jinja2 テンプレ
（`backend/src/services/templates/etf_rating/` 配下）でレンダリング
するための **JSON ペイロード**を1つ生成する。

本フェーズはペイロード生成までで終了し、メイン側で payload パスをユーザーに提示する。
実送信は `--send-mail` 指定時のみ送信スクリプト経由で別途実行される（SKILL.md Step 5）。
スクリプトの実ファイルはホスト上では `backend/scripts/etf_rating_send_mail.py` だが、
コンテナ内では `/app/scripts/etf_rating_send_mail.py`（`./backend/scripts→/app/scripts`
マウント）として呼び出す。

**出力先（重要）**: payload は `.tmp/` ではなく、マウント済みの
`reports/etf-rating/_payloads/{YYYYMMDD}_email_payload.json` に出力する。
`.tmp/` は backend コンテナにマウントされていないため、送信スクリプトがコンテナ内で
payload を見つけられず `payload not found` になる。

## 入力パラメータ

| パラメータ | 説明 | 例 |
|------------|------|-----|
| `WORK_DIR` | 作業ディレクトリ | `.tmp/etf-rating_20260522` |
| `CALC_PARAMS_PATH` | 共通閾値 JSON | `.claude/skills/etf-rating/calc_params.json` |
| `RUN_DATE` | 実行日（YYYY-MM-DD） | `2026-05-22` |
| `SUBJECT_PREFIX` | 件名プレフィックス（参考） | `[ETF Rating]` |

## 手順

### 1. 入力収集

- `{WORK_DIR}/20_summary_meta.json` を Read
- `{WORK_DIR}/10_rating_*_summary.json` を Glob で列挙し全 Read
- `{WORK_DIR}/10_rating_*.md` を Glob で列挙、本文を Read（メール本文埋込用）
- `{WORK_DIR}/00_market_snapshot.md` を Read（マクロ要約埋込用）
- `CALC_PARAMS_PATH` を Read（件名・本文サイズ制約取得）

### 2. 件名生成

`calc_params.json` の `mail.subject_max_chars`（既定40字）を上限とする。

**標準フォーマット**（40字以内・人が読みやすい "／" 区切り）:

```
[{M/D} ETF Rating] {N}銘柄 平均{X.X}点／強い追い風 {K}銘柄／警戒 {W}銘柄
```

| 状況 | 例 | 字数 |
| ---- | ---- | ---- |
| 通常（追い風のみ） | `[5/22 ETF Rating] 7銘柄 平均65.7点／強い追い風 5銘柄` | 35字 |
| 警戒併発 | `[5/22 ETF Rating] 8銘柄 平均48.3点／警戒 2銘柄` | 32字 |
| 強・警ゼロ | `[5/22 ETF Rating] 7銘柄 平均58.2点` | 25字 |

**集計ルール（最重要）**:

- 「強い追い風 K銘柄」「警戒 W銘柄」は **payload.flags リストの type 値で集計** する
  - `type ∈ {strong_tailwind, strong_bullish}` → 強い追い風カウント
  - `type ∈ {severe_risk, critical_risk, warning}` → 警戒カウント
- ゼロ件のセクションは件名に含めない（"強い追い風 0銘柄" は省略する）
- 平均ネット = `ratings[].net_score` の単純平均（小数1位）

**重要**: payload の `subject` キーに固定文字列を入れても **notifier 側で
flags リストから再集計して件名を組み立て直す**。これは 2026-05-22 の運用で
「強0警0」固定文字列バグが発生したインシデント対応として、件名生成の
SSOT を `etf_rating_notifier._build_subject()` に集約したため。

Phase 3 は payload.subject に件名候補を入れても良いが、件名計算の
責務は notifier 側。実際の出力件名は notifier が決める。

**短縮ルール**（40字超過時、notifier 側で自動適用）:

1. "ETF Rating" → "ETF R" に短縮
2. 末尾の警戒部を落とす
3. フラグ件数全体を省略

### 3. 本文構造（短文フォーマット / 2026-07-23〜）

**設計方針**: モバイルで1分以内に読み切れる長さにする。
プレーンテキスト本文は `calc_params.json` の `mail.plain_body_target_chars`
（既定 **2,000字**）以内を厳守。旧フォーマットの銘柄別4部構成ブロック
（ひとこと／Top5／リスク／3シナリオ）と20項目 `<details>` は **廃止** し、
詳細は `reports/etf-rating/{code}/` の銘柄別レポートに委譲する。

本文は **今日の要点 → スコア一覧 → 動きがあった銘柄 → 注意ポイント → フッタ**
の順で固定する。

#### 文体ガイド

- **です・ます調**（必須）。ただし **尊敬語・謙譲語は使わない**（「いたします」「させていただきます」は禁止）
- 専門用語は下の「内部用語 → 平易表現 言い換え表」に従って日本語に言い換える（SSOT）
- 数値密度を下げる: 文章中に必要な数値だけ自然に埋め込む。一覧表はスコア一覧のみ

#### 内部用語 → 平易表現 言い換え表（SSOT）

本表はメール本文・総評・各銘柄ブロックすべての文章中で適用する。
Phase 2 の総評（payload.summary_text）も同じ規則に従うこと。

| 内部用語（コード/スコア名） | 本文での表記（平易表現） | 補足 |
|------------------------------|--------------------------|------|
| 上昇W / upside_weighted | 追い風スコア（または「追い風の強さ」） | 表内のみ「上昇W」表記可 |
| 下落W / downside_weighted | 下落リスク | 表内のみ「下落W」表記可 |
| ネット中期スコア / net_score | 総合点 | 表内のみ「ネット」表記可 |
| strong_bullish / strong_tailwind | 強い追い風 | 件名・本文・badge いずれも |
| bearish / severe_risk / critical_risk / warning | 警戒 / 重大警戒 | 30未満で「重大警戒」、30-39で「警戒」 |
| top5_drivers | 追い風の主役（Top5） | セクション見出しは「追い風の主役（Top5）」 |
| top5_risk_drivers | 注意すべきリスク（Top5） / 気をつけるべきリスク | どちらでも可 |
| leading / lagging | 先取り / 後追い | 表内・本文ともこの表記 |
| NIM | 利ザヤ | 業界専門用語 |
| PBR | 割安感（PBR） | 略語を残し補足 |
| CAGR | 年率成長率 | 必要に応じて |

#### 判定ラベル基準（calc_params.json と一致）

| 総合点 | ラベル | 絵文字 |
|--------|--------|--------|
| 70 以上 | 強い追い風 | 🟢 |
| 60〜69 | 追い風 | 🟢 |
| 40〜59 | 中立寄り | 🟡 |
| 30〜39 | 警戒 | 🔴 |
| 30 未満 | 重大警戒 | 🔴 |

#### セクション一覧

| # | セクション | 内容 | 上限 |
|---|-----------|------|------|
| 1 | ヘッダ | 「7月22日 ETF Rating（終値ベース・N銘柄）」の1行のみ。採点ルールの定型説明は書かない（フッタの判定基準1行に集約） | 1行 |
| 2 | 今日の要点 | payload.summary_text（Phase 2 の300字総評）を **箇条書き最大 `mail.key_points_max`（既定3）行・各60字以内** に凝縮する。「市況の変化」「大きく動いた銘柄と理由」「今日のスタンス」の順を推奨 | 3行 |
| 3 | スコア一覧 | 1銘柄1行: `絵文字 総合点 (前日比) コード 銘柄名 [判定]`。追い風/逆風の内訳数値は載せない。末尾に「平均X点／強い追い風 K銘柄／警戒 W銘柄」 | 銘柄数+1行 |
| 4 | 動きがあった銘柄 | 前日比 ±`mail.movers_delta_pp_threshold`（既定3.0pp）以上 or 判定ラベルが前日から変化した銘柄のみ、**変動幅（絶対値）の大きい順**に最大 `mail.movers_max`（既定5）件。各1〜2行で「何が起きてスコアがどう動いたか」を平易に書く。該当ゼロなら「本日は大きなスコア変動はありません。」の1行 | 5件×2行 |
| 5 | 注意ポイント | 警戒・重大警戒銘柄（総合点40未満）／下落リスクが高い銘柄（downside_weighted が `mail.cautions_downside_threshold`＝既定40以上）／市場全体の留意点を最大 `mail.cautions_max`（既定3）行。該当なしなら省略 | 3行 |
| 6 | 観点鮮度の警告 | criteria_warnings がある場合のみ | - |
| 7 | フッタ | 判定基準1行＋「詳細は reports/etf-rating/{code}/ のレポート参照」1行＋次回 tune 推奨日・送信時刻 | 3行 |

**書かないもの（重要）**: 銘柄別4部構成ブロック（ひとこと／Top5／リスク／3シナリオ）、
20項目スコアの `<details>`、市場環境の独立セクション（要点1行目に統合）、
採点ルールの定型説明3行。これらは全て銘柄別レポートファイル側にのみ存在する。

#### 本文の例（プレーンテキスト）

```
7月22日 ETF Rating（終値ベース・7銘柄）

■ 今日の要点
・中東停戦崩壊で原油・LNG急騰。資源系に強い追い風、市況は中立（やや警戒寄り）
・1655(+7.8) 1618(+6.7) 314A(+5.4) が大幅改善しいずれも強気転換
・首位は商社1629（74.3）。過熱気味の銀行1615は追撃買い見送りが妥当

■ スコア一覧（総合点／前日比）
🟢 74.3 (+0.7pt)  1629 商社・卸売  [強い追い風]
🟢 72.4 (-0.2pt)  1615 東証銀行業  [強い追い風]
（…全銘柄）
平均 69.1点／強い追い風 5銘柄／警戒 0銘柄

■ 動きがあった銘柄（前日比±3pt以上）
▲ 1655 S&P500（+7.8pt）: 円安163円台とAI決算好調で下落リスクが大幅改善
▲ 1618 エネルギー資源（+6.7pt）: ホルムズ再封鎖で原油・LNGが急騰
▲ 314A ゴールド（+5.4pt）: 実質金利低下と地政学リスクで4営業日ぶり改善

■ 注意ポイント
・1615 東証銀行業: 200日線乖離+28.7%と過熱。追撃買いは見送り
・全体: 中東リスクの織り込みが浅い（VIX 17台）点に留意

---
判定基準: 70〜🟢強い追い風／60〜🟢追い風／40〜🟡中立寄り／30〜🔴警戒／30未満🔴重大警戒
銘柄別の詳細（Top5・リスク・3シナリオ・20項目スコア）: reports/etf-rating/{銘柄コード}/ のレポート参照
次回 tune 推奨日: 2026-08-20／送信時刻: 18:15頃（JST）
```

HTML 版は同じセクション構成で組み立てる（レイアウトはフォールバックテンプレート
`backend/src/services/templates/etf_rating/rating.html.j2` を正とする）:
スコア一覧は `銘柄/総合/前日比/判定バッジ` の4列テーブル、要点は左ボーダー付き
ボックス、注意ポイントは黄色背景ボックス。`<details>` は使わない。

**フォールバック（パターンB）との差異**: 「判定ラベルが前日から変化」の条件は
payload に前日ラベルが無いため本フェーズ（パターンA）でのみ判定できる。
フォールバックテンプレートは前日比 ±閾値のみで抽出する
（実装: `etf_rating_notifier._select_movers()` / `_select_cautions()`。
市場全体の留意点も payload から導出できないためフォールバックでは省略）。

### 4. サイズ制約

短文フォーマットでは通常 プレーン 2,000字以内／HTML 15KB 前後に収まる。
超過チェックは従来どおり実施する:

- プレーン本文が `mail.plain_body_target_chars`（既定2,000字）超: 「動きがあった銘柄」の各行を1行に圧縮 → 「今日の要点」を2行に削減、の順で縮約
- `mail.html_size_warn_kb`（既定90KB）超: ペイロードに `html_size_warning: true` フラグ
- `mail.html_size_error_kb`（既定100KB）超: `oversized: true` フラグ + スコア一覧以外を要点のみに縮約してリトライ（短文フォーマットでは実質発生しない）

### 5. ペイロード生成

`reports/etf-rating/_payloads/{YYYYMMDD}_email_payload.json` を Write
（`mkdir -p reports/etf-rating/_payloads` で親ディレクトリを作成してから）:

#### Payload 正規キー一覧（v3）

メール本文受け渡しのキー名は以下を正規とする。これ以外のキーは受け付けない。

| 正規キー | 用途 |
|----------|------|
| `plain_body` | プレーンテキスト本文（パターンA） |
| `html_body` | HTML本文（パターンA） |
| `ratings[].delta_net` | 前日比（pp） |
| `ratings[].upside_weighted` | 上昇マッチ度（重み付け） |
| `ratings[].downside_weighted` | 下落リスク（重み付け） |
| `ratings[].top_drivers_bullish_labels` | Top5（追い風の主役）ラベル配列 |
| `ratings[].top_drivers_bearish_labels` | Top5（注意リスク）ラベル配列。短文フォーマットでは先頭要素を「注意ポイント」の理由に使用 |

`ratings[].detail_summary_lines`（20項目1行サマリ）は短文フォーマットでは
メール本文に描画されないが、履歴・デバッグ用として payload への格納は継続してよい（任意）。

過去の互換キー（`plain` / `html` / `delta` / `upside_score` / `downside_score` /
`top_drivers` / `top_drivers_bullish` / `top_risk_drivers` / `top_drivers_bearish`）は
**2026-05 削除済み**。送信時に存在しても無視される。


#### notifier への本文受け渡しルール

| 採用パターン | 渡すキー | notifier 側の挙動 |
|------------|----------|-------------------|
| **A: Phase 3 で完成本文を組み立てる** | `plain_body` / `html_body`（推奨） | キー値をそのまま EmailClient.send に渡す（Jinja2 レンダリングをスキップ） |
| **B: Jinja2 にレンダリングを任せる** | `ratings` / `flags` / `market_snapshot` / `summary_text` / `criteria_warnings` / `next_tune_date` 等 | `plain_body` / `html_body` が無ければ `rating.md.j2` / `rating.html.j2` で組み立て |

通常運用は **パターン A（`plain_body` / `html_body`）** を推奨。Phase 3 の
縮約（サイズ超過時のハイライト3行短縮など）が確実に反映されるため。
件名のみ notifier が再計算するため、payload.subject は参考扱いで上書きされる。

#### ペイロード例（新フォーマット）

```json
{
  "subject": "[5/22 ETF Rating] 7銘柄 平均65.7点／強い追い風 5銘柄",
  "run_date": "2026-05-22",
  "market_regime": "中立",
  "market_regime_note": "インフレ加速・コモディティ高...",
  "summary_text": "日本株テーマ（B群）が好調で、A群コアとの格差が開いた一日。...",
  "codes": ["1615", "2646", "1629", "200A", "1618", "1655", "314A"],
  "ratings": [
    {
      "code": "1615",
      "name": "東証銀行業",
      "bucket": "group_b",
      "rank": 1,
      "net_score": 72.7,
      "upside_weighted": 76.0,
      "downside_weighted": 30.7,
      "delta_net": null,
      "executive_note": "日銀利上げサイクル進行＋JGB10年2.79%＋3メガ揃って過去最高益...",
      "top_drivers_bullish_labels": [
        "日銀利上げサイクル進行（政策金利0.75→1.00%観測）",
        "JGB10年金利2.79%（1996年以来高水準で利ザヤ拡大）",
        "..."
      ],
      "top_drivers_bearish_labels": [
        "MUFG PBR 1.55（過熱反落リスク）",
        "..."
      ],
      "scenarios": {
        "base": {"description": "現在条件継続 → +5〜+15%"},
        "upside": {"description": "1.00%超利上げ + 為替円安 → +20〜+35%"},
        "downside": {"description": "PBR過熱反落 → -20〜-30%"}
      },
      "detail_summary_lines": [
        "A-1 日銀利上げ: 90点（Top5/×2、政策金利0.75→1.00%観測）",
        "A-2 JGB10年金利: 85点（Top5/×2、2.79%で1996年以来高水準）",
        "..."
      ],
      "criteria_version": "2026-05-22_v1",
      "criteria_age_days": 0,
      "report_path": "reports/etf-rating/1615/20260522_1615_rating.md"
    }
  ],
  "flags": [
    {"code": "1615", "type": "strong_tailwind", "upside_weighted": 76.0},
    {"code": "2646", "type": "strong_tailwind", "upside_weighted": 74.1}
  ],
  "market_snapshot": {
    "regime": "中立",
    "note": "インフレ加速・コモディティ高...",
    "summary_lines": [
      "原油 Brent $110台、LNG高水準で資源系に追い風",
      "USD/JPY 159円、円安が継続中",
      "日銀は6月会合での 0.75 → 1.00% 利上げ観測が強い",
      "中国製造業PMI 52で4年ぶり高水準",
      "中東情勢（ホルムズ海峡封鎖）と米イラン情勢が依然リスクの主軸"
    ]
  },
  "plain_body": "（プレーンテキスト版メール本文。今日の要点→スコア一覧→動きがあった銘柄→注意ポイント→フッタ。2,000字以内）",
  "html_body": "（HTML版メール本文。同セクション構成、<details>不使用、15KB前後目安）",
  "criteria_warnings": [],
  "next_tune_date": "2026-08-20",
  "size_meta": {
    "html_bytes": 87000,
    "html_size_warning": false,
    "oversized": false
  }
}
```

### 6. 失敗時の縮約

サイズ超過時は以下の順で縮約（短文フォーマットでは実質発生しない）:

1. 「動きがあった銘柄」の各行を1行（60字以内）に圧縮
2. 「今日の要点」を2行に削減
3. それでも超過する場合は payload に `oversized: true` フラグを立てて出力（メイン判断）

## 出力

| ファイル | 内容 |
|----------|------|
| `reports/etf-rating/_payloads/{YYYYMMDD}_email_payload.json` | メール送信用ペイロード（マウント済み。送信時はコンテナ内 `/app/...` 絶対パスで渡す） |

## メインへの戻り値

完了時1行:
```
メールペイロード生成完了（{N}銘柄, {NN}KB{, 縮約あり}）
```

失敗時1行:
```
ペイロード生成失敗: {理由}
```

## 注意事項

- 個人情報・SMTP 認証情報はペイロードに含めない（送信時に環境変数から注入）
- 件名は payload.subject に書いても **notifier が flags リストから再構築** する
- 本文の文体は「です・ます調」で統一（尊敬語・謙譲語は禁止）
- 専門用語は必ず日本語に言い換える（言い換え表は本ドキュメントの「文体ガイド」参照）

## 自己修正ルール

- summary_meta.json 欠損 → Phase 2 を再実行依頼ではなく、`10_rating_*_summary.json`
  から最低限の集計を内製してペイロード生成を続行
- 全銘柄サマリ欠損 → 失敗（メイン報告）
- 本文サイズ 100KB 超 → 縮約フロー（手順6）を1回実行してリトライ
