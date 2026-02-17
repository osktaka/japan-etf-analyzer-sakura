# Phase 3+4: 統合レポート作成・保存 指示書

## 前提

- 作業ディレクトリ: `{WORK_DIR}`（メインエージェントから渡される）
- Docker内パス: `/app/{WORK_DIR}`

## データ受け渡しルール

- **入力**: `{WORK_DIR}/` 配下の全分析結果ファイル、`{skill_dir}/report-guide.md`
- **出力**: `./reports/{username}/YYYYMMDD_{username}.md`
- **メインへの戻り値**: 「レポート保存完了: ./reports/{username}/YYYYMMDD_{username}.md」の1行のみ。データ全文やテーブル全体を返さないこと

---

## 統合エージェントの役割

統合エージェント（general-purpose）は、`{WORK_DIR}` 配下の全分析結果ファイルを読み込み、`report-guide.md` のテンプレートに従ってレポートを作成・保存する。

## 入力ファイル

### 共通（全モード）

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/market_environment.md` | 市場環境サマリー |
| `{WORK_DIR}/portfolio_data.json` | 全収集データ |
| `{WORK_DIR}/trend_summary.md` | トレンドデータ（存在する場合のみ。セクション0.5用） |
| `{WORK_DIR}/timing.json` | 各フェーズの実行時間記録 |
| `{WORK_DIR}/portfolio_reference.md` | セクション1・11.2用markdownテーブル（プログラマティック生成） |
| `{skill_dir}/report-guide.md` | レポートガイド（テンプレート＋書き方） |

### speed/normalモード

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/quant_analysis.md` | 定量リスク・リターン分析結果 |
| `{WORK_DIR}/score_analysis.md` | スコア・モメンタム分析結果 |
| `{WORK_DIR}/allocation_analysis.md` | アセットアロケーション分析結果（存在する場合） |
| `{WORK_DIR}/candidate_verification.md` | Phase 2 入替候補の外部検証結果（存在する場合のみ。speedモードでは生成されない） |

