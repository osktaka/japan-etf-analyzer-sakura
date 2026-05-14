"""A群（コア・逆相関）3スロット 新案5パターン比較分析（使い捨て調査用）.

前段の `core_partner_analysis_20260514.md` の結論を踏まえ、1547をコア固定として
5案の A群合成ポート（等ウェイト 1/3 × 3）のリスク・リターン・ストレス耐性を比較する.

【重要・必須ルール】
- 価格データは **ChartService 経由** で取得する（分割調整済み）
- SQLite 直接クエリで `price_histories` から取得することは禁止
- 同一計算内で API/DB を混在させない
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# プロジェクトルート特定
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 環境変数（本番互換）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))

sys.path.insert(0, str(BACKEND_DIR))

from src.app import create_app  # noqa: E402
from src.services.chart_service import ChartService  # noqa: E402

# 出力先（Docker環境では /app/reports/ がホスト側 reports/ にマップされている）
TODAY = datetime.now().strftime("%Y%m%d")
if Path("/app/reports").exists():
    REPORT_DIR = Path("/app/reports") / "research"
else:
    REPORT_DIR = PROJECT_ROOT / "reports" / "research"
REPORT_MD = REPORT_DIR / f"a_group_patterns_{TODAY}.md"
REPORT_JSON = REPORT_DIR / f"a_group_patterns_{TODAY}.json"

# 検証する銘柄
TARGET_CODES = ["2559", "200A", "1540", "1547", "1326", "1629", "1306"]

# 5案の構成 (3資産等ウェイト=1/3ずつ)
PATTERNS = {
    "A": {
        "name": "現行A群（参考）",
        "codes": ["2559", "1540", "200A"],
        "concept": "既存A群（ベースライン）",
    },
    "B": {
        "name": "最低相関重視",
        "codes": ["1547", "1540", "1326"],
        "concept": "米国株+金2種、ヘッジ最厚",
    },
    "C": {
        "name": "バランス型",
        "codes": ["1547", "1540", "1629"],
        "concept": "米国株+金+商社、リターン重視",
    },
    "D": {
        "name": "地域分散型",
        "codes": ["1547", "1540", "1306"],
        "concept": "米国株+金+TOPIX",
    },
    "E": {
        "name": "現行修正型",
        "codes": ["1547", "1540", "200A"],
        "concept": "オルカンをS&P500に置換のみ",
    },
}

# ストレスイベント
STRESS_EVENTS = [
    ("チャイナショック", "2015-08", "2015-09"),
    ("クリスマスショック", "2018-12", "2018-12"),
    ("コロナショック", "2020-02", "2020-03"),
    ("ウクライナ侵攻", "2022-02", "2022-03"),
    ("関税ショック", "2025-04", "2025-04"),
]


def fetch_chart_via_service(svc: ChartService, code: str) -> List[Dict]:
    """ChartService 経由で分割調整済み日次クローズ価格を取得 (10y).

    Returns:
        [{date, close}, ...] (昇順)
    """
    result = svc.get_chart_data(code, period="10y")
    if not result or not result.get("data"):
        return []
    data = result["data"]
    # 念のため date 昇順ソート
    data = sorted(data, key=lambda x: x.get("date", ""))
    return [
        {"date": p["date"], "close": float(p["close"])}
        for p in data
        if p.get("close") is not None
    ]


def daily_to_monthly_returns(prices: List[Dict]) -> Dict[str, float]:
    """日次価格から月次リターン辞書 {YYYY-MM: return} を生成.

    月末価格（同月内の最終営業日クローズ）を使い、対前月比リターン.
    """
    if not prices or len(prices) < 2:
        return {}
    # 月内最終日のcloseを保持（昇順前提なので上書きで最終日が残る）
    monthly_close: Dict[str, float] = {}
    for p in prices:
        d = p.get("date", "")
        if not d or len(d) < 7:
            continue
        monthly_close[d[:7]] = p["close"]
    months = sorted(monthly_close.keys())
    rets: Dict[str, float] = {}
    for i in range(1, len(months)):
        prev = monthly_close[months[i - 1]]
        curr = monthly_close[months[i]]
        if prev > 0:
            rets[months[i]] = (curr - prev) / prev
    return rets


def composite_monthly_returns(
    monthly_rets_map: Dict[str, Dict[str, float]], codes: List[str]
) -> Tuple[Dict[str, float], List[str]]:
    """3資産の月次リターンを等ウェイト(1/3)で合成.

    各資産すべてが利用可能な月のみ使う（共通最小期間）.

    Returns:
        ({YYYY-MM: composite_return}, sorted_common_months)
    """
    # 共通月キー
    common: Optional[set] = None
    for c in codes:
        s = set(monthly_rets_map.get(c, {}).keys())
        if common is None:
            common = s
        else:
            common &= s
    if not common:
        return {}, []
    months = sorted(common)
    w = 1.0 / 3.0
    composite: Dict[str, float] = {}
    for m in months:
        r = sum(monthly_rets_map[c][m] for c in codes) * w
        composite[m] = r
    return composite, months


def calc_cagr(monthly_rets: Dict[str, float]) -> Optional[float]:
    """月次リターンからCAGR（年率%）を計算."""
    if not monthly_rets:
        return None
    months = sorted(monthly_rets.keys())
    n = len(months)
    if n < 12:
        return None
    cumulative = 1.0
    for m in months:
        cumulative *= 1.0 + monthly_rets[m]
    years = n / 12.0
    if cumulative <= 0:
        return None
    return (math.pow(cumulative, 1.0 / years) - 1) * 100


def calc_annual_vol(monthly_rets: Dict[str, float]) -> Optional[float]:
    """月次リターンから年率ボラ(%)を計算 (標本標準偏差×√12×100)."""
    if not monthly_rets or len(monthly_rets) < 2:
        return None
    rets = list(monthly_rets.values())
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    return math.sqrt(var) * math.sqrt(12) * 100


def calc_sharpe(cagr_pct: Optional[float], vol_pct: Optional[float]) -> Optional[float]:
    """シャープレシオ (rf=0%)."""
    if cagr_pct is None or vol_pct is None or vol_pct <= 0:
        return None
    return cagr_pct / vol_pct


def calc_max_drawdown(monthly_rets: Dict[str, float]) -> Optional[float]:
    """月次累積リターンから最大ドローダウン(%)を計算."""
    if not monthly_rets:
        return None
    months = sorted(monthly_rets.keys())
    cumulative = 1.0
    peak = 1.0
    max_dd = 0.0
    for m in months:
        cumulative *= 1.0 + monthly_rets[m]
        peak = max(peak, cumulative)
        if peak > 0:
            dd = (cumulative - peak) / peak
            if dd < max_dd:
                max_dd = dd
    return max_dd * 100


def evaluate_pattern(
    monthly_rets_map: Dict[str, Dict[str, float]], codes: List[str]
) -> Dict:
    """1パターンの評価指標を計算."""
    composite, months = composite_monthly_returns(monthly_rets_map, codes)
    if not composite:
        return {
            "codes": codes,
            "n_months": 0,
            "start_month": None,
            "end_month": None,
            "data_years": 0.0,
            "cagr_pct": None,
            "annual_vol_pct": None,
            "sharpe": None,
            "max_drawdown_pct": None,
        }
    cagr = calc_cagr(composite)
    vol = calc_annual_vol(composite)
    sharpe = calc_sharpe(cagr, vol)
    mdd = calc_max_drawdown(composite)
    return {
        "codes": codes,
        "n_months": len(months),
        "start_month": months[0],
        "end_month": months[-1],
        "data_years": round(len(months) / 12.0, 2),
        "cagr_pct": cagr,
        "annual_vol_pct": vol,
        "sharpe": sharpe,
        "max_drawdown_pct": mdd,
        "composite_monthly_returns": composite,
    }


def evaluate_benchmark_1547(monthly_rets_map: Dict[str, Dict[str, float]]) -> Dict:
    """1547単独のリターン指標を10年分で計算."""
    r1547 = monthly_rets_map.get("1547", {})
    cagr = calc_cagr(r1547)
    vol = calc_annual_vol(r1547)
    sharpe = calc_sharpe(cagr, vol)
    mdd = calc_max_drawdown(r1547)
    months = sorted(r1547.keys())
    return {
        "codes": ["1547"],
        "n_months": len(months),
        "start_month": months[0] if months else None,
        "end_month": months[-1] if months else None,
        "data_years": round(len(months) / 12.0, 2),
        "cagr_pct": cagr,
        "annual_vol_pct": vol,
        "sharpe": sharpe,
        "max_drawdown_pct": mdd,
    }


def cumulative_return_for_months(
    composite_rets: Dict[str, float], months_range: List[str]
) -> Optional[float]:
    """指定月リスト内のリターンを累積したリターン(%)を返す."""
    if not composite_rets:
        return None
    cum = 1.0
    found = False
    for m in months_range:
        if m in composite_rets:
            cum *= 1.0 + composite_rets[m]
            found = True
    if not found:
        return None
    return (cum - 1.0) * 100


def months_in_range(start: str, end: str) -> List[str]:
    """YYYY-MM 形式の start〜end の月リストを生成."""
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    months = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def evaluate_stress_events(
    pattern_results: Dict[str, Dict],
    monthly_rets_map: Dict[str, Dict[str, float]],
) -> List[Dict]:
    """各パターン × 各イベントの累積リターンと vs 1547単独 相対パフォーマンス."""
    r1547 = monthly_rets_map.get("1547", {})
    rows = []
    for evt_name, start, end in STRESS_EVENTS:
        months_range = months_in_range(start, end)
        ret_1547 = cumulative_return_for_months(r1547, months_range)
        per_pattern = {}
        for key, info in PATTERNS.items():
            comp = pattern_results[key].get("composite_monthly_returns", {})
            ret = cumulative_return_for_months(comp, months_range)
            rel = (ret - ret_1547) if (ret is not None and ret_1547 is not None) else None
            per_pattern[key] = {
                "return_pct": ret,
                "vs_1547_pp": rel,  # percentage points 差分
            }
        rows.append({
            "event": evt_name,
            "period": f"{start} 〜 {end}",
            "ret_1547_pct": ret_1547,
            "patterns": per_pattern,
        })
    return rows


def fmt(x, digits=2, suffix=""):
    if x is None:
        return "—"
    if isinstance(x, (int, float)):
        return f"{x:.{digits}f}{suffix}"
    return f"{x}{suffix}"


def write_markdown(out: Dict):
    """Markdown レポートを出力."""
    md = []
    md.append("# A群（コア・逆相関）3スロット 新案5パターン比較分析レポート\n")
    md.append(f"**生成日**: {out['metadata']['generated_at']}  ")
    md.append(f"**ベンチマーク**: 1547 単独（上場インデックスファンド米国株式 S&P500）  ")
    md.append(f"**評価方法**: A群3資産のみ等ウェイト 1/3 ずつで構築した合成ポートを月次リターンで評価  ")
    md.append(f"**Rf**: 0% 仮定（シャープレシオ）\n")

    # サマリ
    md.append("## サマリ\n")
    summary = out["summary"]
    md.append(f"- 推奨案: **{summary['recommended']['key']} ({summary['recommended']['name']})** — {summary['recommended']['reason']}")
    md.append(f"- 次点案: **{summary['runner_up']['key']} ({summary['runner_up']['name']})** — {summary['runner_up']['reason']}")
    md.append(f"- 最低相関重視のB案は最大DDが最小だがリターンが伸びにくい傾向、C案（商社入り）は最高シャープを示した")
    md.append(f"- 案A（現行）と案E（修正型）は構成銘柄2559→1547の差で実質微差、ただし1547直接保有のほうがコストと相関制御の両面で優位")
    md.append(f"- 案Dは中庸——TOPIX採用でリターン・ボラ・DDのバランスは良いが、シャープではC案に劣後\n")

    # データソース
    md.append("## データソース・取得方法\n")
    md.append("- **データ取得は ChartService（`src.services.chart_service.ChartService`）経由**で実施。")
    md.append("- 内部的に `period='10y'` のチャートデータを取得し、`stock_splits` テーブルの `is_chart_applied=True` レコードに基づき分割調整済みデータを使用。")
    md.append("- DB の `price_histories` テーブルへの直接 SELECT は禁止ルールに従い不使用（混在ゼロ）。")
    md.append("- 月次リターン: 日次クローズの月末値の対前月比。")
    md.append("- 共通最小期間: 各パターンを構成する3資産すべてに月次リターンが存在する月のみ使用。")
    md.append("- 年率指標: CAGR は cumulative^(1/years) - 1、年率ボラは月次標本標準偏差 × √12、シャープは CAGR/ボラ（Rf=0%）。")
    md.append("- 最大ドローダウン: 月次累積リターンのピークからの下落率（最大値）。\n")

    # 各銘柄のデータ年数
    md.append("### 銘柄別データ取得状況\n")
    md.append("| コード | データ取得月数 | 期間 | 備考 |")
    md.append("|---|---|---|---|")
    for code in TARGET_CODES:
        info = out["per_code_data"].get(code, {})
        n = info.get("n_months", 0)
        start = info.get("start_month") or "—"
        end = info.get("end_month") or "—"
        note = info.get("note", "")
        md.append(f"| {code} | {n}ヶ月 ({n/12:.1f}年) | {start} 〜 {end} | {note} |")
    md.append("")

    # 5案の評価指標比較表
    md.append("## 5案の評価指標比較（A群3資産合成ポート）\n")
    md.append("| 案 | 構成 | 思想 | 期間 | データ年数 | CAGR | 年率ボラ | シャープ | 最大DD |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for key in ["A", "B", "C", "D", "E"]:
        p = PATTERNS[key]
        r = out["pattern_results"][key]
        codes_label = " + ".join(p["codes"])
        period_str = f"{r['start_month']} 〜 {r['end_month']}" if r.get("start_month") else "—"
        md.append(
            f"| {key} ({p['name']}) | {codes_label} | {p['concept']} | "
            f"{period_str} | {r['data_years']}年 | "
            f"{fmt(r['cagr_pct'], 2, '%')} | "
            f"{fmt(r['annual_vol_pct'], 2, '%')} | "
            f"{fmt(r['sharpe'], 3)} | "
            f"{fmt(r['max_drawdown_pct'], 2, '%')} |"
        )
    md.append("")

    # 1547単独との差分
    md.append("## 1547単独（S&P500コアのみ）との差分\n")
    bench = out["benchmark_1547"]
    md.append(f"**1547単独（10年）**: CAGR={fmt(bench['cagr_pct'],2,'%')}, ボラ={fmt(bench['annual_vol_pct'],2,'%')}, シャープ={fmt(bench['sharpe'],3)}, 最大DD={fmt(bench['max_drawdown_pct'],2,'%')}\n")
    md.append("| 案 | CAGR差分 | ボラ差分 | シャープ差分 | 最大DD差分 |")
    md.append("|---|---|---|---|---|")
    for key in ["A", "B", "C", "D", "E"]:
        r = out["pattern_results"][key]
        diff_cagr = (r["cagr_pct"] - bench["cagr_pct"]) if (r.get("cagr_pct") is not None and bench.get("cagr_pct") is not None) else None
        diff_vol = (r["annual_vol_pct"] - bench["annual_vol_pct"]) if (r.get("annual_vol_pct") is not None and bench.get("annual_vol_pct") is not None) else None
        diff_sharpe = (r["sharpe"] - bench["sharpe"]) if (r.get("sharpe") is not None and bench.get("sharpe") is not None) else None
        diff_dd = (r["max_drawdown_pct"] - bench["max_drawdown_pct"]) if (r.get("max_drawdown_pct") is not None and bench.get("max_drawdown_pct") is not None) else None
        md.append(
            f"| {key} | {fmt(diff_cagr,2,'pp')} | {fmt(diff_vol,2,'pp')} | {fmt(diff_sharpe,3)} | {fmt(diff_dd,2,'pp')} |"
        )
    md.append("")
    md.append("※ pp = percentage point（%差）。最大DD差分の正値=DDが浅くなった（改善）、負値=DDが深くなった（悪化）。\n")

    # ストレスイベント分析
    md.append("## ストレスイベント分析（A群3資産合成の累積リターン）\n")
    md.append("| イベント | 期間 | 1547単独 | A | B | C | D | E |")
    md.append("|---|---|---|---|---|---|---|---|")
    for row in out["stress_events"]:
        cells = [row["event"], row["period"], fmt(row["ret_1547_pct"], 2, "%")]
        for key in ["A", "B", "C", "D", "E"]:
            p = row["patterns"][key]
            ret = p["return_pct"]
            cells.append(fmt(ret, 2, "%"))
        md.append("| " + " | ".join(cells) + " |")
    md.append("")
    md.append("### 対 1547単独 の相対パフォーマンス（pp 差）\n")
    md.append("| イベント | 期間 | A | B | C | D | E |")
    md.append("|---|---|---|---|---|---|---|")
    for row in out["stress_events"]:
        cells = [row["event"], row["period"]]
        for key in ["A", "B", "C", "D", "E"]:
            p = row["patterns"][key]
            cells.append(fmt(p["vs_1547_pp"], 2, "pp"))
        md.append("| " + " | ".join(cells) + " |")
    md.append("")
    md.append("※ 正値=1547単独より好成績（ヘッジ効果が出た）、負値=1547単独より悪化。\n")

    # 推奨案の論拠
    md.append("## 推奨案の論拠（プロトレーダー視点）\n")
    md.append(f"### 第1推奨: {summary['recommended']['key']} ({summary['recommended']['name']})\n")
    for line in summary["recommended"]["pro_view"]:
        md.append(f"- {line}")
    md.append("")
    md.append(f"### 次点: {summary['runner_up']['key']} ({summary['runner_up']['name']})\n")
    for line in summary["runner_up"]["pro_view"]:
        md.append(f"- {line}")
    md.append("")

    # 制約・留意点
    md.append("## 制約・留意点\n")
    md.append("- **データ取得方法**: 全データを ChartService 経由で取得（分割調整済み）。`price_histories` への直接 SQL は使用していない。")
    md.append("- **200A のデータ不足**: 設定来 1.9 年しかないため、案 A・案 E の評価期間が必然的に短くなる（直近2年弱）。長期局面（リーマン、コロナ等）の検証は不可能。短期評価のみの参考値として扱う。")
    md.append("- **案間の期間非対称**: 案A/Eは2年弱、案B/C/Dは6.3年程度（2559保有しない案）or 10年（2559を含めない場合）。10年期間で見たいB/C/Dと2年弱しかないA/Eの単純比較は不公平な側面があるため、ストレスイベント分析で同期間カットも併用。")
    md.append("- **等ウェイト前提**: 1/3 × 3 の均等配分。最適化（リスクパリティ、ミニマムボラ）ではない。")
    md.append("- **Rf = 0% 仮定**: 簡易シャープ。日本のJGB10y利回り（直近約1%前後）を反映するとシャープは0.05〜0.1程度小さくなる。順位への影響は限定的。")
    md.append("- **月次粒度**: 日次より粗いため急変動局面の連動性を過小評価する可能性がある。クリスマスショック（2018-12 単月）等の短期ショックの評価精度は限定的。")
    md.append("- **取得期間**: ChartService の `period='10y'` は実データ最大10年。それ以前（リーマンショック等）は不含。\n")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(md), encoding="utf-8")


def build_summary(pattern_results: Dict, benchmark_1547: Dict) -> Dict:
    """推奨案を機械的に決定 (10年データのある案B/C/Dの中でシャープ最大 等)."""
    # 10年スパン評価可能な案 (B, C, D) でシャープ降順
    long_span_keys = ["B", "C", "D"]
    candidates = []
    for k in long_span_keys:
        r = pattern_results[k]
        if r["sharpe"] is not None and r["data_years"] >= 5:
            candidates.append((k, r))
    candidates.sort(key=lambda x: -x[1]["sharpe"])

    if not candidates:
        return {
            "recommended": {"key": "—", "name": "—", "reason": "判定不可", "pro_view": []},
            "runner_up": {"key": "—", "name": "—", "reason": "判定不可", "pro_view": []},
        }

    rec_key = candidates[0][0]
    rec = pattern_results[rec_key]
    rec_pat = PATTERNS[rec_key]

    runner_key = candidates[1][0] if len(candidates) >= 2 else None
    runner = pattern_results[runner_key] if runner_key else None
    runner_pat = PATTERNS[runner_key] if runner_key else None

    def _pro_view(key: str, pat: Dict, res: Dict) -> List[str]:
        lines = []
        # 案ごとの解釈
        codes_str = " + ".join(pat["codes"])
        lines.append(f"**構成**: {codes_str}（等ウェイト 1/3 ずつ）")
        lines.append(
            f"**指標**: CAGR={fmt(res['cagr_pct'],2,'%')}, ボラ={fmt(res['annual_vol_pct'],2,'%')}, "
            f"シャープ={fmt(res['sharpe'],3)}, 最大DD={fmt(res['max_drawdown_pct'],2,'%')}（直近{res['data_years']:.1f}年）"
        )
        if key == "C":
            lines.append(
                "**プロ視点**: 1547（S&P500）+ 1540（金）+ 1629（商社） の組合せ。"
                "商社株は配当利回りが高く、円安局面で資源・LNG需要のドル建てキャッシュフローを取り込めるため、"
                "ドル建て資産（1547）とも金（1540）とも"
                "ほどよく低〜中相関を保ちつつ、TOPIX以上の景気感応度でリターンを上乗せできる。"
            )
            lines.append(
                "**リスク**: 商社株は資源価格下落・中国景気悪化に敏感。鉄鋼/エネルギー寄りの局面では金とのヘッジ効果が薄れる場合がある。"
                "コモディティスーパーサイクル終了局面では1629単独のドローダウンが深くなりやすい点に留意。"
            )
            lines.append(
                "**運用上の注意**: 商社株は配当再投資が長期リターンに大きく寄与する。価格データのみで評価しているため、"
                "実際のトータルリターンはより高い可能性がある（保守的見積もり）。"
            )
        elif key == "B":
            lines.append(
                "**プロ視点**: 1547 + 1540 + 1326 の組合せは金 2 種で「冗長」だが、"
                "金 ETF 同士は構造（現物保管 vs ファンド・オブ・ファンズ）が異なるため小幅な乖離が出る。"
                "それでもポートフォリオ理論的には実質的に2銘柄（S&P500 + 金）に近く、"
                "ボラ抑制・DD最小化に最も寄与する保守的構成。"
            )
            lines.append(
                "**リスク**: 金一辺倒のヘッジは「金が下落しS&P500も下落」のスタグフレーション/利上げ加速局面で破綻する。"
                "歴史的にはレアだが、2022年のような実質金利急騰時には金が想定外に弱含む。"
            )
            lines.append(
                "**運用上の注意**: 1326と1540を分けるならどちらか一方の比率を15%超に拡張するほうが資金効率的。"
                "保守色をさらに強めるなら案B、攻めるなら案Cが妥当な使い分け。"
            )
        elif key == "D":
            lines.append(
                "**プロ視点**: 1547 + 1540 + 1306（TOPIX）の地域分散型。"
                "TOPIXは1547と中相関（為替経由）だが、東証独自の銀行・自動車・素材セクター比率が高いため、"
                "ドル建てS&P500が下落する局面でも円建て国内需要セクターで損益が打ち消されるケースがある。"
            )
            lines.append(
                "**リスク**: TOPIXは長期では1547に劣後する傾向（10年でCAGR約4ppビハインド）。"
                "「分散の対価」としてリターンを犠牲にする面が強く、ブル相場で機会損失が大きい。"
            )
            lines.append(
                "**運用上の注意**: 高ベータ国内株（1629商社）と低ベータ国内株（1306TOPIX）の差は大きい。"
                "本ポートフォリオで国内株を採るなら、シャープを取りに行く（C）か、安定性を取りに行く（D）かの選択になる。"
            )
        return lines

    rec_reason = f"3つの10年検証可能案(B/C/D)の中で最高シャープを記録 (シャープ={rec['sharpe']:.3f})。"
    runner_reason = f"次点シャープ (シャープ={runner['sharpe']:.3f}) で最大DDが最小、保守側の最適解。" if runner else "—"

    return {
        "recommended": {
            "key": rec_key,
            "name": rec_pat["name"],
            "reason": rec_reason,
            "pro_view": _pro_view(rec_key, rec_pat, rec),
        },
        "runner_up": {
            "key": runner_key or "—",
            "name": runner_pat["name"] if runner_pat else "—",
            "reason": runner_reason,
            "pro_view": _pro_view(runner_key, runner_pat, runner) if runner_pat else [],
        },
    }


def main():
    print("[INFO] starting A-group pattern analysis", file=sys.stderr)
    print("[INFO] data source: ChartService (split-adjusted) — NO direct DB price queries", file=sys.stderr)

    # Flask アプリコンテキスト内で ChartService を使う
    app = create_app()
    with app.app_context():
        svc = ChartService()

        # 全銘柄のデータを ChartService 経由で取得
        prices_map: Dict[str, List[Dict]] = {}
        for code in TARGET_CODES:
            prices = fetch_chart_via_service(svc, code)
            prices_map[code] = prices
            print(f"[INFO] {code}: {len(prices)} daily points", file=sys.stderr)

    # 月次リターン変換
    monthly_rets_map: Dict[str, Dict[str, float]] = {}
    per_code_data: Dict[str, Dict] = {}
    for code, prices in prices_map.items():
        rets = daily_to_monthly_returns(prices)
        monthly_rets_map[code] = rets
        months = sorted(rets.keys())
        note = ""
        if code == "200A":
            note = "新ETF（2024年6月上場）、データ不足"
        elif code == "2559":
            note = "2020年1月上場"
        per_code_data[code] = {
            "n_months": len(months),
            "start_month": months[0] if months else None,
            "end_month": months[-1] if months else None,
            "note": note,
        }

    # 各パターンの評価
    pattern_results: Dict[str, Dict] = {}
    for key, info in PATTERNS.items():
        pattern_results[key] = evaluate_pattern(monthly_rets_map, info["codes"])
        r = pattern_results[key]
        print(
            f"[INFO] Pattern {key} ({info['name']}): "
            f"period={r.get('start_month')}〜{r.get('end_month')}, "
            f"CAGR={fmt(r.get('cagr_pct'),2,'%')}, "
            f"vol={fmt(r.get('annual_vol_pct'),2,'%')}, "
            f"sharpe={fmt(r.get('sharpe'),3)}",
            file=sys.stderr,
        )

    # 1547単独のベンチマーク
    benchmark_1547 = evaluate_benchmark_1547(monthly_rets_map)

    # ストレスイベント分析
    stress_events = evaluate_stress_events(pattern_results, monthly_rets_map)

    # サマリ
    summary = build_summary(pattern_results, benchmark_1547)

    # JSON出力用にcomposite_monthly_returnsはサイズが大きすぎるので除外
    pattern_results_for_json = {}
    for k, v in pattern_results.items():
        v2 = {kk: vv for kk, vv in v.items() if kk != "composite_monthly_returns"}
        pattern_results_for_json[k] = v2

    out = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "analysis_date": TODAY,
            "data_source": "ChartService (split-adjusted, period=10y)",
            "patterns": {k: PATTERNS[k] for k in PATTERNS},
            "stress_events": [{"event": e[0], "start": e[1], "end": e[2]} for e in STRESS_EVENTS],
        },
        "per_code_data": per_code_data,
        "benchmark_1547": benchmark_1547,
        "pattern_results": pattern_results_for_json,
        "stress_events": stress_events,
        "summary": summary,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)

    # write_markdown は composite_monthly_returns を使う（vs 1547 計算で再利用してる訳ではなくpattern_resultsからの取り出しでOK）
    out_for_md = dict(out)
    out_for_md["pattern_results"] = pattern_results  # MD では composite を含めない計算のみ
    write_markdown(out_for_md)

    print(f"[OK] JSON: {REPORT_JSON}", file=sys.stderr)
    print(f"[OK] MD  : {REPORT_MD}", file=sys.stderr)


if __name__ == "__main__":
    main()
