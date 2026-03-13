"""market-outlook精度集計スクリプト

AM/PMレポートペアを走査し、方向性一致率・レンジ包含率・CME乖離等を集計する。

使い方:
  python backend/scripts/market_outlook_accuracy.py --month 2026-03
  python backend/scripts/market_outlook_accuracy.py --all
  python backend/scripts/market_outlook_accuracy.py --month 2026-03 --json
  python backend/scripts/market_outlook_accuracy.py --all --csv
"""

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path
from statistics import mean, median

# プロジェクトルートを特定（backend/scripts/ -> backend/ -> project root）
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

import os

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

REPORTS_DIR = PROJECT_ROOT / "reports" / "market-outlook"


# ---------------------------------------------------------------------------
# YAML フロントマターパース
# ---------------------------------------------------------------------------

def parse_yaml_frontmatter(text):
    """YAMLフロントマターを正規表現でパースする。"""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    return _parse_yaml_block(m.group(1))


def _parse_yaml_block(block):
    """簡易YAMLパーサー（ネスト1段のみ対応）。"""
    result = {}
    current_key = None
    for line in block.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                result[key] = _cast_yaml_value(val)
            else:
                result[key] = {}
                current_key = key
        elif indent > 0 and current_key:
            key, _, val = line.strip().partition(":")
            key = key.strip()
            val = val.strip()
            if isinstance(result.get(current_key), dict):
                result[current_key][key] = _cast_yaml_value(val)
    return result


def _cast_yaml_value(val):
    """文字列を適切な型にキャストする。"""
    val = val.strip('"').strip("'")
    # bool値
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() == "null" or val == "~":
        return None
    if val.isdigit():
        return int(val)
    try:
        return float(val)
    except ValueError:
        return val


# ---------------------------------------------------------------------------
# AMレポートパース
# ---------------------------------------------------------------------------

def parse_am_report(filepath):
    """AMレポートから予想データを抽出する。"""
    text = filepath.read_text(encoding="utf-8")
    data = {}

    # YAMLフロントマターから取得
    fm = parse_yaml_frontmatter(text)
    pred = fm.get("prediction", {})
    if isinstance(pred, dict):
        data.update(pred)

    # フロントマターに無い場合、本文からフォールバックパース
    if "direction" not in data:
        data["direction"] = _parse_direction_from_body(text)
    if "confidence" not in data:
        data["confidence"] = _parse_confidence_from_body(text)
    if "cme_nikkei" not in data:
        data["cme_nikkei"] = _parse_cme_from_body(text)

    return data


def _parse_direction_from_body(text):
    """本文の「**上昇** 予想」やHTMLコメントから方向性を抽出する。"""
    # HTMLコメント形式: <!-- prediction: 上昇 -->
    m = re.search(r"<!--\s*prediction:\s*(上昇|下落|横ばい)\s*-->", text)
    if m:
        return m.group(1)
    # 本文パターン: **上昇** 予想
    m = re.search(r"\*\*(上昇|下落|横ばい)\*\*\s*予想", text)
    return m.group(1) if m else None


def _parse_confidence_from_body(text):
    """本文の「確信度: 中」やHTMLコメントから確信度を抽出する。"""
    # HTMLコメント形式: <!-- confidence: 中 -->
    m = re.search(r"<!--\s*confidence:\s*(高|中|低)\s*-->", text)
    if m:
        return m.group(1)
    # 本文パターン: 確信度: 中 / データ整合性: 中
    m = re.search(r"(?:確信度|データ整合性)[:\s]*\s*(高|中|低)", text)
    return m.group(1) if m else None


