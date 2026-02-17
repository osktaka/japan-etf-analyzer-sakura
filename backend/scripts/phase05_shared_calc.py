#!/usr/bin/env python3
"""
Phase 0.5: 共通定量計算スクリプト
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

import pandas as pd
import numpy as np

def main():
    # コマンドライン引数でWORK_DIRを受け取る
    if len(sys.argv) < 2:
        print("Usage: python phase05_shared_calc.py <WORK_DIR>")
        sys.exit(1)

    work_dir = Path(sys.argv[1])
    if not work_dir.exists():
        print(f"Error: WORK_DIR not found: {work_dir}")
        sys.exit(1)

    # データ読み込み
    with open(work_dir / 'portfolio_data.json', 'r', encoding='utf-8') as f:
        pf_data = json.load(f)

    # リスクフリーレート取得
    try:
        with open(work_dir / 'market_environment.md', 'r', encoding='utf-8') as f:
            mkt_env = f.read()
        import re
        if '## リスクフリーレート' in mkt_env:
            rf_section = mkt_env.split('## リスクフリーレート')[1].split('##')[0]
            match = re.search(r'(\d+\.\d+)%', rf_section)
            if match:
                risk_free_rate = float(match.group(1))
                rf_source = f"{risk_free_rate}%（日本国債10年利回り、market_environment.mdより）"
            else:
                risk_free_rate = 0.5
                rf_source = "0.5%（フォールバック値: 数値抽出失敗）"
        else:
            risk_free_rate = 0.5
            rf_source = "0.5%（フォールバック値: リスクフリーレートセクションなし）"
    except Exception as e:
        risk_free_rate = 0.5
        rf_source = f"0.5%（フォールバック値: {str(e)}）"

    # データ構造を統一的に取得（dict['data']またはlist）
    def get_data(obj):
        return obj['data'] if isinstance(obj, dict) and 'data' in obj else obj

    # holdings: 保有比率
    holdings = get_data(pf_data['holdings'])
    total_value = sum(h['current_value'] for h in holdings)
    holding_ratios = {h['etf_code']: h['current_value'] / total_value for h in holdings}

    # etf_data: 銘柄情報マップ
    etf_data_list = get_data(pf_data['etf_data'])
    etf_data_map = {e['code']: e for e in etf_data_list}

    # holdingsからetf名を取得
    etf_name_map = {h['etf_code']: h['etf']['name'] for h in holdings}

    # performance_cache: 1yデータ
    perf_data = get_data(pf_data['performance_cache'])
    perf_1y = {p['etf_code']: p for p in perf_data if p.get('period') == '1y'}

    # 1. シャープレシオ
    sharpe_results = []
    for code, perf in perf_1y.items():
        ret = perf['return_rate']
        vol = perf.get('volatility')
        if vol and vol > 0:
            sharpe = (ret - risk_free_rate) / vol
            sharpe_results.append({
                'code': code,
                'name': etf_name_map.get(code, code),
                'return': ret,
                'volatility': vol,
                'sharpe': sharpe
            })
    sharpe_results.sort(key=lambda x: x['sharpe'], reverse=True)

    # 2. 相関分析（月次リターン）
    price_data = get_data(pf_data['price_data'])
    df_price = pd.DataFrame(price_data)
    df_price['date'] = pd.to_datetime(df_price['date'])
    df_price['ym'] = df_price['date'].dt.to_period('M')
    monthly_first = df_price.sort_values('date').groupby(['etf_code', 'ym']).first().reset_index()

    pivot = monthly_first.pivot(index='ym', columns='etf_code', values='close')
    monthly_returns = pivot.pct_change().dropna()

    corr_matrix = monthly_returns.corr()

    high_corr = []
    low_corr = []
    codes = corr_matrix.columns.tolist()
    for i, code1 in enumerate(codes):
        for code2 in codes[i+1:]:
            corr_val = corr_matrix.loc[code1, code2]
            if corr_val > 0.7:
                high_corr.append({
                    'code1': code1,
                    'name1': etf_name_map.get(code1, code1),
                    'code2': code2,
                    'name2': etf_name_map.get(code2, code2),
                    'corr': float(corr_val)
                })
            elif corr_val < 0.3:
                low_corr.append({
                    'code1': code1,
                    'name1': etf_name_map.get(code1, code1),
                    'code2': code2,
                    'name2': etf_name_map.get(code2, code2),
                    'corr': float(corr_val)
                })

    # ポートフォリオ月次リターン
    pf_monthly_returns = (monthly_returns * pd.Series(holding_ratios)).sum(axis=1)

    # 7. VaR/CVaR
    var_cvar = None
    if len(monthly_returns) >= 6:
        var_95 = float(pf_monthly_returns.quantile(0.05))
        cvar_95 = float(pf_monthly_returns[pf_monthly_returns <= var_95].mean())
        var_cvar = {
            'var_95': var_95,
            'cvar_95': cvar_95,
            'var_amount': var_95 * total_value,
            'cvar_amount': cvar_95 * total_value,
            'data_points': len(pf_monthly_returns),
        }

    # 3. 最大ドローダウン
    val_history = get_data(pf_data['valuation_history'])
    max_dd_result = None
    if len(val_history) >= 10:
        df_val = pd.DataFrame(val_history)
        df_val['date'] = pd.to_datetime(df_val['date'])
        df_val = df_val.sort_values('date')

        df_val['cummax'] = df_val['value'].cummax()
        df_val['dd'] = (df_val['value'] - df_val['cummax']) / df_val['cummax']

        max_dd_idx = df_val['dd'].idxmin()
        max_dd = float(df_val.loc[max_dd_idx, 'dd'])
        bottom_date = df_val.loc[max_dd_idx, 'date']

        peak_idx = df_val.loc[:max_dd_idx, 'value'].idxmax()
        peak_date = df_val.loc[peak_idx, 'date']

        recovery = df_val.loc[max_dd_idx:, :]
        recovery_idx = recovery[recovery['value'] >= recovery.loc[max_dd_idx, 'cummax']].index
        if len(recovery_idx) > 0:
            recovery_date = df_val.loc[recovery_idx[0], 'date']
            recovery_days = int((recovery_date - bottom_date).days)
        else:
            recovery_date = None
            recovery_days = None

        max_dd_result = {
            'dd': max_dd,
            'peak_date': str(peak_date.date()),
            'bottom_date': str(bottom_date.date()),
            'recovery_date': str(recovery_date.date()) if recovery_date else None,
            'recovery_days': recovery_days,
        }

    # 保存
    output = {
        'risk_free_rate': risk_free_rate,
        'rf_source': rf_source,
        'total_value': total_value,
        'holding_ratios': holding_ratios,
        'sharpe_results': sharpe_results,
        'high_corr': high_corr,
        'low_corr': low_corr,
        'monthly_returns_count': len(monthly_returns),
        'var_cvar': var_cvar,
        'max_dd': max_dd_result,
        'val_history_count': len(val_history),
        'etf_name_map': etf_name_map,
    }

    with open(work_dir / '_calc_temp.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Phase 0.5 計算完了（項目1-3, 7）")
    print(f"リスクフリーレート: {rf_source}")
    print(f"シャープレシオ: {len(sharpe_results)}銘柄")
    print(f"相関分析: {len(monthly_returns)}ヶ月分")
    print(f"VaR/CVaR: {'算出' if var_cvar else 'スキップ'}")
    print(f"最大DD: {'算出' if max_dd_result else 'スキップ'}")

if __name__ == '__main__':
    main()
