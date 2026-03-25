"""market-outlook-v2 レポートの機械検証スクリプト

使い方:
  python report_validate.py <レポートパス> <market_data JSONパス> [--timing am|pm]
  --timing 未指定時はファイル名パターン (_am_ / _pm_) で自動判定。

出力 (stdout): {"status": "OK|WARN|FAIL", "errors": [...], "warnings": [...], "summary": {...}}
"""
import argparse, json, re, sys
from pathlib import Path
import yaml

# --- 定数 ---
PRICE_KEYS = ["sp500", "nasdaq", "vix", "nikkei_futures", "usdjpy"]
FMTS = ["{:,.2f}", "{:.2f}", "{:,.1f}", "{:.1f}", "{:,.0f}", "{:.0f}"]
DELTAS = [i / 100 for i in range(-5, 6) if i != 0]
AM_FIELDS = ["direction", "confidence", "cme_nikkei", "range_low", "range_high",
             "difficulty", "causal_chain", "key_assumption", "invalidation_signal",
             "high_volatility", "crisis_mode"]
PM_FIELDS = ["direction_hit", "range_hit", "cme_deviation", "cme_deviation_pct",
             "core_premise_hit", "invalidation_triggered", "notes"]
DIRECTION_OK = {"上昇", "下落", "横ばい", "やや強気", "やや弱気"}
CONFIDENCE_OK = {"高", "中", "低"}
SECTION_RE = re.compile(r"^#{2,3}\s+(\d+)\.", re.MULTILINE)
SEC7_RE = re.compile(r"^#{2,3}\s+7\.\s.*?\n(.*?)(?=^#{2,3}\s+\d+\.|\Z)", re.MULTILINE | re.DOTALL)
IF_THEN_WORDS = [re.compile(w) for w in ["こうなれば", "逆に", "場合"]]
FORBIDDEN = [re.compile(p) for p in [
    r"必ず(上がる|下がる|上昇|下落)", r"確実に", r"(買う|売る)べき", r"\d+%の確率",
    r"\[ws\]", r"(?<!\S)暴落(?!\S)", r"(?<!\S)急騰(?!\S)", r"売り推奨", r"買い推奨"]]

def _strip(text):
    text = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL)
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