def _parse_cme_from_body(text):
    """主要指標テーブルやHTMLコメントからCME日経先物の値を抽出する。"""
    # HTMLコメント形式: <!-- cme_nikkei: 39500 -->
    m = re.search(r"<!--\s*cme_nikkei:\s*([\d,]+)\s*-->", text)
    if m:
        return int(m.group(1).replace(",", ""))
    # テーブルパターン: CME日経先物 | 39,500
    m = re.search(r"CME日経先物\s*\|\s*([\d,]+)", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


# ---------------------------------------------------------------------------
# PMレポートパース
# ---------------------------------------------------------------------------

def parse_pm_comparison(filepath):
    """PMレポートの精度データを取得する。

    1. YAMLフロントマターの accuracy キーを優先的にチェック
    2. なければ既存の「AM予想との比較」テーブルパースにフォールバック
    """
    text = filepath.read_text(encoding="utf-8")

    # --- YAML accuracy フロントマター ---
    fm = parse_yaml_frontmatter(text)
    acc = fm.get("accuracy", {})
    if isinstance(acc, dict) and acc:
        result = {}
        result["direction_hit"] = _normalize_bool(
            acc.get("direction_hit"))
        result["range_hit"] = _normalize_bool(acc.get("range_hit"))
        result["cme_gap"] = _parse_cme_deviation(
            acc.get("cme_deviation"))
        result["core_premise_hit"] = _normalize_premise(
            acc.get("core_premise_hit"))
        result["invalidation_triggered"] = _normalize_bool(
            acc.get("invalidation_triggered"))
        return result

    # --- フォールバック: テーブルパース ---
    section = _extract_comparison_section(text)
    if not section:
        return None
    table_result = _parse_comparison_table(section)
    # テーブルパースの結果にcore_premise/invalidationフィールドを追加
    table_result.setdefault("core_premise_hit", None)
    table_result.setdefault("invalidation_triggered", None)
    return table_result


def _normalize_bool(val):
    """各種値をTrue/False/Noneに正規化する。"""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).lower().strip()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def _normalize_premise(val):
    """core_premise_hitの値をtrue/partial/false/Noneに正規化する。"""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).lower().strip()
    if s in ("true", "1", "yes"):
        return True
    if s == "partial":
        return "partial"
    if s in ("false", "0", "no"):
        return False
    return None


