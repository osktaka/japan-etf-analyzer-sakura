#!/usr/bin/env python3
"""
Phase 1出力ファイルの品質検証スクリプト。

使い方:
    python validate_phase1.py {WORK_DIR} {MODE}

引数:
    WORK_DIR: 作業ディレクトリパス
    MODE: 分析モード（speed / normal / debate）

出力:
    JSON形式の検証結果をstdoutに出力。
    異常終了時はexit code 1 + stderrにエラーメッセージ。
"""

import json
import re
import sys
from pathlib import Path


def check_file_size(filepath: Path, min_bytes: int = 500) -> tuple[bool, int]:
    """ファイルサイズが最小バイト数以上かチェックする。"""
    if not filepath.exists():
        return False, 0
    size = filepath.stat().st_size
    return size >= min_bytes, size


def check_phase2_block(content: str) -> str:
    """PHASE2_CANDIDATESマーカーの存在をチェックする。"""
    has_start = "<!-- PHASE2_CANDIDATES_START -->" in content
    has_end = "<!-- PHASE2_CANDIDATES_END -->" in content
    if has_start and has_end:
        return "OK"
    missing = []
    if not has_start:
        missing.append("START")
    if not has_end:
        missing.append("END")
    return f"NG:missing_{'+'.join(missing)}"