### debateモード

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/shared_calculations.md` | 共通定量計算結果（Phase 0.5で生成） |
| `{WORK_DIR}/analyst_a_analysis.md` | analyst-A分析結果 |
| `{WORK_DIR}/analyst_b_analysis.md` | analyst-B分析結果 |
| `{WORK_DIR}/analyst_c_analysis.md` | analyst-C分析結果（存在する場合） |
| `{WORK_DIR}/crossreview_round1_a.md` | analyst-A Round 1 レビュー（Phase 3で生成） |
| `{WORK_DIR}/crossreview_round1_b.md` | analyst-B Round 1 レビュー（Phase 3で生成） |
| `{WORK_DIR}/crossreview_round1_c.md` | analyst-C Round 1 レビュー（Phase 3で生成） |
| `{WORK_DIR}/crossreview_round2_a.md` | analyst-A Round 2 反論・合意（Phase 3で生成） |
| `{WORK_DIR}/crossreview_round2_b.md` | analyst-B Round 2 反論・合意（Phase 3で生成） |
| `{WORK_DIR}/crossreview_round2_c.md` | analyst-C Round 2 反論・合意（Phase 3で生成） |
| `{WORK_DIR}/candidate_verification.md` | Phase 2 入替候補の外部検証結果（存在する場合のみ。speedモードでは生成されない） |

---

## クロスレビュー（統合エージェント内で実施）

モードに応じて、以下のクロスレビュー観点ファイルを読み込み、レポートのセクション9に記載する。

### speedモード

クロスレビューなし。セクション9に「速度重視モードのためスキップ」と記載。

### normalモード

以下のファイルを読み込み、記載された観点で分析結果間の矛盾・整合性を検証する:

- **参照ファイル**: `{skill_dir}/agent-instructions/crossreview-normal.md`

### debateモード

Phase 3で独立エージェントが実施したクロスレビュー結果を読み込み、`crossreview-debate.md`の統合手順に従いセクション9を構成する。クロスレビュー自体の実施は不要（Phase 3で完了済み）。

- **参照ファイル**: `{skill_dir}/agent-instructions/crossreview-debate.md`
- **クロスレビュー結果ファイル**: `{WORK_DIR}/crossreview_round1_{a,b,c}.md`, `{WORK_DIR}/crossreview_round2_{a,b,c}.md`

**統合時の注意事項**:
- Phase 3で各エージェントが独立に出力したレビュー結果を忠実に反映すること
- 各ペルソナの★★★重点項目に基づくレビュー内容をそのまま活用すること
- 「全ペルソナ同意」と記載する前に、Round 2の反論・合意ファイルで実際に合意が形成されているか確認すること

セクション9には議論の経緯を詳細に記載:
- 見解の相違点とその根拠
- 合意された点
- 各アクションの合意度（100% / 67% / 見解分かれる）

### ペルソナ統合ガイド（議論重視モードのみ）

議論重視モードでは、3つのペルソナ（積極派/堅実派/異論派）の分析結果を統合する。

**統合の原則**:
1. **全ペルソナ合意の項目**: レポートで「全ペルソナ一致」と明記し、高い確信度で推奨
2. **過半数合意の項目**: 多数派の結論を採用しつつ、少数派の懸念を付記
3. **全ペルソナ不合意の項目**: 各ペルソナの見解を併記し、読者に判断を委ねる

**合意度の記載方法**:
- 各分析セクションの結論部分に `【合意度】` を付記する
- 形式: `【合意度: 100% / 67% / 見解分かれる】`
- 100%: 全ペルソナ一致
- 67%: 2ペルソナ合意、1ペルソナ反対・留保
- 見解分かれる: 全ペルソナ不合意（各見解を併記し読者に判断を委ねる）

---

## 出力

1. レポートファイル: `./reports/{username}/YYYYMMDD_{username}.md`（**`reports/{username}/` ディレクトリに保存**）
2. **メインへの戻り値**: 「レポート保存完了: ./reports/{username}/YYYYMMDD_{username}.md」の1行のみ

---

## レポート作成手順

1. `{WORK_DIR}/` 配下の全ファイルを読み込む
2. `{skill_dir}/report-guide.md` を読み込む
2a. `portfolio_data.json` の `_metadata._data_status` を読み込み、各データソースの取得状態を確認する。Phase 1各アナリストの出力ファイルに記載されたスキップ理由と突合し、「データ活用状況」テーブルを以下のルールで生成する:
    - `_data_status.{source}.status == "ok"` かつ Phase 1で活用された → ✓
    - `_data_status.{source}.status == "ok"` だがPhase 1でデータ不足（条件未充足）によりスキップ → △
    - `_data_status.{source}.status == "empty"` → △（備考: 「空レスポンス」）
    - `_data_status.{source}.status == "error"` → ✗（備考: エラー詳細を転記）
    - Phase 0で取得対象外（条件に該当せず） → -
2b. `{WORK_DIR}/trend_summary.md` が存在する場合、読み込んでセクション0.5（トレンド分析）を記載する。存在しない場合は「（初回分析のためトレンドデータなし）」と記載してセクション0.5をスキップする
3. テンプレートに従い、各セクションを実データで埋める
   - **セクション1.1（銘柄別保有状況）**: `{WORK_DIR}/portfolio_reference.md` の「セクション1.1」テーブルをそのまま転記する。数値の丸め・フォーマット変更は禁止
   - **セクション1.2（サマリー）**: `{WORK_DIR}/portfolio_reference.md` の「セクション1.2」をそのまま転記する
   - **セクション11.2（現行ポートフォリオ・改善前）**: `{WORK_DIR}/portfolio_reference.md` の「セクション1.1」テーブルをそのまま転記する（セクション11.2の注記参照）
   - **セクション13.2（用語解説）**: テンプレートの基本用語テーブルをそのまま転記し、レポート本文で使用したその他の専門用語（リバランス、アセットアロケーション、ヘッジ等）を追記する
   - **上記以外のセクション**: Phase 1の各分析ファイルと `portfolio_data.json` から統合して記載する
4. クロスレビュー結果をセクション9に記載:
   - **speedモード**: 「速度重視モードのためスキップ」と記載
   - **normalモード**: `crossreview-normal.md` に従い分析結果間の矛盾・整合性を検証し記載
   - **debateモード**: Phase 3のクロスレビュー結果ファイル（6ファイル）を読み込み、`crossreview-debate.md`の統合手順に従いセクション9を構成する
4a. セクション10（最適化提案）の各入替提案に外部検証結果を反映する:
   - `{WORK_DIR}/candidate_verification.md` が存在する場合: 各入替提案テンプレートの **合意度** 行の後に `**外部検証**: {判定}（{リスク付記}）` 行を追加する。判定・リスク付記は candidate_verification.md の各候補の検証結果から転記する
   - 検証結果が「要再検討」「非推奨」の場合: 提案に注記を付ける（例: 「※外部検証で構造的逆風が指摘されています」）
   - `{WORK_DIR}/candidate_verification.md` が存在しない場合（speedモード等）: 入替提案の外部検証行に「**外部検証**: 速度重視モードのためスキップ」と記載する
   - 入替提案でない項目（買い増し停止、現金運用等）には外部検証行は不要
5. `{WORK_DIR}/timing.json` を読み込み、Phase 3+4の開始時刻（phase_3_start）と完了時刻（phase_3_end, skill_end）を自身で記録した上で、所要時間を計算し「実行時間」セクション（セクション15）に記載する
5a. コンテキスト使用量の集計: timing.json の `session_jsonl_path` と `session_jsonl_start_line` を読み込み、セッションJSONLの開始行以降のusageデータを集計して「コンテキスト使用量」テーブル（セクション15内）に記載する。集計方法は後述の「コンテキスト使用量の集計方法」を参照。
6. `./reports/{username}/` ディレクトリを作成（存在しない場合）
7. **レポート本体を保存**: `./reports/{username}/YYYYMMDD_{username}.md`
7a. **metrics.json への追記（必須）**: レポート作成時に保持しているコンテキスト（portfolio_data.json、各analysis.md等）からメトリクスを抽出し、`reports/{username}/metrics.json` に追記する。

    **手順**:
    1. `reports/{username}/` ディレクトリが存在しない場合は作成する
    2. `reports/{username}/metrics.json` を読み込む（ファイルが存在しない場合は空配列 `[]` で初期化）
    3. 以下のJSONエントリを構築する:
       ```json
       {
         "date": "YYYY-MM-DD",
         "report_path": "reports/{username}/YYYYMMDD_{username}.md",
         "mode": "speed|normal|debate",
         "total_asset": 999999,
         "cash_balance": 99999,
         "cash_ratio": 0.0159,
         "holdings_count": 9,
         "holdings": [
           {"etf_code": "1475", "name": "銘柄名", "weight": 0.322, "pnl_rate": -0.009, "current_value": 313600}
         ],
         "overall_score": 99.9,
         "sharpe_ratio_portfolio": 9.99,
         "max_drawdown": -0.0228,
         "var_95": -0.016,
         "score_axes": {"dividend_power": 72, "cost_efficiency": 84, "scale_reliability": 96, "trading_quality": 95, "return_performance": 79},
         "top_actions": [{"action": "アクション名", "priority": "highest", "consensus": 100}],
         "key_risks": ["リスク1", "リスク2"]
       }
       ```
    4. 同日（date一致）のエントリが既に存在する場合は上書き、存在しない場合は追加する
    5. 配列を日付昇順でソートして保存する

    **メトリクス抽出元**:
    - `date`: レポートファイル名から抽出（YYYYMMDD → YYYY-MM-DD）
    - `report_path`: 保存したレポートファイルのパス
    - `mode`: 分析モード（speed/normal/debate）
    - `total_asset`: `portfolio_data.json` の `summary` セクション（総資産）
    - `cash_balance`: `portfolio_data.json` の `summary` セクション（現金残高）
    - `cash_ratio`: cash_balance / total_asset で算出
    - `holdings_count`, `holdings`: `portfolio_data.json` の `holdings` セクション（etf_code, name, weight, pnl_rate, current_value を含むオブジェクト配列）
    - `overall_score`: score_analysis.md（またはanalyst_*_analysis.md）の総合評価スコア
    - `sharpe_ratio_portfolio`: quant_analysis.md（またはanalyst_*_analysis.md、shared_calculations.md）のポートフォリオ加重シャープレシオ
    - `max_drawdown`, `var_95`: 同上の各リスク指標
    - `score_axes`: 5軸スコア（dividend_power, cost_efficiency, scale_reliability, trading_quality, return_performance）
    - `top_actions`: 最優先アクション（action, priority, consensus）
    - `key_risks`: 主要リスク（文字列配列）

    **注意**: 値が算出できなかった指標（データ不足でスキップされた場合等）は `null` を設定する。

7b. **数値整合性チェック（必須）**: レポート保存後、`{WORK_DIR}/portfolio_reference.md` のチェック値セクションとレポート内の数値を照合する。以下のBashコマンドを実行:

    ```bash
    python3 -c "
    import re, sys

    with open('/app/{WORK_DIR}/portfolio_reference.md', encoding='utf-8') as f:
        ref = f.read()
    with open('./reports/{username}/{REPORT_FILENAME}', encoding='utf-8') as f:
        report = f.read()

    # チェック値セクションから期待値を抽出
    ref_total = re.search(r'合計評価額:\s*([\d,]+)円', ref)
    ref_asset = re.search(r'総資産:\s*([\d,]+)円', ref)
    ref_count = re.search(r'銘柄数:\s*(\d+)', ref)
    ref_cash = re.search(r'現金残高:\s*([\d,]+)円', ref)

    # レポートのセクション1.2から実値を抽出
    report_total = re.search(r'合計評価額:\s*([\d,]+)円', report)
    report_asset = re.search(r'総資産:\s*([\d,]+)円', report)
    report_count = re.search(r'保有銘柄数:\s*(\d+)', report)
    report_cash = re.search(r'現金残高:\s*([\d,]+)円', report)

    errors = []
    if ref_total and report_total:
        if ref_total.group(1) != report_total.group(1):
            errors.append(f'合計評価額: 参照={ref_total.group(1)}円 vs レポート={report_total.group(1)}円')
    if ref_asset and report_asset:
        if ref_asset.group(1) != report_asset.group(1):
            errors.append(f'総資産: 参照={ref_asset.group(1)}円 vs レポート={report_asset.group(1)}円')
    if ref_count and report_count:
        if ref_count.group(1) != report_count.group(1):
            errors.append(f'銘柄数: 参照={ref_count.group(1)} vs レポート={report_count.group(1)}')
    if ref_cash and report_cash:
        if ref_cash.group(1) != report_cash.group(1):
            errors.append(f'現金残高: 参照={ref_cash.group(1)}円 vs レポート={report_cash.group(1)}円')

    if errors:
        print('数値整合性エラー:')
        for e in errors:
            print(f'  - {e}')
        print('portfolio_reference.md から再転記して修正してください')
        sys.exit(1)
    else:
        print('数値整合性チェック: OK')
    "
    ```

    **不一致があった場合**: レポートのセクション1.1/1.2/11.2を `portfolio_reference.md` の値で上書きし、再度保存する。
7c. **定量目標の整合性チェック（必須）**: セクション10の各Phase提案に記載された定量目標と、セクション11.1の指標比較テーブルの値が整合しているか確認する。
    - Phase 3後の最終目標値 = セクション11.1の「改善後」の値であること
    - 全Phase完了時の定量目標サマリーテーブルの最終目標値が11.1と一致すること
    - 不一致があった場合: セクション10の定量目標をセクション11.1の値に合わせて修正する
8. メインに保存先パスのみ返す

### まとめの作成指示

`report-guide.md` の「まとめ」セクションの注記に従って作成する。

**作成のポイント**:
1. **ポートフォリオ診断**: セクション2-8の定量分析結果から5軸の評価テーブルを構成。判定はデータに基づき客観的に行う
2. **構造的課題**: セクション9（クロスレビュー）で合意された構造的問題を優先し、個別銘柄ではなくポートフォリオ構造レベルで記載
3. **改善の方向性**: 構造的課題に対応する改善方向をラベル付け。セクション10の定量目標テーブルと重複する数値の再掲は避け、構造変化の方向性を示す
4. **次回への申し送り**: 観察期間設定中の銘柄、未実行の連続提案、データ不足でスキップされた分析項目を記載

**注意**: HISTORY.mdの更新やhistory/スナップショットの作成はこのスキルでは行わない。これらは `/publish-report confirm`（記事確定時）に実行される。記事化しない場合はユーザーが手動で更新を指示する。詳細は `reports/demo/PROMPT.md` の「週次分析フロー」を参照

---

## 実行時間の計算方法

- 各フェーズの所要時間 = end - start（秒単位で計算し、X分XX秒で表示）
- Phase 0a+0 合計 = max(phase_0a_end, phase_0_end) - min(phase_0a_start, phase_0_start)（並行実行のため）
- 合計 = skill_end - skill_start
- phase_3_start: timing.jsonを読み込んだ直後に現在時刻を記録
- phase_3_end / skill_end: レポート保存直前に現在時刻を記録

## コンテキスト使用量の集計方法

timing.json から `session_jsonl_path` と `session_jsonl_start_line` を読み込む。

```bash
python3 -c "
import json
with open('{WORK_DIR}/timing.json') as f:
    timing = json.load(f)
jsonl_path = timing.get('session_jsonl_path', '')
start_line = timing.get('session_jsonl_start_line', 0)
if not jsonl_path:
    print('session_jsonl_path not found')
else:
    totals = {'input_tokens': 0, 'output_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation_input_tokens': 0}
    try:
        with open(jsonl_path) as f:
            for i, line in enumerate(f):
                if i <= start_line:
                    continue
                try:
                    entry = json.loads(line)
                    usage = entry.get('message', {}).get('usage', {})
                    for key in totals:
                        totals[key] += usage.get(key, 0)
                except (json.JSONDecodeError, KeyError):
                    pass
        for key, val in totals.items():
            print(f'{key}: {val:,}')
    except (FileNotFoundError, PermissionError) as e:
        print(f'Error: {e}')
"
```

集計結果をレポートの「コンテキスト使用量」テーブルに記入する。トークン数はカンマ区切り（例: 1,234,567）で表示する。session_jsonl_pathが未設定の場合は「（計測データなし）」と記載する。