def _extract_yaml(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None

def _find_price(body, price):
    for fmt in FMTS:
        if re.search(re.escape(fmt.format(price)), body):
            return True
    for d in DELTAS:
        for fmt in FMTS:
            if re.search(re.escape(fmt.format(price + d)), body):
                return True
    return False

# --- RV-A ---
def check_a(body, md):
    errs, warns, missing = [], [], []
    for k in PRICE_KEYS:
        e = md.get(k)
        if not isinstance(e, dict):
            continue
        p = e.get("price")
        if p is not None and not _find_price(body, p):
            missing.append(k)
    msg = f"RV-A: 指標 {len(missing)}/5 が本文に未発見 ({', '.join(missing)})"
    if len(missing) >= 3:
        errs.append(msg.replace("指標", "主要指標"))
    elif missing:
        warns.append(msg)
    return errs, warns

# --- RV-B ---
def check_b(yd, timing):
    errs = []
    if yd is None:
        return ["RV-B: YAMLフロントマターが見つかりません"]
    sec_name = "prediction" if timing == "am" else "accuracy"
    fields = AM_FIELDS if timing == "am" else PM_FIELDS
    sec = yd.get(sec_name)
    if not isinstance(sec, dict):
        return [f"RV-B: '{sec_name}' セクションが存在しません"]
    for f in fields:
        if f not in sec:
            errs.append(f"RV-B: '{sec_name}.{f}' が欠落しています")
    if timing == "am" and isinstance(sec, dict):
        if sec.get("direction") not in (None, *DIRECTION_OK):
            errs.append(f"RV-B: prediction.direction '{sec['direction']}' が不正")
        if sec.get("confidence") not in (None, *CONFIDENCE_OK):
            errs.append(f"RV-B: prediction.confidence '{sec['confidence']}' が不正")
        d = sec.get("difficulty")
        if d is not None and not (isinstance(d, (int, float)) and 1 <= d <= 5):
            errs.append(f"RV-B: prediction.difficulty '{d}' が不正 (1-5)")
        for bk in ["high_volatility", "crisis_mode"]:
            if sec.get(bk) not in (None, True, False):
                errs.append(f"RV-B: prediction.{bk} が不正 (true/false)")
    if timing == "pm" and isinstance(sec, dict):
        for bk in ["direction_hit", "range_hit", "core_premise_hit", "invalidation_triggered"]:
            if bk in sec and sec[bk] not in (True, False, None):
                errs.append(f"RV-B: accuracy.{bk} が不正 (true/false/null)")
    return errs

# --- RV-C ---
def check_c(body):
    errs, warns = [], []
    nums = {int(m.group(1)) for m in SECTION_RE.finditer(body) if 1 <= int(m.group(1)) <= 9}
    c = len(nums)
    if c < 5:
        errs.append(f"RV-C: セクション {c}/9 のみ検出 (5未満でFAIL)")
    elif c < 7:
        warns.append(f"RV-C: セクション {c}/9 検出 (7未満でWARN)")
    s7 = SEC7_RE.search(body)
    if s7 and not any(p.search(s7.group(1)) for p in IF_THEN_WORDS):
        warns.append("RV-C: セクション7に「こうなれば/逆に/場合」パターンが未検出")
    return errs, warns

# --- RV-D ---
def check_d(text):
    warns = []
    for i, line in enumerate(_strip(text).split("\n"), 1):
        for pat in FORBIDDEN:
            m = pat.search(line)
            if m:
                warns.append(f"RV-D: L{i} 禁止表現 '{m.group()}': {line.strip()}")
    return warns

# --- 統合 ---
def validate(report_text, market_data, timing):
    body = _strip(report_text)
    yd = _extract_yaml(report_text)
    a_e, a_w = check_a(body, market_data)
    b_e = check_b(yd, timing)
    c_e, c_w = check_c(body)
    d_w = check_d(report_text)
    errors = a_e + b_e + c_e
    warnings = a_w + c_w + d_w
    ck = {"RV-A": "FAIL" if a_e else ("WARN" if a_w else "PASS"),
          "RV-B": "FAIL" if b_e else "PASS",
          "RV-C": "FAIL" if c_e else ("WARN" if c_w else "PASS"),
          "RV-D": "WARN" if d_w else "PASS"}
    status = "FAIL" if errors else ("WARN" if warnings else "OK")
    return {"status": status, "errors": errors, "warnings": warnings,
            "summary": {"checks_run": 4,
                        "checks_passed": sum(v == "PASS" for v in ck.values()),
                        "checks_warned": sum(v == "WARN" for v in ck.values()),
                        "checks_failed": sum(v == "FAIL" for v in ck.values()),
                        "timing": timing, "report_file": "", "details": ck}}

def _fail_exit(msg):
    json.dump({"status": "FAIL", "errors": [msg], "warnings": [], "summary": {}},
              sys.stdout, ensure_ascii=False, indent=2)
    print()
    sys.exit(1)

def main():
    ap = argparse.ArgumentParser(description="market-outlook-v2 レポート検証")
    ap.add_argument("report_path", help="レポートファイルのパス (.md)")
    ap.add_argument("market_data_path", help="market_data JSONファイルのパス")
    ap.add_argument("--timing", choices=["am", "pm"], help="AM/PM指定")
    args = ap.parse_args()
    rp, mp = Path(args.report_path), Path(args.market_data_path)
    if not rp.exists():
        _fail_exit(f"レポートファイルが見つかりません: {rp}")
    if not mp.exists():
        _fail_exit(f"market_data JSONが見つかりません: {mp}")
    try:
        md = json.loads(mp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _fail_exit(f"market_data JSONパースエラー: {e}")
    timing = args.timing
    if not timing:
        n = rp.name
        timing = "am" if ("_am_" in n or "_am." in n) else ("pm" if ("_pm_" in n or "_pm." in n) else None)
    if not timing:
        _fail_exit("timingを判定できません。--timing am|pm を指定してください")
    result = validate(rp.read_text(encoding="utf-8"), md, timing)
    result["summary"]["report_file"] = rp.name
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    if result["status"] == "FAIL":
        sys.exit(1)

if __name__ == "__main__":
    main()
