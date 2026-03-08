#!/usr/bin/env python3
"""Phase 0出力（00_portfolio_data.json）の品質検証スクリプト。
使い方: python validate_phase0.py {WORK_DIR}
出力: JSON { "status": "OK"|"WARN"|"NG", "results": {...}, "warnings": [...] }
"""
import json, sys
from pathlib import Path

REQUIRED_KEYS = ["holdings", "summary", "_metadata", "_data_status"]
HOLDING_FIELDS = ("quantity", "current_price", "current_value")


def validate(work_dir: Path) -> tuple[dict, list[str]]:
    """00_portfolio_data.jsonの4ルール検証を実行する。"""
    results, warnings = {}, []
    filepath = work_dir / "00_portfolio_data.json"
    # ルール1: 存在・パース・必須キー
    if not filepath.exists():
        return {"file_exists": "NG:not_found"}, ["ファイルが存在しない"]
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"file_parse": f"NG:{e}"}, ["パース失敗"]
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        return {"required_keys": f"NG:missing_{','.join(missing)}"}, [f"必須キー不足: {', '.join(missing)}"]
    results["required_keys"] = "OK"

    # ルール2-3: holdings各銘柄の値チェック + 評価額計算チェック
    null_errs, calc_errs = [], []
    for h in data["holdings"]:
        t = h.get("ticker_code", "?")
        qty, price, val = (h.get(f) for f in HOLDING_FIELDS)
        for f, v in zip(HOLDING_FIELDS, (qty, price, val)):
            if v is None or v == 0:
                null_errs.append(f"{t}.{f}={v}")
        if all(v is not None and v != 0 for v in (qty, price, val)):
            if abs(qty * price - val) > 1:
                calc_errs.append(f"{t}:{qty}*{price}!={val}")
    results["holdings_values"] = "OK" if not null_errs else f"NG:{';'.join(null_errs)}"
    results["value_calc"] = "OK" if not calc_errs else f"NG:{';'.join(calc_errs)}"
    if null_errs:
        warnings.append(f"holdings値異常: {'; '.join(null_errs)}")
    if calc_errs:
        warnings.append(f"評価額計算不一致: {'; '.join(calc_errs)}")

    # ルール4: Σ(current_value) + cash ≈ total_asset（誤差10円以内）
    summary = data["summary"]
    total_cv = sum(h.get("current_value", 0) for h in data["holdings"])
    cash = summary.get("cash_balance")
    if cash is None:
        cash = summary.get("cash", 0)
    total_asset = summary.get("total_asset", 0)
    diff = abs(total_cv + cash - total_asset)
    if diff > 10:
        results["total_asset"] = f"NG:sum={total_cv}+cash={cash},total={total_asset},diff={diff}"
        warnings.append(f"総資産不一致: 差額{diff}円")
    else:
        results["total_asset"] = "OK"

    # WARN判定: _data_status内のerrorが3件以上
    err_cnt = sum(1 for v in data.get("_data_status", {}).values() if v == "error")
    if err_cnt >= 3:
        warnings.append(f"_data_status内のerror={err_cnt}件")

    return results, warnings


def main():
    if len(sys.argv) < 2:
        print("使い方: python validate_phase0.py {WORK_DIR}", file=sys.stderr); sys.exit(1)
    work_dir = Path(sys.argv[1])
    if not work_dir.exists():
        print(f"エラー: ディレクトリが存在しません: {work_dir}", file=sys.stderr); sys.exit(1)
    results, warnings = validate(work_dir)
    has_ng = any(v.startswith("NG") for v in results.values())
    has_warn = any("_data_status" in w for w in warnings)
    status = "NG" if has_ng else ("WARN" if has_warn else "OK")
    print(json.dumps({"status": status, "results": results, "warnings": warnings}, ensure_ascii=False, indent=2))
    sys.exit(1 if status == "NG" else 0)


if __name__ == "__main__":
    main()
