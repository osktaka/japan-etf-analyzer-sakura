# バリデーション + timing更新

## 概要

Phase 0/Phase 1/Phase 2完了後に、メインエージェントから委譲される出力ファイルの検証とtiming.json更新を実行する。

## パラメータ

- `WORK_DIR`: 作業ディレクトリパス
- `mode`: 分析モード（speed/normal/debate）
- `validation_phase`: 検証対象フェーズ（`phase0` or `phase1` or `phase2`）

## timing.json 拡張メトリクス

以下のフィールドをtiming.jsonに記録する。全てオプショナル（旧形式との後方互換を維持）。

### スキル開始時に記録するフィールド

timing.jsonの初期化時（skill_start記録時）に、以下も合わせて記録すること:

- `mode`: 実行モード文字列。`"speed"` / `"normal"` / `"debate"` のいずれか
- `holdings_count`: 保有銘柄数（整数）。Phase 0のAPI取得結果から算出

### Phase 0完了後に記録するフィールド

Phase 0検証後（phase_0_end記録後）に、以下も合わせて記録すること:

- `phase_0_file_size`: `00_portfolio_data.json` のバイト数（整数）。`os.path.getsize()` で取得

### スキル完了時に自動算出するフィールド

skill_end記録時に、以下を自動算出して記録すること:

- `total_duration_sec`: skill_start〜skill_endの秒数（浮動小数点）。skill_startとskill_endのISO形式タイムスタンプから算出

### 記録例

```json
{
  "skill_start": "2026-03-08T18:00:19+09:00",
  "mode": "debate",
  "holdings_count": 8,
  "phase_0_end": "2026-03-08T18:01:27",
  "phase_0_file_size": 15234,
  "phase_05_end": "2026-03-08T18:09:13.193331",
  "phase_1_end": "2026-03-08T18:18:22.909135",
  "phase_2_end": "2026-03-08T18:20:50.139516",
  "phase_3_round1_end": "2026-03-08T18:26:19.709902",
  "phase_3_round2_end": "2026-03-08T18:29:28.078015",
  "phase_4_end": "2026-03-08T18:40:43.621398",
  "skill_end": "2026-03-08T18:40:43.621398",
  "total_duration_sec": 2424.62
}
```

### 後方互換性

- 新フィールドは全てオプショナル。旧形式のtiming.jsonにこれらのフィールドがなくても、集計スクリプト（`timing_summary.py`）は正常に動作する
- `mode` フィールドがない場合、集計時は「不明」として分類される
- `total_duration_sec` がない場合、集計時にskill_start/skill_endから自動算出される

## Phase 0完了後の検証

### Phase 0出力の品質検証

以下のPythonスクリプトを実行して品質検証を行う:

```bash
python {skill_dir}/scripts/validate_phase0.py {WORK_DIR}
```

スクリプトはJSON結果をstdoutに出力する。結果のstatusフィールドを確認する。

- **NG**: `00_portfolio_data.json` の構造・数値整合性に問題あり → Phase 0をやり直す（1回のみ）
- **WARN**: データ取得エラーが3件以上 → 警告を記録して続行
- **OK**: 全チェック通過

### Phase 0検証NGの場合の自己修正ルール

- NG項目がある場合 → メインエージェントに具体的なNG内容を報告し、Phase 0の再実行を促す（**1回のみ**）
- 再実行後もNG → 「修正試行済み・品質警告あり」として続行し、最終レポートの「注意事項」に警告を記載
- **スクリプト異常終了時**: `00_portfolio_data.json` の `wc -c` でサイズ100バイト以上を確認するフォールバックを実行し、警告を記録して続行

### Phase 0検証後のフロー

Phase 0検証が完了したら、結果をメインエージェントに返す。Phase 1検証（`validate_phase1.py`）はPhase 1完了後に別途 `validation_phase=phase1` で呼び出される。

## Phase 1完了後の検証

### Phase 1出力の品質検証

以下のPythonスクリプトを実行して品質検証を行う:

```bash
python {skill_dir}/scripts/validate_phase1.py {WORK_DIR} {mode}
```

スクリプトはJSON結果をstdoutに出力する。結果のstatusフィールドを確認する。

### 品質検証NGの場合の自己修正ルール

- スクリプト結果にNG項目がある場合 → **NG該当のanalystのみ**に具体的なNG項目を伝えて再実行（**1回のみ**、他のOK analystは再実行しない）
- 再実行後もNG → 「修正試行済み・品質警告あり」として続行し、最終レポートの「注意事項」に警告を記載
- speedモード時: 所要時間優先のため再実行をスキップし、警告のみ記録
- **スクリプト異常終了時**（Python実行失敗等）: 各ファイルの `wc -c` でサイズ500バイト以上を確認するフォールバックを実行し、警告を記録して続行

### timing.json一括書き込み

以下のPythonスクリプトを実行:

```python
import json, os, datetime

wd = '{WORK_DIR}'

def mtime(f):
    try:
        return datetime.datetime.fromtimestamp(
            os.path.getmtime(os.path.join(wd, f))
        ).isoformat()
    except:
        return None

with open(os.path.join(wd, 'timing.json')) as f:
    data = json.load(f)

updates = {
    'phase_0a_end': mtime('0a_market_environment.md'),
    'phase_0b_end': mtime('0b_trend_summary.md'),
    'phase_0_end': mtime('00_portfolio_data.json'),
    'phase_05_end': mtime('05_shared_calculations.md'),
    'phase_1_end': datetime.datetime.now().isoformat()
}
data.update({k: v for k, v in updates.items() if v})

with open(os.path.join(wd, 'timing.json'), 'w') as f:
    json.dump(data, f, indent=2)

print('timing updated')
```

### 戻り値フォーマット

成功時: `「検証完了: quant=OK(2.1KB) score=OK(1.8KB) alloc=OK(1.5KB) timing更新済み」`
WARN時: `「検証完了(WARN): quant=OK(2.1KB) score=WARN(score_range:NG) alloc=OK(1.5KB) timing更新済み」`
debateモード: `「検証完了: A=OK(3.2KB) B=OK(2.8KB) C=OK(3.0KB) D=OK(2.5KB) E=OK(2.7KB) timing更新済み」`
フォールバック時: `「検証完了(フォールバック): quant=OK(2.1KB) score=OK(1.8KB) alloc=OK(1.5KB) timing更新済み ※スクリプト実行失敗」`

## Phase 2完了後の検証

### 出力ファイルチェック

- `{WORK_DIR}/20_candidate_verification.md` - 200バイト以上

### timing.json追記

```python
import json, os, datetime

wd = '{WORK_DIR}'

with open(os.path.join(wd, 'timing.json')) as f:
    data = json.load(f)

data['phase_2_end'] = datetime.datetime.now().isoformat()

with open(os.path.join(wd, 'timing.json'), 'w') as f:
    json.dump(data, f, indent=2)

print('phase_2 timing updated')
```

### 戻り値フォーマット

成功時: `「Phase 2検証完了: candidate_verification=OK(1.2KB) timing更新済み」`
失敗時: `「Phase 2検証失敗: candidate_verification.mdが200バイト未満（XXバイト）」`
