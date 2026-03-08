"""portfolio-analysis スキルの実行時間統計集計スクリプト.

.tmp/pf_*/timing.json を収集し、モード別・期間別の統計を出力する。
旧形式（modeフィールドなし）も「不明」として処理する。
"""

import glob
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """ISO形式タイムスタンプをdatetimeに変換する."""
    if not ts_str:
        return None
    try:
        # タイムゾーン付き (+09:00)
        if "+" in ts_str or ts_str.endswith("Z"):
            ts_str_naive = ts_str.split("+")[0].split("Z")[0]
            return datetime.fromisoformat(ts_str_naive)
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def calc_duration_sec(start_str: str, end_str: str) -> Optional[float]:
    """2つのタイムスタンプ間の秒数を算出する."""
    start = parse_timestamp(start_str)
    end = parse_timestamp(end_str)
    if start and end:
        delta = (end - start).total_seconds()
        return delta if delta >= 0 else None
    return None


def calc_phase_durations(data: dict) -> dict:
    """各Phaseの所要時間を算出する."""
    durations = {}

    # total
    total = data.get("total_duration_sec")
    if total is None:
        total = calc_duration_sec(
            data.get("skill_start", ""), data.get("skill_end", "")
        )
    durations["total"] = total

    # Phase 0: skill_start -> phase_0_end
    durations["phase_0"] = calc_duration_sec(
        data.get("skill_start", ""), data.get("phase_0_end", "")
    )

    # Phase 0.5: phase_0_end -> phase_05_end
    durations["phase_05"] = calc_duration_sec(
        data.get("phase_0_end", ""), data.get("phase_05_end", "")
    )

    # Phase 1: phase_05_end or phase_0_end -> phase_1_end
    phase1_start = data.get("phase_05_end") or data.get("phase_0_end", "")
    durations["phase_1"] = calc_duration_sec(phase1_start, data.get("phase_1_end", ""))

    # Phase 2: phase_1_end -> phase_2_end
    durations["phase_2"] = calc_duration_sec(
        data.get("phase_1_end", ""), data.get("phase_2_end", "")
    )

    # Phase 3 round1: phase_2_end or phase_1_end -> phase_3_round1_end
    phase3_start = data.get("phase_2_end") or data.get("phase_1_end", "")
    # 旧形式: phase_3_start -> phase_3_end
    if "phase_3_end" in data and "phase_3_round1_end" not in data:
        durations["phase_3"] = calc_duration_sec(
            data.get("phase_3_start", phase3_start), data.get("phase_3_end", "")
        )
    else:
        durations["phase_3_r1"] = calc_duration_sec(
            data.get("phase_3_round1_start", phase3_start),
            data.get("phase_3_round1_end", ""),
        )
        durations["phase_3_r2"] = calc_duration_sec(
            data.get("phase_3_round2_start", ""),
            data.get("phase_3_round2_end", ""),
        )

    # Phase 4: phase_4_start -> phase_4_end
    durations["phase_4"] = calc_duration_sec(
        data.get("phase_4_start", ""), data.get("phase_4_end", "")
    )

    return {k: v for k, v in durations.items() if v is not None}


def percentile(values: list, p: float) -> Optional[float]:
    """リストからパーセンタイル値を算出する."""
    if not values:
        return None
    sorted_vals = sorted(values)
    idx = (len(sorted_vals) - 1) * p / 100.0
    lower = int(idx)
    upper = lower + 1
    if upper >= len(sorted_vals):
        return sorted_vals[-1]
    weight = idx - lower
    return sorted_vals[lower] * (1 - weight) + sorted_vals[upper] * weight


def format_duration(sec: Optional[float]) -> str:
    """秒数を mm:ss 形式にフォーマットする."""
    if sec is None:
        return "-"
    minutes = int(sec) // 60
    seconds = int(sec) % 60
    return f"{minutes:2d}:{seconds:02d}"


def collect_timing_data(base_dir: str) -> list:
    """timing.jsonファイルを収集してパースする."""
    pattern = os.path.join(base_dir, ".tmp", "pf_*", "timing.json")
    files = sorted(glob.glob(pattern))
    results = []
    for fpath in files:
        try:
            with open(fpath) as f:
                data = json.load(f)
            data["_file_path"] = fpath
            data["_dir_name"] = os.path.basename(os.path.dirname(fpath))
            results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return results


def classify_mode(data: dict) -> str:
    """実行モードを判定する."""
    mode = data.get("mode", "")
    if mode in ("speed", "normal", "debate"):
        return mode
    return "unknown"


