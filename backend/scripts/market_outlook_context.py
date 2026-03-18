"""market-outlook直近営業日コンテキスト生成スクリプト

過去5営業日のmarket-outlookレポートのYAMLフロントマターから
構造化要約を生成する。market-outlook AM生成時のコンテキスト注入用。

使い方:
  python backend/scripts/market_outlook_context.py
  python backend/scripts/market_outlook_context.py --days 3
  python backend/scripts/market_outlook_context.py --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from statistics import mean

# プロジェクトルートを特定（backend/scripts/ → backend/ → project root）
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

REPORTS_DIR = PROJECT_ROOT / "reports" / "market-outlook"
FLAT_THRESHOLD_PCT = 0.3  # 横ばい判定閾値（±0.3%）SKILL.mdパラメータ表参照


# ---------------------------------------------------------------------------
# YAML フロントマターパース
# ---------------------------------------------------------------------------

def parse_yaml_frontmatter(text):
    """^---\\n(.*?)\\n--- で正規表現マッチ後、ブロックを解析する。"""
    m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
    if not m:
        return {}
    return _parse_yaml_block(m.group(1))


def _parse_yaml_block(block):
    """ネスト1段の簡易YAMLパーサー。"""
    result = {}
    current_key = None
    for line in block.split("\n"):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                result[key] = _cast_yaml_value(val)
            else:
                result[key] = {}
                current_key = key
        elif current_key and line.startswith(" ") and ":" in line:
            key, _, val = line.strip().partition(":")
            result[current_key][key.strip()] = _cast_yaml_value(val.strip())
    return result


def _cast_yaml_value(val):
    """bool/null/int/float/strに順次キャストする。"""
    if val in ("true", "True"):
        return True
    if val in ("false", "False"):
        return False
    if val in ("null", "None", "~"):
        return None
    # クォート除去
    if ((val.startswith('"') and val.endswith('"'))
            or (val.startswith("'") and val.endswith("'"))):
        return val[1:-1]
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


# ---------------------------------------------------------------------------
# レポート収集
# ---------------------------------------------------------------------------

def collect_recent_days(days=5):
    """直近N営業日分のAM/PMレポートペアを日付降順で収集する。"""
    am_files = sorted(REPORTS_DIR.glob("*_am.md"), reverse=True)
    pairs = []
    for am_path in am_files:
        date_str = am_path.stem.replace("_am", "")
        pm_path = am_path.parent / f"{date_str}_pm.md"
        pairs.append({
            "date": date_str,
            "am_path": am_path,
            "pm_path": pm_path if pm_path.exists() else None,
        })
        if len(pairs) >= days:
            break
    # 日付昇順に戻す（古い→新しい）
    pairs.reverse()
    return pairs


# ---------------------------------------------------------------------------
# データ抽出
# ---------------------------------------------------------------------------

def extract_am_data(filepath):
    """AMレポートから予測データを抽出する。"""
    text = filepath.read_text(encoding="utf-8")
    fm = parse_yaml_frontmatter(text)
    pred = fm.get("prediction", {})
    if not isinstance(pred, dict):
        pred = {}
    return {
        "direction": pred.get("direction"),
        "cme_nikkei": pred.get("cme_nikkei"),
        "macro_regime": pred.get("macro_regime"),
        "causal_chain": pred.get("causal_chain"),
    }


def extract_pm_data(filepath):
    """PMレポートから実績データを抽出する。"""
    text = filepath.read_text(encoding="utf-8")
    fm = parse_yaml_frontmatter(text)
    acc = fm.get("accuracy", {})
    if not isinstance(acc, dict):
        acc = {}
    return {
        "direction_hit": acc.get("direction_hit"),
        "cme_deviation": _to_int_or_none(acc.get("cme_deviation")),
        "core_premise_hit": acc.get("core_premise_hit"),
        "notes": acc.get("notes"),
    }


def _to_int_or_none(val):
    """値をintに変換する。失敗時はNone。"""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    try:
        return int(str(val).strip().replace(",", "").replace("+", ""))
    except (ValueError, TypeError):
        return None


def extract_change_pct(notes):
    """PMのnotesから実績変化率を正規表現で抽出する。"""
    if not notes:
        return None
    m = re.search(r"[+\-]?\d+\.\d+%", notes)
    if m:
        try:
            return float(m.group(0).rstrip("%"))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# actual_flow構築
# ---------------------------------------------------------------------------

def determine_direction(direction_hit, am_direction, notes):
    """PMのdirection_hitとAMのdirectionから実績の方向を判定する。"""
    # notesから変化率を抽出して微小変動を判定
    pct = extract_change_pct(notes)
    if pct is not None and abs(pct) <= FLAT_THRESHOLD_PCT:
        return "FLAT"

    if direction_hit is None:
        return "FLAT"
    if direction_hit is True:
        if am_direction == "上昇":
            return "UP"
        if am_direction == "下落":
            return "DOWN"
        return "FLAT"
    if direction_hit is False:
        if am_direction == "上昇":
            return "DOWN"
        if am_direction == "下落":
            return "UP"
        return "FLAT"
    return "FLAT"


# ---------------------------------------------------------------------------
# trend_summary判定
# ---------------------------------------------------------------------------

def determine_trend_summary(sequence):
    """実績騰落シーケンスからトレンドサマリーを判定する。

    trend_summary enum:
      UPTREND            - 直近5日中UP3日以上かつ直近2日がUP
      DOWNTREND          - 直近5日中DOWN3日以上かつ直近2日がDOWN
      REVERSAL_RECOVERY  - 前半DOWN優勢→直近2日UP
      REVERSAL_DECLINE   - 前半UP優勢→直近2日DOWN
      RANGE_BOUND        - 上記いずれにも該当しない
    """
    effective = [d for d in sequence if d != "FLAT"]
    if len(effective) < 2:
        return "RANGE_BOUND"

    up_count = effective.count("UP")
    down_count = effective.count("DOWN")
    last_two = effective[-2:]

    if up_count >= 3 and last_two == ["UP", "UP"]:
        return "UPTREND"
    if down_count >= 3 and last_two == ["DOWN", "DOWN"]:
        return "DOWNTREND"

    mid = len(effective) // 2
    first_half = effective[:mid] if mid > 0 else effective[:1]

    if (last_two == ["UP", "UP"]
            and first_half.count("DOWN") >= first_half.count("UP")):
        return "REVERSAL_RECOVERY"
    if (last_two == ["DOWN", "DOWN"]
            and first_half.count("UP") >= first_half.count("DOWN")):
        return "REVERSAL_DECLINE"

    return "RANGE_BOUND"


# ---------------------------------------------------------------------------
# 精度トラッキング
# ---------------------------------------------------------------------------

def compute_direction_stats(pm_data_list):
    """direction_hitのtrue/false/nullカウントを集計する。"""
    true_count = 0
    false_count = 0
    null_count = 0
    for pm in pm_data_list:
        hit = pm.get("direction_hit")
        if hit is True:
            true_count += 1
        elif hit is False:
            false_count += 1
        else:
            null_count += 1
    parts = [f"{true_count}勝{false_count}敗"]
    if null_count > 0:
        parts.append(f"({null_count}不明)")
    return "".join(parts)


def compute_cme_bias_avg(pm_data_list):
    """cme_deviationの平均値を算出する（null除外）。"""
    values = [
        pm["cme_deviation"] for pm in pm_data_list
        if pm.get("cme_deviation") is not None
    ]
    if not values:
        return None
    return round(mean(values))


# ---------------------------------------------------------------------------
# テーマ・レジーム
# ---------------------------------------------------------------------------

def extract_themes_3d(am_data_list):
    """直近3日のAMのcausal_chainを返す。"""
    recent = am_data_list[-3:] if len(am_data_list) >= 3 else am_data_list
    themes = []
    for am in recent:
        chain = am.get("causal_chain")
        if chain:
            themes.append(chain)
    return themes


def check_regime_change(am_data_list):
    """期間中にmacro_regimeが変化したかを判定する。"""
    regimes = [
        am.get("macro_regime") for am in am_data_list
        if am.get("macro_regime") is not None
    ]
    if len(regimes) < 2:
        return False
    return len(set(regimes)) > 1


# ---------------------------------------------------------------------------
# アラート生成
# ---------------------------------------------------------------------------

def generate_alerts(pm_data_list, themes_3d):
    """最大2件のアラートを生成する。"""
    alerts = []

    # CME乖離バイアスチェック（4日以上同方向）
    deviations = [
        pm["cme_deviation"] for pm in pm_data_list
        if pm.get("cme_deviation") is not None
    ]
    if len(deviations) >= 4:
        positive = sum(1 for d in deviations if d > 0)
        negative = sum(1 for d in deviations if d < 0)
        avg = round(mean(deviations))
        if positive >= 4:
            alerts.append(f"CME_プラスバイアス(平均{avg:+d}円)")
        elif negative >= 4:
            alerts.append(f"CME_マイナスバイアス(平均{avg:+d}円)")

    # テーマ継続チェック（3日連続で同一キーワード）
    if len(themes_3d) >= 3:
        keywords = _extract_common_keywords(themes_3d)
        for kw in keywords:
            if len(alerts) >= 2:
                break
            alerts.append(f"テーマ継続({kw})")

    return alerts[:2]


def _extract_common_keywords(themes):
    """3つのcausal_chain全てに出現するキーワードを抽出する。"""
    # 重要そうな名詞を抽出（カタカナ・漢字2文字以上）
    keyword_pattern = re.compile(r"[ァ-ヶー]{2,}|[一-龥]{2,}|[A-Z][A-Z0-9]{1,}")
    sets = []
    for theme in themes:
        words = set(keyword_pattern.findall(theme))
        sets.append(words)
    if not sets:
        return []
    common = sets[0]
    for s in sets[1:]:
        common = common & s
    # ストップワードを除外
    stop_words = {"東証", "日経", "先物", "予想", "方向", "環境", "CME"}
    common = common - stop_words
    return sorted(common)


# ---------------------------------------------------------------------------
# メインロジック
# ---------------------------------------------------------------------------

def build_context(days=5):
    """構造化要約コンテキストを構築する。"""
    pairs = collect_recent_days(days)
    if not pairs:
        return None

    am_data_list = []
    pm_data_list = []
    sequence = []

    for pair in pairs:
        am_data = extract_am_data(pair["am_path"])
        am_data["date"] = pair["date"]
        am_data_list.append(am_data)

        if pair["pm_path"]:
            pm_data = extract_pm_data(pair["pm_path"])
            pm_data["date"] = pair["date"]
            pm_data_list.append(pm_data)

            direction = determine_direction(
                pm_data["direction_hit"],
                am_data["direction"],
                pm_data.get("notes"),
            )
            sequence.append(direction)

    # PMデータが皆無の場合はコンテキストとして意味をなさない
    if not pm_data_list:
        return None

    # 期間文字列
    first_date = pairs[0]["date"]
    last_date = pairs[-1]["date"]
    period = (
        f"{first_date[:4]}-{first_date[4:6]}-{first_date[6:8]}"
        f" ~ "
        f"{last_date[:4]}-{last_date[4:6]}-{last_date[6:8]}"
    )

    # actual_flow
    trend_summary = determine_trend_summary(sequence)

    # 精度トラッキング
    direction_stats = compute_direction_stats(pm_data_list)
    cme_bias_avg = compute_cme_bias_avg(pm_data_list)

    # テーマ・レジーム
    themes_3d = extract_themes_3d(am_data_list)
    regime_latest = am_data_list[-1].get("macro_regime") if am_data_list else None
    regime_changed = check_regime_change(am_data_list)

    # アラート
    alerts = generate_alerts(pm_data_list, themes_3d)

    context = {
        "period": period,
        "actual_flow": {
            "sequence": sequence,
            "trend_summary": trend_summary,
        },
        "accuracy": {
            "direction_stats": direction_stats,
            "cme_bias_avg": cme_bias_avg,
        },
        "themes_3d": themes_3d,
        "regime": {
            "latest": regime_latest,
            "changed": regime_changed,
        },
        "alerts": alerts,
    }
    return context


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

def format_yaml_output(context):
    """構造化要約をYAML形式で標準出力する。"""
    lines = ["recent_context:"]
    lines.append(f'  period: "{context["period"]}"')
    lines.append("")

    # actual_flow
    lines.append("  actual_flow:")
    seq_str = ", ".join(context["actual_flow"]["sequence"])
    lines.append(f"    sequence: [{seq_str}]")
    lines.append(
        f'    trend_summary: {context["actual_flow"]["trend_summary"]}'
    )
    lines.append("")

    # accuracy
    lines.append("  accuracy:")
    lines.append(
        f'    direction_stats: "{context["accuracy"]["direction_stats"]}"'
    )
    cme_avg = context["accuracy"]["cme_bias_avg"]
    if cme_avg is not None:
        lines.append(f"    cme_bias_avg: {cme_avg:+d}")
    else:
        lines.append("    cme_bias_avg: null")
    lines.append("")

    # themes_3d
    lines.append("  themes_3d:")
    for theme in context["themes_3d"]:
        lines.append(f'    - "{theme}"')
    lines.append("")

    # regime
    lines.append("  regime:")
    lines.append(f'    latest: "{context["regime"]["latest"]}"')
    changed_str = "true" if context["regime"]["changed"] else "false"
    lines.append(f"    changed: {changed_str}")
    lines.append("")

    # alerts
    lines.append("  alerts:")
    if context["alerts"]:
        for alert in context["alerts"]:
            lines.append(f'    - "{alert}"')
    else:
        lines[-1] = "  alerts: []"

    print("\n".join(lines))


def format_json_output(context):
    """構造化要約をJSON形式で標準出力する。"""
    print(json.dumps(context, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="market-outlook直近営業日コンテキスト生成"
    )
    parser.add_argument(
        "--days", type=int, default=5,
        help="参照する営業日数（デフォルト: 5）"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="JSON形式で出力（デフォルトはYAML形式）"
    )
    args = parser.parse_args()

    context = build_context(days=args.days)
    if context is None:
        print("レポートが見つかりません", file=sys.stderr)
        sys.exit(1)

    if args.json:
        format_json_output(context)
    else:
        format_yaml_output(context)


if __name__ == "__main__":
    main()