def check_sharpe_ratio(content: str) -> str:
    """シャープレシオの数値が抽出可能かチェックする。"""
    patterns = [
        r"シャープレシオ[:：]?\s*\*{0,2}[\s]*(-?[\d.]+)",
        r"[Ss]harpe[:：]?\s*\*{0,2}[\s]*(-?[\d.]+)",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return f"OK:{m.group(1)}"
    return "NG:not_found"


def check_max_drawdown(content: str) -> str:
    """最大ドローダウンの数値（負値）が抽出可能かチェックする。"""
    patterns = [
        r"最大ドローダウン[:：]?\s*\*{0,2}[\s]*(-[\d.]+)%",
        r"[Mm]ax\s*[Dd]rawdown[:：]?\s*\*{0,2}[\s]*(-[\d.]+)%",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return f"OK:{m.group(1)}%"
    return "NG:not_found"


def check_score_range(content: str) -> str:
    """スコア値が全銘柄0-100範囲かチェックする。"""
    # "1234...XX点" パターンで銘柄コードとスコアを抽出
    pattern = r"(\d{4})[^\n]*?(\d+)点"
    matches = re.findall(pattern, content)
    if not matches:
        return "NG:no_scores"
    out_of_range = []
    for code, score_str in matches:
        score = int(score_str)
        if score < 0 or score > 100:
            out_of_range.append(f"{code}={score}")
    if out_of_range:
        return f"NG:{','.join(out_of_range)}"
    return f"OK:{len(matches)}銘柄"


def check_weight_sum(content: str) -> str:
    """保有比率合計が0.98-1.02の範囲かチェックする。"""
    # パターン1: "合計: 1.00" や "保有比率合計: 1.00" の小数値（0.0〜1.0）
    # スコアアナリスト仕様: 保有比率は小数値（0.0〜1.0）で扱う
    pattern_total = r"(?:保有比率)?合計[:：]\s*([\d.]+)"
    m = re.search(pattern_total, content)
    if m:
        total = float(m.group(1))
        if 0.98 <= total <= 1.02:
            return f"OK:{total:.2f}"
        # 合計が1を超えているなら%形式の可能性を確認
        if total > 1.02:
            # %形式（例: 合計: 100.0）の場合は100で割る
            total_pct = total / 100
            if 0.98 <= total_pct <= 1.02:
                return f"OK:{total_pct:.2f}"
        return f"NG:{total:.2f}"

    # パターン2: テーブル行の%形式 | ... | XX.X% | （銘柄コード不要）
    pattern_pct_table = r"(\d+\.?\d*)%\s*\|"
    matches_pct = re.findall(pattern_pct_table, content)
    if matches_pct:
        total = sum(float(v) for v in matches_pct) / 100
        if 0.98 <= total <= 1.02:
            return f"OK:{total:.2f}"
        return f"NG:{total:.2f}"

    # パターン3: "保有比率: XX.X%" や "比率: XX.X%" の個別記述
    pattern_pct_label = r"保有比率[:：]?\s*([\d.]+)%"
    matches_label = re.findall(pattern_pct_label, content)
    if matches_label:
        total = sum(float(v) for v in matches_label) / 100
        if 0.98 <= total <= 1.02:
            return f"OK:{total:.2f}"
        return f"NG:{total:.2f}"

    return "NG:no_weights"


def check_allocation_sum(content: str, label: str) -> str:
    """配分合計が98-102%の範囲かチェックする。"""
    # テーブル行からパーセンテージを抽出
    # | 地域名 | XX.X% | のパターン
    pattern = r"\|\s*[^|]+\s*\|\s*([\d.]+)%\s*\|"
    matches = re.findall(pattern, content)
    if not matches:
        return f"NG:no_{label}"
    total = sum(float(v) for v in matches)
    if 98.0 <= total <= 102.0:
        return f"OK:{total:.1f}"
    return f"NG:{total:.1f}"


def check_shared_calc_ref(content: str) -> str:
    """05_shared_calculations.mdへの言及をチェックする。"""
    if "05_shared_calculations" in content:
        return "OK"
    return "NG:no_reference"


def validate_speed_normal(work_dir: Path) -> dict:
    """speed/normalモードの検証を実行する。"""
    results = {}
    warnings = []

    # quant_analysis
    quant_path = work_dir / "10_quant_analysis.md"
    size_ok, size = check_file_size(quant_path)
    if not size_ok:
        results["quant"] = {
            "status": "NG",
            "size": size,
            "checks": {"file_size": f"NG:{size}B"},
        }
        warnings.append(f"quant: ファイルサイズ不足 {size}B < 500B")
    else:
        content = quant_path.read_text(encoding="utf-8")
        sharpe = check_sharpe_ratio(content)
        max_dd = check_max_drawdown(content)
        phase2 = check_phase2_block(content)
        checks = {"sharpe": sharpe, "max_dd": max_dd, "phase2_block": phase2}
        has_ng = any(v.startswith("NG") for v in checks.values())
        results["quant"] = {
            "status": "NG" if has_ng else "OK",
            "size": size,
            "checks": checks,
        }
        if has_ng:
            for k, v in checks.items():
                if v.startswith("NG"):
                    warnings.append(f"quant: {k}={v}")

    # score_analysis
    score_path = work_dir / "10_score_analysis.md"
    size_ok, size = check_file_size(score_path)
    if not size_ok:
        results["score"] = {
            "status": "NG",
            "size": size,
            "checks": {"file_size": f"NG:{size}B"},
        }
        warnings.append(f"score: ファイルサイズ不足 {size}B < 500B")
    else:
        content = score_path.read_text(encoding="utf-8")
        score_range = check_score_range(content)
        weight_sum = check_weight_sum(content)
        phase2 = check_phase2_block(content)
        checks = {
            "score_range": score_range,
            "weight_sum": weight_sum,
            "phase2_block": phase2,
        }
        has_ng = any(v.startswith("NG") for v in checks.values())
        results["score"] = {
            "status": "NG" if has_ng else "OK",
            "size": size,
            "checks": checks,
        }
        if has_ng:
            for k, v in checks.items():
                if v.startswith("NG"):
                    warnings.append(f"score: {k}={v}")

    # allocation_analysis（存在しない場合はスキップ）
    alloc_path = work_dir / "10_allocation_analysis.md"
    if not alloc_path.exists():
        results["allocation"] = {
            "status": "SKIP",
            "size": 0,
            "checks": {"skipped": "file_not_found"},
        }
    else:
        size_ok, size = check_file_size(alloc_path)
        if not size_ok:
            results["allocation"] = {
                "status": "NG",
                "size": size,
                "checks": {"file_size": f"NG:{size}B"},
            }
            warnings.append(f"allocation: ファイルサイズ不足 {size}B < 500B")
        else:
            content = alloc_path.read_text(encoding="utf-8")
            phase2 = check_phase2_block(content)
            # 地域配分とセクター配分のチェック
            # ファイル全体から地域セクションとセクターセクションを分割
            region_sum = check_region_allocation(content)
            sector_sum = check_sector_allocation(content)
            checks = {
                "region_sum": region_sum,
                "sector_sum": sector_sum,
                "phase2_block": phase2,
            }
            has_ng = any(v.startswith("NG") for v in checks.values())
            results["allocation"] = {
                "status": "NG" if has_ng else "OK",
                "size": size,
                "checks": checks,
            }
            if has_ng:
                for k, v in checks.items():
                    if v.startswith("NG"):
                        warnings.append(f"allocation: {k}={v}")

    return results, warnings


def check_region_allocation(content: str) -> str:
    """地域配分合計が98-102%かチェックする。"""
    # 地域セクションを探す
    region_section = extract_section(content, ["地域", "リージョン", "国別", "地域配分"])
    if region_section:
        return check_allocation_sum(region_section, "region")
    # セクションが見つからない場合、ファイル全体で試行
    return check_allocation_sum(content, "region")


def check_sector_allocation(content: str) -> str:
    """セクター配分合計が98-102%かチェックする。"""
    # セクターセクションを探す
    sector_section = extract_section(
        content, ["セクター", "業種", "セクター配分"]
    )
    if sector_section:
        return check_allocation_sum(sector_section, "sector")
    # セクションが見つからない場合、ファイル全体で試行
    return check_allocation_sum(content, "sector")


def extract_section(content: str, keywords: list[str]) -> str | None:
    """キーワードを含む見出しのセクションを抽出する。"""
    for keyword in keywords:
        pattern = rf"(#{1,3}\s*.*?{keyword}.*?\n)(.*?)(?=\n#{1,3}\s|\Z)"
        m = re.search(pattern, content, re.DOTALL)
        if m:
            return m.group(1) + m.group(2)
    return None


def validate_debate(work_dir: Path) -> dict:
    """debateモードの検証を実行する。"""
    results = {}
    warnings = []
    analysts = ["a", "b", "c", "d", "e"]

    for analyst in analysts:
        key = f"analyst_{analyst}"
        filepath = work_dir / f"10_analyst_{analyst}_analysis.md"
        size_ok, size = check_file_size(filepath)

        if not size_ok:
            results[key] = {
                "status": "NG",
                "size": size,
                "checks": {"file_size": f"NG:{size}B"},
            }
            warnings.append(f"{key}: ファイルサイズ不足 {size}B < 500B")
            continue

        content = filepath.read_text(encoding="utf-8")
        phase2 = check_phase2_block(content)
        shared_ref = check_shared_calc_ref(content)
        checks = {"phase2_block": phase2, "shared_calc_ref": shared_ref}
        has_ng = any(v.startswith("NG") for v in checks.values())
        results[key] = {
            "status": "NG" if has_ng else "OK",
            "size": size,
            "checks": checks,
        }
        if has_ng:
            for k, v in checks.items():
                if v.startswith("NG"):
                    warnings.append(f"{key}: {k}={v}")

    return results, warnings


def determine_overall_status(results: dict) -> str:
    """全体ステータスを決定する。"""
    for entry in results.values():
        if entry["status"] == "NG":
            return "WARN"
    return "OK"


def main():
    if len(sys.argv) < 3:
        print(
            "使い方: python validate_phase1.py {WORK_DIR} {MODE}\n"
            "  WORK_DIR: 作業ディレクトリパス\n"
            "  MODE: speed / normal / debate",
            file=sys.stderr,
        )
        sys.exit(1)

    work_dir = Path(sys.argv[1])
    mode = sys.argv[2].lower()

    if not work_dir.exists():
        print(
            f"エラー: 作業ディレクトリが存在しません: {work_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    if mode not in ("speed", "normal", "debate"):
        print(
            f"エラー: 不正なモード: {mode}（speed / normal / debate）",
            file=sys.stderr,
        )
        sys.exit(1)

    if mode in ("speed", "normal"):
        results, warnings = validate_speed_normal(work_dir)
    else:
        results, warnings = validate_debate(work_dir)

    overall_status = determine_overall_status(results)

    output = {
        "status": overall_status,
        "results": results,
        "warnings": warnings,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