def print_stats(label: str, entries: list):
    """統計情報を出力する."""
    if not entries:
        print(f"  {label}: データなし")
        return

    totals = [e.get("total") for e in entries if e.get("total") is not None]
    count = len(entries)
    total_count = len(totals)

    print(f"  {label}: {count}回実行")
    if not totals:
        print("    所要時間データなし")
        return

    avg = sum(totals) / total_count
    p50 = percentile(totals, 50)
    p95 = percentile(totals, 95)
    min_val = min(totals)
    max_val = max(totals)

    print(f"    合計所要時間: 平均 {format_duration(avg)}, "
          f"P50 {format_duration(p50)}, P95 {format_duration(p95)}")
    print(f"    範囲: {format_duration(min_val)} ~ {format_duration(max_val)}")

    # Phase別の統計
    phase_keys = ["phase_0", "phase_05", "phase_1", "phase_2",
                  "phase_3", "phase_3_r1", "phase_3_r2", "phase_4"]
    phase_labels = {
        "phase_0": "Phase 0  ",
        "phase_05": "Phase 0.5",
        "phase_1": "Phase 1  ",
        "phase_2": "Phase 2  ",
        "phase_3": "Phase 3  ",
        "phase_3_r1": "Phase 3-1",
        "phase_3_r2": "Phase 3-2",
        "phase_4": "Phase 4  ",
    }
    has_phase_data = False
    for key in phase_keys:
        values = [e.get(key) for e in entries if e.get(key) is not None]
        if values:
            if not has_phase_data:
                print("    --- Phase別 ---")
                has_phase_data = True
            pavg = sum(values) / len(values)
            pp50 = percentile(values, 50)
            print(f"    {phase_labels[key]}: "
                  f"平均 {format_duration(pavg)}, "
                  f"P50 {format_duration(pp50)} ({len(values)}件)")


def main():
    """メイン処理."""
    # プロジェクトルート特定
    script_dir = Path(__file__).resolve().parent
    # .claude/skills/portfolio-analysis/scripts/ -> project root
    project_root = script_dir.parent.parent.parent.parent

    print(f"=== portfolio-analysis 実行時間統計 ===")
    print(f"プロジェクト: {project_root}")
    print()

    # データ収集
    all_data = collect_timing_data(str(project_root))
    if not all_data:
        print("timing.jsonが見つかりません。")
        return

    print(f"検出ファイル数: {len(all_data)}")
    print()

    # Phase所要時間算出
    all_durations = []
    for data in all_data:
        durations = calc_phase_durations(data)
        durations["_mode"] = classify_mode(data)
        durations["_skill_start"] = data.get("skill_start", "")
        durations["_dir_name"] = data.get("_dir_name", "")
        if data.get("holdings_count") is not None:
            durations["_holdings_count"] = data["holdings_count"]
        if data.get("phase_0_file_size") is not None:
            durations["_phase_0_file_size"] = data["phase_0_file_size"]
        all_durations.append(durations)

    # モード別集計
    modes = {"speed": [], "normal": [], "debate": [], "unknown": []}
    for d in all_durations:
        modes[d["_mode"]].append(d)

    print("--- モード別統計（全期間）---")
    for mode_name in ["speed", "normal", "debate", "unknown"]:
        label = mode_name if mode_name != "unknown" else "不明"
        print_stats(label, modes[mode_name])
    print()

    # 全体統計
    print("--- 全体統計 ---")
    print_stats("全モード合計", all_durations)
    print()

    # 期間別比較
    # skill_startでソート
    sorted_durations = sorted(
        all_durations, key=lambda d: d.get("_skill_start", "")
    )

    print("--- 期間別比較 ---")
    if len(sorted_durations) >= 10:
        print_stats("直近10回", sorted_durations[-10:])
    if len(sorted_durations) >= 30:
        print_stats("直近30回", sorted_durations[-30:])
    print_stats("全期間", sorted_durations)
    print()

    # 直近5回の詳細
    print("--- 直近5回の詳細 ---")
    recent = sorted_durations[-5:]
    for d in recent:
        mode_str = d["_mode"] if d["_mode"] != "unknown" else "不明"
        total_str = format_duration(d.get("total"))
        dir_name = d.get("_dir_name", "?")
        extra = []
        if "_holdings_count" in d:
            extra.append(f"銘柄数={d['_holdings_count']}")
        if "_phase_0_file_size" in d:
            extra.append(f"P0={d['_phase_0_file_size']}B")
        extra_str = f" ({', '.join(extra)})" if extra else ""
        print(f"  {dir_name}: {mode_str} {total_str}{extra_str}")


if __name__ == "__main__":
    main()