def _parse_cme_deviation(val):
    """accuracy.cme_deviationの値を数値に変換する。"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    # 文字列: "+457", "-120" 等
    s = str(val).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _extract_comparison_section(text):
    """AM予想との比較セクションを抽出する。"""
    m = re.search(r"###?\s*AM予想との比較\s*\n(.*?)(?:\n---|\n###|\Z)",
                  text, re.DOTALL)
    return m.group(1) if m else None


def _parse_comparison_table(section):
    """比較テーブルの各行をパースする。"""
    result = {}

    # 総合判断行
    result["direction_hit"] = _parse_judgment_hit(section)

    # CME乖離
    result["cme_gap"] = _parse_cme_gap(section)

    # レンジ判定
    result["range_hit"] = _parse_range_hit(section)

    return result


def _parse_judgment_hit(section):
    """総合判断の的中/外れを判定する。"""
    m = re.search(
        r"総合判断\s*\|.*?\|\s*.*?\|\s*\**(\S+?)\**\s*\|?$",
        section, re.MULTILINE
    )
    if not m:
        return None
    verdict = m.group(1)
    if "的中" in verdict:
        return True
    if "外れ" in verdict or "不的中" in verdict:
        return False
    return None


def _parse_cme_gap(section):
    """CME乖離額をパースする。"""
    m = re.search(r"乖離\s*([+\-])\s*([\d,.]+)\s*円", section)
    if not m:
        return None
    sign = 1 if m.group(1) == "+" else -1
    value = float(m.group(2).replace(",", ""))
    return sign * value


def _parse_range_hit(section):
    """レンジ的中/外れを判定する。"""
    m = re.search(r"ベースレンジ\s*\|.*?\|.*?\|\s*\**(\S+?)\**\s*\|?$",
                  section, re.MULTILINE)
    if not m:
        return None  # レンジ行なし
    verdict = m.group(1)
    if "的中" in verdict:
        return True
    if "外れ" in verdict or "不的中" in verdict:
        return False
    return None


# ---------------------------------------------------------------------------
# ファイル走査
# ---------------------------------------------------------------------------

def find_report_pairs(month=None):
    """AM/PMレポートペアを走査する。monthは'2026-03'形式。"""
    am_files = sorted(REPORTS_DIR.glob("*_am.md"))
    pairs = []
    for am_path in am_files:
        date_str = am_path.stem.replace("_am", "")
        if month and not _matches_month(date_str, month):
            continue
        pm_path = am_path.parent / f"{date_str}_pm.md"
        pairs.append({
            "date": date_str,
            "am_path": am_path,
            "pm_path": pm_path if pm_path.exists() else None,
        })
    return pairs


def _matches_month(date_str, month):
    """'20260312'が'2026-03'にマッチするかチェックする。"""
    ym = month.replace("-", "")
    return date_str.startswith(ym)


# ---------------------------------------------------------------------------
# 集計
# ---------------------------------------------------------------------------

def aggregate(pairs):
    """全ペアを集計してサマリーを返す。"""
    records = []
    am_count = 0
    pm_count = 0

    for pair in pairs:
        am_data = parse_am_report(pair["am_path"])
        am_count += 1

        if not pair["pm_path"]:
            continue

        pm_data = parse_pm_comparison(pair["pm_path"])
        if pm_data is None:
            continue
        pm_count += 1

        records.append({
            "date": pair["date"],
            "direction": am_data.get("direction"),
            "confidence": am_data.get("confidence"),
            "difficulty": am_data.get("difficulty"),
            "direction_hit": pm_data.get("direction_hit"),
            "range_hit": pm_data.get("range_hit"),
            "cme_gap": pm_data.get("cme_gap"),
            "core_premise_hit": pm_data.get("core_premise_hit"),
            "invalidation_triggered": pm_data.get(
                "invalidation_triggered"),
        })

    return _compute_stats(records, am_count, pm_count)


def _compute_stats(records, am_count, pm_count):
    """レコードから統計を算出する。"""
    stats = {
        "am_count": am_count,
        "pm_count": pm_count,
        "pair_count": len(records),
    }

    # 方向性一致率
    stats["direction"] = _direction_stats(records)

    # レンジ包含率
    stats["range"] = _range_stats(records)

    # CME乖離
    stats["cme_gap"] = _cme_gap_stats(records)

    # confidence別
    stats["by_confidence"] = _group_hit_rate(records, "confidence")

    # difficulty別
    stats["by_difficulty"] = _group_hit_rate(records, "difficulty")

    # 核心前提の的中率
    stats["core_premise"] = _core_premise_stats(records)

    # 無効化トリガー
    stats["invalidation"] = _invalidation_stats(records)

    # 日次レコード（CSV/JSON用）
    stats["_records"] = records

    return stats


def _direction_stats(records):
    """方向性の的中統計を算出する。"""
    valid = [r for r in records if r["direction_hit"] is not None]
    hits = [r for r in valid if r["direction_hit"]]
    total = _hit_rate(len(hits), len(valid))

    by_dir = {}
    for direction in ["上昇", "下落", "横ばい"]:
        subset = [r for r in valid if r["direction"] == direction]
        sub_hits = [r for r in subset if r["direction_hit"]]
        by_dir[direction] = _hit_rate(len(sub_hits), len(subset))

    return {"total": total, "by_direction": by_dir}


def _range_stats(records):
    """レンジ包含率を算出する。"""
    valid = [r for r in records if r["range_hit"] is not None]
    hits = [r for r in valid if r["range_hit"]]
    return _hit_rate(len(hits), len(valid))


def _cme_gap_stats(records):
    """CME乖離の統計を算出する。"""
    gaps = [r["cme_gap"] for r in records if r["cme_gap"] is not None]
    if not gaps:
        return {"mean": None, "median": None, "count": 0}
    return {
        "mean": round(mean(gaps), 1),
        "median": round(median(gaps), 1),
        "count": len(gaps),
    }


def _core_premise_stats(records):
    """核心前提の的中統計を算出する。"""
    values = [r["core_premise_hit"] for r in records]
    true_count = sum(1 for v in values if v is True)
    partial_count = sum(1 for v in values if v == "partial")
    false_count = sum(1 for v in values if v is False)
    null_count = sum(1 for v in values if v is None)
    valid = true_count + partial_count + false_count
    return {
        "true": true_count,
        "partial": partial_count,
        "false": false_count,
        "null": null_count,
        "valid": valid,
    }


def _invalidation_stats(records):
    """無効化トリガーの統計を算出する。"""
    values = [r["invalidation_triggered"] for r in records]
    true_count = sum(1 for v in values if v is True)
    false_count = sum(1 for v in values if v is False)
    null_count = sum(1 for v in values if v is None)
    return {
        "true": true_count,
        "false": false_count,
        "null": null_count,
    }


def _group_hit_rate(records, key):
    """指定キーでグループ化し、的中率を算出する。"""
    groups = {}
    for r in records:
        val = r.get(key)
        if val is None or r["direction_hit"] is None:
            continue
        val_str = str(val)
        if val_str not in groups:
            groups[val_str] = {"hits": 0, "total": 0}
        groups[val_str]["total"] += 1
        if r["direction_hit"]:
            groups[val_str]["hits"] += 1

    result = {}
    for val_str, g in sorted(groups.items()):
        result[val_str] = _hit_rate(g["hits"], g["total"])
    return result


def _hit_rate(hits, total):
    """的中数/全体数から率を算出する。"""
    return {
        "hits": hits,
        "total": total,
        "rate": round(hits / total * 100, 1) if total > 0 else None,
    }


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

def format_text(stats, label):
    """テキスト形式のサマリーを生成する。"""
    lines = [f"=== market-outlook 精度集計 ({label}) ===", ""]
    lines += _format_direction(stats["direction"])
    lines += _format_range(stats["range"])
    lines += _format_cme_gap(stats["cme_gap"])
    lines += _format_core_premise(stats["core_premise"])
    lines += _format_invalidation(stats["invalidation"])
    lines += _format_grouped("confidence別的中率", stats["by_confidence"])
    lines += _format_grouped("difficulty別的中率", stats["by_difficulty"])
    lines += _format_report_count(stats)
    return "\n".join(lines)


def _format_direction(d):
    """方向性セクションをフォーマットする。"""
    lines = ["■ 方向性一致率"]
    lines.append(f"  全体: {_rate_str(d['total'])}")
    for name in ["上昇", "下落", "横ばい"]:
        r = d["by_direction"].get(name, _hit_rate(0, 0))
        lines.append(f"  {name}予想: {_rate_str(r)}")
    lines.append("")
    return lines


def _format_range(r):
    """レンジセクションをフォーマットする。"""
    if r["total"] == 0:
        return ["■ レンジ包含率: データなし", ""]
    return [f"■ レンジ包含率: {_rate_str(r)}", ""]


def _format_cme_gap(g):
    """CME乖離セクションをフォーマットする。"""
    lines = ["■ CME乖離"]
    if g["count"] == 0:
        lines.append("  データなし")
    else:
        sign_m = "+" if g["mean"] >= 0 else ""
        sign_d = "+" if g["median"] >= 0 else ""
        lines.append(f"  平均: {sign_m}{g['mean']:.0f}円")
        lines.append(f"  中央値: {sign_d}{g['median']:.0f}円")
    lines.append("")
    return lines


def _format_core_premise(cp):
    """核心前提の的中率セクションをフォーマットする。"""
    if cp["valid"] == 0:
        return []
    lines = ["■ 核心前提の的中率"]
    lines.append(f"  完全的中: {cp['true']}/{cp['valid']}")
    lines.append(f"  部分的中: {cp['partial']}/{cp['valid']}")
    lines.append(f"  不的中: {cp['false']}/{cp['valid']}")
    lines.append("")
    return lines


def _format_invalidation(inv):
    """無効化トリガーセクションをフォーマットする。"""
    total = inv["true"] + inv["false"]
    if total == 0:
        return []
    lines = ["■ 無効化トリガー"]
    lines.append(f"  発動: {inv['true']}/{total}")
    lines.append(f"  未発動: {inv['false']}/{total}")
    lines.append("")
    return lines


def _format_grouped(title, groups):
    """グループ別的中率セクションをフォーマットする。"""
    if not groups:
        return []
    lines = [f"■ {title}"]
    for key, r in groups.items():
        lines.append(f"  {key}: {_rate_str(r)}")
    lines.append("")
    return lines


def _format_report_count(stats):
    """レポート数をフォーマットする。"""
    return [
        f"■ レポート数: AM={stats['am_count']}, "
        f"PM={stats['pm_count']}, ペア={stats['pair_count']}"
    ]


def _rate_str(r):
    """'5/7 (71.4%)'形式の文字列を生成する。"""
    if r["total"] == 0:
        return "0/0 (N/A)"
    return f"{r['hits']}/{r['total']} ({r['rate']}%)"


def format_csv(stats):
    """CSV形式の日次一覧を生成する。"""
    records = stats["_records"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "date", "direction", "confidence", "difficulty",
        "direction_hit", "range_hit", "cme_gap",
        "core_premise_hit",
    ])
    for r in records:
        writer.writerow([
            r["date"],
            r.get("direction", ""),
            r.get("confidence", ""),
            r.get("difficulty", ""),
            r.get("direction_hit", ""),
            r.get("range_hit", ""),
            r.get("cme_gap", ""),
            r.get("core_premise_hit", ""),
        ])
    return output.getvalue()


def format_json(stats):
    """JSON形式で出力する（_recordsは除外）。"""
    output = {k: v for k, v in stats.items() if k != "_records"}
    return json.dumps(output, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    args = _parse_args()
    month = None if args.all else args.month
    label = "全期間" if args.all else args.month

    pairs = find_report_pairs(month=month)
    if not pairs:
        print(f"レポートが見つかりません: {label}", file=sys.stderr)
        sys.exit(1)

    stats = aggregate(pairs)

    if args.csv:
        print(format_csv(stats), end="")
    elif args.json:
        print(format_json(stats))
    else:
        print(format_text(stats, label))


def _parse_args():
    """コマンドライン引数をパースする。"""
    parser = argparse.ArgumentParser(
        description="market-outlook精度集計"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--month", type=str,
        help="集計対象月 (例: 2026-03)"
    )
    group.add_argument(
        "--all", action="store_true",
        help="全期間を集計"
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json", action="store_true",
        help="JSON形式で出力"
    )
    output_group.add_argument(
        "--csv", action="store_true",
        help="CSV形式の日次一覧を出力"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
