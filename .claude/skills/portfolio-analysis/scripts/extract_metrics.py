#!/usr/bin/env python3
"""
既存レポート（Markdown）からメトリクスを抽出し、metrics.json を生成するスクリプト。

使い方:
    python extract_metrics.py [--reports-dir REPORTS_DIR] [--user USER] [--output OUTPUT]

デフォルト:
    --reports-dir: reports/
    --user: demo
    --output: reports/{user}/metrics.json
"""

import argparse
import json
import re
import sys
from pathlib import Path


def find_reports(reports_dir: Path, user: str) -> list[Path]:
    """レポートディレクトリからユーザーのレポートファイルを日付順で取得する。"""
    pattern = f"*_{user}.md"
    user_dir = reports_dir / user
    reports = sorted(user_dir.glob(pattern)) if user_dir.exists() else []
    return reports


def extract_date(filepath: Path) -> str:
    """ファイル名 YYYYMMDD_user.md から日付文字列 YYYY-MM-DD を抽出する。"""
    stem = filepath.stem  # 例: 20260212_demo
    date_part = stem.split("_")[0]
    if len(date_part) == 8 and date_part.isdigit():
        return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
    return ""


def extract_mode(content: str) -> str:
    """分析モードを抽出する。"""
    # "分析モード: debate（議論重視）" や "分析モード: normal（クロスレビュー実施）"
    m = re.search(r"分析モード[:：]\s*(\w+)", content)
    if m:
        mode_raw = m.group(1).lower()
        if "debate" in mode_raw or "議論" in mode_raw:
            return "debate"
        elif "speed" in mode_raw:
            return "speed"
        else:
            return "normal"
    return "normal"


def extract_total_asset(content: str) -> int | None:
    """総資産を抽出する。"""
    # "総資産: 991,130円" パターン
    m = re.search(r"総資産[:：]\s*([\d,]+)円", content)
    if m:
        return int(m.group(1).replace(",", ""))
    # 予算パターン（初回構築提案の場合）: "予算: 100万円"
    m = re.search(r"予算[:：]\s*([\d,]+)万円", content)
    if m:
        return int(m.group(1).replace(",", "")) * 10000
    m = re.search(r"予算[:：]\s*([\d,]+)円", content)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def extract_cash_balance(content: str) -> int | None:
    """現金残高を抽出する。"""
    m = re.search(r"現金残高[:：]\s*([\d,]+)円", content)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def extract_holdings_count(content: str) -> int:
    """保有銘柄数を抽出する。"""
    m = re.search(r"保有銘柄数[:：]\s*(\d+)銘柄", content)
    if m:
        return int(m.group(1))
    return 0


