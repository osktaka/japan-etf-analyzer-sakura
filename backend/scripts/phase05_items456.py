#!/usr/bin/env python3
"""
Phase 0.5: 項目4-6の計算（ストレスシナリオ、加重平均スコア、モメンタム分布）
"""
import json
import sys
import os
from pathlib import Path

# 環境変数設定
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

def main():
    if len(sys.argv) < 2:
        print("Usage: python phase05_items456.py <WORK_DIR>")
        sys.exit(1)

    work_dir = Path(sys.argv[1])

    # データ読み込み
    with open(work_dir / 'portfolio_data.json', 'r', encoding='utf-8') as f:
        pf_data = json.load(f)

    with open(work_dir / '_calc_temp.json', 'r', encoding='utf-8') as f:
        calc_data = json.load(f)

    def get_data(obj):
        return obj['data'] if isinstance(obj, dict) and 'data' in obj else obj

    holdings = get_data(pf_data['holdings'])
    total_value = calc_data['total_value']
    holding_ratios = calc_data['holding_ratios']
    etf_name_map = calc_data['etf_name_map']

    # tag_data: 銘柄ごとのタグリスト
    tag_data = get_data(pf_data['tag_data'])
    tag_by_etf = {}
    for t in tag_data:
        code = t['etf_code']
        if code not in tag_by_etf:
            tag_by_etf[code] = []
        tag_by_etf[code].append(t)

    # 4. ストレスシナリオ基礎数値
    scenarios = []

    # シナリオ1: 米国テック-20%
    us_tech_codes = [code for code, tags in tag_by_etf.items() if any(t['name'] in ['米国', 'テクノロジー'] for t in tags)]
    if us_tech_codes:
        impact_value = sum(holdings[i]['current_value'] for i, h in enumerate(holdings) if h['etf_code'] in us_tech_codes) * 0.2
        impact_ratio = impact_value / total_value
        scenarios.append({
            'name': '米国テック-20%',
            'target_codes': us_tech_codes,
            'impact_value': impact_value,
            'impact_ratio': impact_ratio,
        })

    # シナリオ2: 全世界株式-15%
    stock_codes = [code for code, tags in tag_by_etf.items() if any(t['name'] == '株式' for t in tags)]
    if stock_codes:
        impact_value = sum(holdings[i]['current_value'] for i, h in enumerate(holdings) if h['etf_code'] in stock_codes) * 0.15
        impact_ratio = impact_value / total_value
        scenarios.append({
            'name': '全世界株式-15%',
            'target_codes': stock_codes,
            'impact_value': impact_value,
            'impact_ratio': impact_ratio,
        })

    # シナリオ3: 円高進行（為替ヘッジなし外貨建て-15%）
    foreign_codes = [code for code, tags in tag_by_etf.items() if any(t['name'] in ['米国', '先進国', '新興国', '全世界'] for t in tags)]
    if foreign_codes:
        impact_value = sum(holdings[i]['current_value'] for i, h in enumerate(holdings) if h['etf_code'] in foreign_codes) * 0.15
        impact_ratio = impact_value / total_value
        scenarios.append({
            'name': '円高進行（USD/JPY 130→110、外貨建て-15%）',
            'target_codes': foreign_codes,
            'impact_value': impact_value,
            'impact_ratio': impact_ratio,
        })

    # 5. 加重平均スコア
    score_data = get_data(pf_data['score_cache'])

    # balance視点の5軸加重平均
    balance_scores = [s for s in score_data if s['perspective'] == 'balance']
    axes = ['dividend_power', 'cost_efficiency', 'scale_reliability', 'trading_quality', 'return_performance']
    axis_weighted = {}
    for axis in axes:
        weighted_sum = sum(s[axis] * holding_ratios[s['etf_code']] for s in balance_scores if s['etf_code'] in holding_ratios)
        axis_weighted[axis] = weighted_sum

    # 最弱軸・最強軸
    weakest_axis = min(axis_weighted, key=axis_weighted.get)
    strongest_axis = max(axis_weighted, key=axis_weighted.get)
    axis_diff = axis_weighted[strongest_axis] - axis_weighted[weakest_axis]

    # 視点別総合スコア加重平均
    perspectives = pf_data['_metadata']['score_cache']['perspectives']
    perspective_weighted = {}
    for persp in perspectives:
        persp_scores = [s for s in score_data if s['perspective'] == persp]
        weighted_sum = sum(s['total_score'] * holding_ratios[s['etf_code']] for s in persp_scores if s['etf_code'] in holding_ratios)
        perspective_weighted[persp] = weighted_sum

    # バリデーション
    for axis, val in axis_weighted.items():
        if not (0 <= val <= 100):
            print(f"警告: {axis}の加重平均が範囲外: {val:.2f}")

    # 6. モメンタム分布
    etf_data = get_data(pf_data['etf_data'])
    momentum_dist = {}
    for e in etf_data:
        label = e.get('momentum_label', '不明')
        if label not in momentum_dist:
            momentum_dist[label] = []
        momentum_dist[label].append(e['code'])

    # 下降中/下降加速の銘柄リスト
    declining = []
    for label in ['下降中', '下降加速', '失速']:
        if label in momentum_dist:
            for code in momentum_dist[label]:
                h = next((h for h in holdings if h['etf_code'] == code), None)
                if h:
                    declining.append({
                        'code': code,
                        'name': etf_name_map.get(code, code),
                        'ratio': holding_ratios[code],
                        'label': label,
                    })

    # 保存
    items456 = {
        'scenarios': scenarios,
        'axis_weighted': axis_weighted,
        'weakest_axis': weakest_axis,
        'strongest_axis': strongest_axis,
        'axis_diff': axis_diff,
        'perspective_weighted': perspective_weighted,
        'momentum_dist': momentum_dist,
        'declining': declining,
    }

    with open(work_dir / '_items456.json', 'w', encoding='utf-8') as f:
        json.dump(items456, f, ensure_ascii=False, indent=2)

    print("Phase 0.5 項目4-6計算完了")
    print(f"ストレスシナリオ: {len(scenarios)}件")
    print(f"5軸加重平均: {len(axis_weighted)}軸")
    print(f"視点別総合: {len(perspective_weighted)}視点")
    print(f"下降中銘柄: {len(declining)}件")

if __name__ == '__main__':
    main()
