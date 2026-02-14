# Phase 3+4: 統合レポート作成・保存 指示書

## 前提

- 作業ディレクトリ: `{WORK_DIR}`（メインエージェントから渡される）
- Docker内パス: `/app/{WORK_DIR}`

## データ受け渡しルール

- **入力**: `{WORK_DIR}/` 配下の全分析結果ファイル、`{skill_dir}/report-template.md`、`{skill_dir}/report-writing-guide.md`
- **出力**: `./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`
- **メインへの戻り値**: 「レポート保存完了: ./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md」の1行のみ。データ全文やテーブル全体を返さないこと

---

## 統合エージェントの役割

統合エージェント（general-purpose）は、`{WORK_DIR}` 配下の全分析結果ファイルを読み込み、`report-template.md` のテンプレートに従ってレポートを作成・保存する。

## 入力ファイル

### 共通（全モード）

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/market_environment.md` | 市場環境サマリー |
| `{WORK_DIR}/portfolio_data.json` | 全収集データ |
| `{WORK_DIR}/timing.json` | 各フェーズの実行時間記録 |
| `{WORK_DIR}/portfolio_reference.md` | セクション1・11.2用markdownテーブル（プログラマティック生成） |
| `{skill_dir}/report-template.md` | レポート出力形式テンプレート |
| `{skill_dir}/report-writing-guide.md` | レポート書き方ガイド（注意事項・記載例） |

### speed/normalモード

| ファイル | 内容 |
|---------|------|
| `{WORK_DIR}/quant_analysis.md` | 定量リスク・リターン分析結果 |
| `{WORK_DIR}/score_analysis.md` | スコア・モメンタム分析結果 |
| `{WORK_DIR}/allocation_analysis.md` | アセットアロケーション分析結果（存在する場合） |

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

1. レポートファイル: `./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`（**全ユーザー共通で`reports/`直下に保存**）
2. **メインへの戻り値**: 「レポート保存完了: ./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md」の1行のみ

---

## レポート作成手順

1. `{WORK_DIR}/` 配下の全ファイルを読み込む
2. `{skill_dir}/report-template.md` と `{skill_dir}/report-writing-guide.md` を読み込む
2a. `portfolio_data.json` の `_metadata._data_status` を読み込み、各データソースの取得状態を確認する。Phase 1各アナリストの出力ファイルに記載されたスキップ理由と突合し、「データ活用状況」テーブルを以下のルールで生成する:
    - `_data_status.{source}.status == "ok"` かつ Phase 1で活用された → ✓
    - `_data_status.{source}.status == "ok"` だがPhase 1でデータ不足（条件未充足）によりスキップ → △
    - `_data_status.{source}.status == "empty"` → △（備考: 「空レスポンス」）
    - `_data_status.{source}.status == "error"` → ✗（備考: エラー詳細を転記）
    - Phase 0で取得対象外（条件に該当せず） → -
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
5. `{WORK_DIR}/timing.json` を読み込み、Phase 3+4の開始時刻（phase_3_start）と完了時刻（phase_3_end, skill_end）を自身で記録した上で、所要時間を計算し「実行時間」セクション（セクション14）に記載する
6. `./reports/` ディレクトリを作成（存在しない場合）
7. **レポート本体を保存**: `./reports/YYYYMMDD_HHMMSS_portfolio_analysis_{username}.md`
7a. **数値整合性チェック（必須）**: レポート保存後、`{WORK_DIR}/portfolio_reference.md` のチェック値セクションとレポート内の数値を照合する。以下のBashコマンドを実行:

    ```bash
    python3 -c "
    import re, sys

    with open('/app/{WORK_DIR}/portfolio_reference.md', encoding='utf-8') as f:
        ref = f.read()
    with open('./reports/{REPORT_FILENAME}', encoding='utf-8') as f:
        report = f.read()

    # チェック値セクションから期待値を抽出
    ref_total = re.search(r'合計評価額:\s*([\d,]+)円', ref)
    ref_asset = re.search(r'総資産:\s*([\d,]+)円', ref)

    # レポートのセクション1.2から実値を抽出
    report_total = re.search(r'合計評価額:\s*([\d,]+)円', report)
    report_asset = re.search(r'総資産:\s*([\d,]+)円', report)

    errors = []
    if ref_total and report_total:
        if ref_total.group(1) != report_total.group(1):
            errors.append(f'合計評価額: 参照={ref_total.group(1)}円 vs レポート={report_total.group(1)}円')
    if ref_asset and report_asset:
        if ref_asset.group(1) != report_asset.group(1):
            errors.append(f'総資産: 参照={ref_asset.group(1)}円 vs レポート={report_asset.group(1)}円')

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
7b. **定量目標の整合性チェック（必須）**: セクション10の各Phase提案に記載された定量目標と、セクション11.1の指標比較テーブルの値が整合しているか確認する。
    - Phase 3後の最終目標値 = セクション11.1の「改善後」の値であること
    - 全Phase完了時の定量目標サマリーテーブルの最終目標値が11.1と一致すること
    - 不一致があった場合: セクション10の定量目標をセクション11.1の値に合わせて修正する
8. メインに保存先パスのみ返す

### まとめ（初心者向け）の作成指示

`report-writing-guide.md` の「まとめ（初心者向け）の作成指示」に従って作成する。

**注意**: HISTORY.mdの更新やhistory/スナップショットの作成はこのスキルでは行わない。これらは `/publish-report confirm`（記事確定時）に実行される。記事化しない場合はユーザーが手動で更新を指示する。詳細は `reports/demo/PROMPT.md` の「週次分析フロー」を参照

---

## 実行時間の計算方法

- 各フェーズの所要時間 = end - start（秒単位で計算し、X分XX秒で表示）
- Phase 0a+0 合計 = max(phase_0a_end, phase_0_end) - min(phase_0a_start, phase_0_start)（並行実行のため）
- 合計 = skill_end - skill_start
- phase_3_start: timing.jsonを読み込んだ直後に現在時刻を記録
- phase_3_end / skill_end: レポート保存直前に現在時刻を記録