def extract_overall_score(content: str) -> float | None:
    """総合スコアを抽出する。"""
    # "総合評価: 64点/100点", "**総合スコア**: 81.1点/100点",
    # "総合評価: **62点/100点**" 等のパターン
    patterns = [
        r"\*{0,2}(?:総合評価|総合スコア)\*{0,2}[:：]\s*\*{0,2}([\d.]+)点",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return float(m.group(1))
    return None


def extract_sharpe_ratio(content: str) -> float | None:
    """ポートフォリオのシャープレシオを抽出する。"""
    # "ポートフォリオ全体のシャープレシオ: 1.97" や "加重シャープレシオ: 1.58"
    # "ポートフォリオ推定シャープレシオ: 2.2"
    patterns = [
        r"ポートフォリオ(?:全体の)?(?:加重)?シャープレシオ[:：]\s*\*{0,2}([\d.]+)",
        r"ポートフォリオ推定シャープレシオ[:：]\s*\*{0,2}([\d.]+)",
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return float(m.group(1))
    return None


def extract_max_drawdown(content: str) -> float | None:
    """最大ドローダウンを抽出する。"""
    # "最大ドローダウン: -2.28%" または "最大ドローダウン: **-2.28%**"
    m = re.search(r"最大ドローダウン[:：]\s*\*{0,2}(-?[\d.]+)%", content)
    if m:
        return round(float(m.group(1)) / 100, 6)
    return None


def extract_var_95(content: str) -> float | None:
    """月次VaR(95%)を抽出する。"""
    # "月次VaR(95%): -0.99%" または "月次VaR(95%): **-1.60%**"
    m = re.search(r"月次VaR\(95%\)[:：]\s*\*{0,2}(-?[\d.]+)%", content)
    if m:
        return round(float(m.group(1)) / 100, 6)
    return None


def extract_score_axes(content: str) -> dict | None:
    """5軸スコアを抽出する。"""
    axes = {}

    # テーブル形式: | 配当力 | コスト効率 | 規模信頼性 | 売買品質 | リターン |
    # ヘッダー行を探す
    header_pattern = r"\|\s*配当力\s*\|\s*コスト効率\s*\|\s*規模信頼性\s*\|\s*売買品質\s*\|\s*リターン\s*\|"
    m = re.search(header_pattern, content)
    if m:
        # ヘッダーの次の行（セパレータ）、さらに次の行にデータ
        pos = m.end()
        remaining = content[pos:]
        lines = remaining.split("\n")
        for line in lines[1:5]:  # セパレータの次から数行
            # | 62.0 | 84.0 | 96.2 | 95.4 | 78.9 | のパターン
            vals = re.findall(r"([\d.]+)", line)
            if len(vals) >= 5:
                axes = {
                    "dividend_power": float(vals[0]),
                    "cost_efficiency": float(vals[1]),
                    "scale_reliability": float(vals[2]),
                    "trading_quality": float(vals[3]),
                    "return_performance": float(vals[4]),
                }
                return axes

    # 視点別テーブル形式（初回レポート: 行ごとにバランス, 高配当, ...）
    # "| バランス | 68.4 | 80.9 | 96.6 | 92.5 | 67.2 | 81.1 |" パターン
    m = re.search(
        r"\|\s*バランス\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|",
        content,
    )
    if m:
        axes = {
            "dividend_power": float(m.group(1)),
            "cost_efficiency": float(m.group(2)),
            "scale_reliability": float(m.group(3)),
            "trading_quality": float(m.group(4)),
            "return_performance": float(m.group(5)),
        }
        return axes

    return None


def extract_holdings(content: str) -> list[dict]:
    """保有銘柄一覧を抽出する。"""
    holdings = []

    # セクション1の銘柄テーブルを検索
    # | コード | 銘柄名 | 保有数量 | 平均取得単価 | 現在価格 | 評価額 | 損益 | 損益率 | 保有比率 |
    section_match = re.search(r"## 1\. (?:保有銘柄一覧|候補銘柄一覧)", content)
    if not section_match:
        return holdings

    section_start = section_match.start()
    # 次のセクション開始まで
    next_section = re.search(r"\n## 2\.", content[section_start:])
    section_end = section_start + next_section.start() if next_section else len(content)
    section_content = content[section_start:section_end]

    # 保有銘柄テーブル行の抽出
    # | 1475 | iシェアーズ・コア TOPIX ETF | 800口 | 395.4円 | 392円 | 313,600円 | -2,720円 | -0.9% | 32.2% |
    row_pattern = re.compile(
        r"\|\s*(\d{4})\s*\|"   # コード
        r"\s*([^|]+)\s*\|"      # 銘柄名
        r"\s*[\d,]+口?\s*\|"    # 保有数量（スキップ）
        r"\s*[\d,.]+円?\s*\|"   # 平均取得単価（スキップ）
        r"\s*[\d,.]+円?\s*\|"   # 現在価格（スキップ）
        r"\s*([\d,]+)円?\s*\|"  # 評価額
        r"\s*[+\-]?[\d,]+円?\s*\|"  # 損益（スキップ）
        r"\s*([+\-]?[\d.]+)%\s*\|"  # 損益率
        r"\s*([\d.]+)%\s*\|"    # 保有比率
    )

    for m in row_pattern.finditer(section_content):
        etf_code = m.group(1).strip()
        name = m.group(2).strip()
        current_value = int(m.group(3).replace(",", ""))
        pnl_rate = float(m.group(4)) / 100
        weight = float(m.group(5)) / 100

        holdings.append({
            "etf_code": etf_code,
            "name": name,
            "weight": weight,
            "pnl_rate": pnl_rate,
            "current_value": current_value,
        })

    return holdings


def extract_top_actions(content: str) -> list[dict]:
    """最優先アクション（トップ3）を抽出する。"""
    actions = []

    # "### 最優先アクション（トップ3）" セクションを探す
    m = re.search(r"### 最優先アクション", content)
    if not m:
        return actions

    pos = m.end()
    # 次の ### まで
    next_heading = re.search(r"\n###?\s", content[pos:])
    section_end = pos + next_heading.start() if next_heading else pos + 2000
    section = content[pos:section_end]

    # "1. **アクション名**: 説明（合意度: 100%）"
    action_pattern = re.compile(
        r"\d+\.\s*\*\*([^*]+)\*\*[:：]?\s*([^（(]*?)(?:（合意度[:：]\s*(\d+)%）|\(合意度[:：]\s*(\d+)%\))?(?:\n|$)"
    )

    priority_map = {0: "highest", 1: "high", 2: "medium"}

    for i, am in enumerate(action_pattern.finditer(section)):
        action_name = am.group(1).strip()
        consensus = None
        if am.group(3):
            consensus = int(am.group(3))
        elif am.group(4):
            consensus = int(am.group(4))

        actions.append({
            "action": action_name,
            "priority": priority_map.get(i, "low"),
            "consensus": consensus,
        })

    return actions


def extract_key_risks(content: str) -> list[str]:
    """主要リスクを抽出する。"""
    risks = []

    # "主要リスク: ..." パターン
    m = re.search(r"主要リスク[:：]\s*(.+?)(?:\n|$)", content)
    if m:
        risk_text = m.group(1).strip()
        # "、" や "," で分割
        risk_items = re.split(r"[、,]", risk_text)
        for item in risk_items:
            item = item.strip().strip("*")
            if item:
                risks.append(item)

    return risks


def extract_metrics_from_report(filepath: Path, user: str) -> dict | None:
    """1つのレポートファイルからメトリクスを抽出する。"""
    content = filepath.read_text(encoding="utf-8")

    date = extract_date(filepath)
    if not date:
        print(f"警告: 日付を抽出できませんでした: {filepath.name}", file=sys.stderr)
        return None

    report_path = f"reports/{user}/{filepath.name}"
    mode = extract_mode(content)
    total_asset = extract_total_asset(content)
    cash_balance = extract_cash_balance(content)
    holdings_count = extract_holdings_count(content)
    holdings = extract_holdings(content)
    overall_score = extract_overall_score(content)
    sharpe_ratio = extract_sharpe_ratio(content)
    max_drawdown = extract_max_drawdown(content)
    var_95 = extract_var_95(content)
    score_axes = extract_score_axes(content)
    top_actions = extract_top_actions(content)
    key_risks = extract_key_risks(content)

    # 現金比率の計算
    cash_ratio = None
    if cash_balance is not None and total_asset is not None and total_asset > 0:
        cash_ratio = round(cash_balance / total_asset, 4)

    return {
        "date": date,
        "report_path": report_path,
        "mode": mode,
        "total_asset": total_asset,
        "cash_balance": cash_balance,
        "cash_ratio": cash_ratio,
        "holdings_count": holdings_count if holdings_count > 0 else len(holdings),
        "holdings": holdings,
        "overall_score": overall_score,
        "sharpe_ratio_portfolio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "var_95": var_95,
        "score_axes": score_axes,
        "top_actions": top_actions,
        "key_risks": key_risks,
    }


def main():
    parser = argparse.ArgumentParser(
        description="既存レポートからメトリクスを抽出し metrics.json を生成する"
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="レポートディレクトリのパス（デフォルト: reports/）",
    )
    parser.add_argument(
        "--user",
        default="demo",
        help="ユーザー名（デフォルト: demo）",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="出力先パス（デフォルト: reports/{user}/metrics.json）",
    )
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    user = args.user
    output_path = Path(args.output) if args.output else reports_dir / user / "metrics.json"

    if not reports_dir.exists():
        print(f"エラー: レポートディレクトリが存在しません: {reports_dir}", file=sys.stderr)
        sys.exit(1)

    reports = find_reports(reports_dir, user)
    if not reports:
        print(f"エラー: レポートが見つかりません: {reports_dir}/{user}/*_{user}.md", file=sys.stderr)
        sys.exit(1)

    print(f"レポート {len(reports)} 件を処理中...", file=sys.stderr)

    metrics = []
    for report_path in reports:
        print(f"  抽出中: {report_path.name}", file=sys.stderr)
        entry = extract_metrics_from_report(report_path, user)
        if entry:
            metrics.append(entry)

    # 出力先ディレクトリの作成
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"\n完了: {output_path} ({len(metrics)} エントリ)", file=sys.stderr)

    # 検証: JSONとして正しくパースできるか
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        print(f"検証OK: {len(data)} エントリ", file=sys.stderr)
        for entry in data:
            print(
                f"  {entry['date']}: 総資産={entry['total_asset']}, "
                f"スコア={entry['overall_score']}, "
                f"シャープ={entry['sharpe_ratio_portfolio']}, "
                f"銘柄数={entry['holdings_count']}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
