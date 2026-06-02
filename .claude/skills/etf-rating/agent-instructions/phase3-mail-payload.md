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

### 3. 本文構造（新フォーマット）

本文は **冒頭サマリ → 全銘柄スコア一覧 → 市場環境 → 銘柄別ブロック → フッタ**
の順で固定する。各銘柄ブロックは「ひとこと／Top5／リスク／3シナリオ」の
4部構成とし、生の20項目スコア表は `<details>` 折りたたみ内に「1行サマリ」
で格納する。

#### 文体ガイド

- **です・ます調**（必須）。ただし **尊敬語・謙譲語は使わない**（「いたします」「させていただきます」は禁止）
- 専門用語は下の「内部用語 → 平易表現 言い換え表」に従って日本語に言い換える（SSOT）
- 数値密度を下げる: 文章中に必要な数値だけ自然に埋め込む。一覧表は冒頭の銘柄スコア一覧と詳細セクション（`<details>` 内）のみ

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

| # | セクション | 内容 | 折りたたみ |
|---|-----------|------|-----------|
| 1 | ヘッダ | 「5月22日 終値ベース ETF Rating レポートです」+ 採点ルール3行 | なし |
| 2 | 今日のひとこと | Phase 2 の300字総評（payload.summary_text）。市場局面ラベル含む | なし |
| 3 | 全銘柄スコア一覧 | 銘柄ごとに `銘柄/総合点/追い風/逆風/前日比/判定` の表 | なし |
| 4 | いまの市場環境 | 為替・金利・コモディティ・地政学（market_snapshot.summary_lines） | なし |
| 5 | 銘柄別ブロック | 各銘柄を「ひとこと／Top5／リスク／3シナリオ」の4部で表示 | 各銘柄末尾 `<details>` で20項目スコア |
| 6 | 観点鮮度の警告 | criteria_warnings がある場合のみ | なし |
| 7 | フッタ | 次回 tune 推奨日、送信時刻 | なし |

#### 銘柄別ブロック（HTML）の例

```html
<div style="margin:12px 0;border:1px solid #ddd;border-radius:4px;padding:12px;">
  <div>
    <strong>#3 1629 商社・卸売</strong><br>
    総合 <strong>68.2点</strong>／前日比 +1.5pt／判定 <span class="badge">強い追い風</span>
  </div>

  <p><strong>■ ひとこと</strong></p>
  <p>資源・エネルギー価格高、円安、Buffett の保有継続、株主還元拡大という追い風が
     複数同時成立。中期で構造的に好環境ですが、PBRが2倍を超えて割安感が消えている
     点と、円キャリー巻き戻しの再来リスクは引き続き注意が必要です。</p>

  <p><strong>■ 追い風の主役（Top5）</strong></p>
  <ul>
    <li>コモディティ複合（原油 $110・LNG $17 で爆上げ）</li>
    <li>円安継続（USD/JPY 159円）</li>
    <li>Buffett が 5社すべて 10%超まで保有</li>
    <li>株主還元（5社合計 自社株買い 6,400億円超）</li>
    <li>中国景気回復（PMI 52）</li>
  </ul>

  <p><strong>■ 気をつけるべきリスク</strong></p>
  <ul>
    <li>バリュエーション過熱（PBR 2倍超、1年で+90%上昇後）</li>
    <li>中東停戦と日銀タカ派化の同時発生（2024年8月型の急落リスク）</li>
  </ul>

  <p><strong>■ 3ヶ月の見通し</strong></p>
  <ul>
    <li><strong>基本ケース</strong>：中東長期化＋日銀緩慢な利上げ → +10〜+20%</li>
    <li><strong>上振れケース</strong>：コモディティ追加スパイク → +25〜+40%</li>
    <li><strong>下振れケース</strong>：中東停戦＋日銀タカ派加速 → -20〜-30%</li>
  </ul>

  <details>
    <summary>詳細を見る（20項目スコアと採点根拠）</summary>
    <ul>
      <li>A-1 コモディティ複合: 85点（原油 $110・LNG $17、Top5/weight×2）</li>
      <li>A-2 円安継続: 78点（USD/JPY 159円、Top5/weight×2）</li>
      ... 18行
    </ul>
  </details>
</div>
```

Plain Text 版は同じ4部構成を `===` 区切りで実装し、`<details>` 相当は
「→ 全20項目の詳細スコアは {report_path} を参照してください」の1行で
ファイルパスへ誘導する。

### 4. HTML 縮約仕様（初版から <100KB 厳守）

各銘柄詳細を **初版生成時から「ひとこと＋Top5＋リスク＋3シナリオ」のみに絞る**。
生の20項目スコア表（A-1〜B-10）は `<details>` 内に格納するが、各項目は
**1行サマリ**程度（例: `A-1 コモディティ複合: 85点（原油$110・LNG$17, Top5）`）
に圧縮する。

これにより:
- 初版生成時に HTML <100KB を保証
- Gmail クリップ回避（102KB 閾値）
- 後付け縮約フローを不要化

サイズ計測:
- `mail.html_size_warn_kb`（既定90KB）超: ペイロードに `html_size_warning: true` フラグ
- `mail.html_size_error_kb`（既定100KB）超: `oversized: true` フラグ + 銘柄別 `<details>` 中身を「Top3のみ」に追加縮約してリトライ

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
| `ratings[].top_drivers_bearish_labels` | Top5（注意リスク）ラベル配列 |

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
  "plain_body": "（プレーンテキスト版メール本文。冒頭サマリ→市場環境→各銘柄ブロック）",
  "html_body": "（HTML版メール本文。初版から<100KB、銘柄詳細は4部構成、20項目は<details>内）",
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

サイズ超過時は以下の順で縮約:

1. 各銘柄の `detail_summary_lines` を Top5 のみに絞る
2. ランキング表を上位3件に削減
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
