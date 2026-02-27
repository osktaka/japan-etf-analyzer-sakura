# バリデーション + timing更新

## 概要

Phase 1/Phase 2完了後に、メインエージェントから委譲される出力ファイルの検証とtiming.json更新を実行する。

## パラメータ

- `WORK_DIR`: 作業ディレクトリパス
- `mode`: 分析モード（speed/normal/debate）
- `validation_phase`: 検証対象フェーズ（`phase1` or `phase2`）

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
