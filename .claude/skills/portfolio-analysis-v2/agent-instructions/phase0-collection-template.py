"""
Phase 0: データ収集テンプレートスクリプト（サービス層直接アクセス版）

このファイルは phase0-data-collection.md のテンプレートスクリプトです。
サブエージェントがデータ収集スクリプトを実装する際の参考実装として使用します。

プレースホルダー:
  {USER_ID}   → 対象ユーザーID（文字列。例: "demo"）
  {WORK_DIR}  → 作業ディレクトリパス

注意: このテンプレートをコピーして使う場合、上記プレースホルダーを実際の値に置換すること。
サブエージェントが実装する場合は、メインから渡された引数で動的に置換する。
株式分割検証コードは本テンプレート末尾に組込済み。検証失敗時はスクリプトが停止する。

全データはサービス層（Python import）経由で取得する。HTTP APIは使用しない。
Flask app_context内で PortfolioService, AnalysisDataService 等を直接呼び出す。
"""

import os
import sys
import json
from pathlib import Path

# プロジェクトルート特定（Docker内: /app）
# Docker内実行時は /app がプロジェクトルート
PROJECT_ROOT = Path("/app")
BACKEND_DIR = PROJECT_ROOT / "backend"

# 環境変数設定
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

from src.app import create_app  # noqa: E402
from src.models.user import User  # noqa: E402
from src.services.portfolio_service import PortfolioService  # noqa: E402
from src.services.analysis_data_service import AnalysisDataService  # noqa: E402
from src.services.compare_service import CompareService  # noqa: E402
from src.services.recommend_service import RecommendService  # noqa: E402

# 作業ディレクトリ（引数から取得）
if len(sys.argv) < 2:
    print("Usage: python script.py <WORK_DIR>")
    sys.exit(1)
WORK_DIR = Path(sys.argv[1])
WORK_DIR.mkdir(parents=True, exist_ok=True)

USER_ID = '{USER_ID}'

# データソースの取得状態を記録
data_status = {}


def record_status(name, data=None, error=None):
    """データソースの取得状態を記録"""
    if error:
        data_status[name] = {"status": "error", "error": str(error)[:200]}
    elif data is None or (isinstance(data, list) and len(data) == 0) or (isinstance(data, dict) and len(data) == 0):
        data_status[name] = {"status": "empty", "detail": "データが空"}
    else:
        count = len(data) if isinstance(data, (list, dict)) else 1
        data_status[name] = {"status": "ok", "count": count}


app = create_app()
with app.app_context():
    # ユーザー検索（文字列のuser_idから整数のPK idを取得）
    user = User.query.filter_by(user_id=USER_ID).first()
    if not user:
        print(f"エラー: ユーザー '{USER_ID}' が見つかりません。")
        sys.exit(1)
    user_pk = user.id
    print(f"ユーザー: {USER_ID} (id={user_pk})")

    # サービスインスタンス化
    portfolio_service = PortfolioService()
    analysis_data_service = AnalysisDataService()
    compare_service = CompareService()
    recommend_service = RecommendService()

    # 1. 保有銘柄取得（分割調整済み）
    holdings = portfolio_service.get_holdings(user_pk)
    if not holdings:
        print("エラー: 保有銘柄が0件です。スキル全体を中止します。")
        sys.exit(1)
    etf_codes = [h['etf_code'] for h in holdings]
    record_status('holdings', data=holdings)
    print(f"保有銘柄数: {len(etf_codes)}")

    # 2. サマリー取得
    try:
        summary = portfolio_service.get_portfolio_summary(user_pk)
        record_status('summary', data=summary)
    except Exception as e:
        print(f"サマリー取得エラー: {e}")
        print("サマリーデータなしでは総資産検証が不可能。スクリプトを停止します。")
        sys.exit(1)

    # 3. 資産推移取得
    valuation_history = None
    try:
        valuation_history = portfolio_service.get_valuation_history(user_pk, '3y')
        record_status('valuation_history', data=valuation_history)
    except Exception as e:
        print(f"資産推移取得エラー: {e}（スキップ）")
        record_status('valuation_history', error=e)

    # 4. バルク分析データ（performance_cache, score_cache, etfs, tags, price_data）
    performance_data = []
    score_data = []
    etf_data = []
    tag_data = []
    price_data = []
    price_data_daily_30d = []
    price_data_close_250d = []

    try:
        analysis = analysis_data_service.get_analysis_data(etf_codes)
        performance_data = analysis.get('performance_cache', [])
        score_data = analysis.get('score_cache', [])
        etf_data = analysis.get('etf_data', [])
        tag_data = analysis.get('tag_data', [])
        price_data = analysis.get('price_data', [])
        price_data_daily_30d = analysis.get('price_data_daily_30d', [])
        price_data_close_250d = analysis.get('price_data_close_250d', [])
        record_status('performance_cache', data=performance_data)
        record_status('score_cache', data=score_data)
        record_status('etf_data', data=etf_data)
        record_status('tag_data', data=tag_data)
        record_status('price_data', data=price_data)
        record_status('price_data_daily_30d', data=price_data_daily_30d)
        record_status('price_data_close_250d', data=price_data_close_250d)
    except Exception as e:
        print(f"分析データ取得エラー: {e}")
        for name in ['performance_cache', 'score_cache', 'etf_data', 'tag_data', 'price_data', 'price_data_daily_30d', 'price_data_close_250d']:
            if name not in data_status:
                record_status(name, error=e)

    # 5. おすすめ
    recommendations = {}
    for perspective in ['balance', 'dividend', 'low-cost']:
        try:
            rec = recommend_service.get_recommendations(perspective=perspective)
            recommendations[perspective] = rec
            record_status(f'recommendations_{perspective}', data=rec.get('recommendations', []) if isinstance(rec, dict) else rec)
        except Exception as e:
            print(f"おすすめ取得エラー（{perspective}）: {e}（スキップ）")
            recommendations[perspective] = None
            record_status(f'recommendations_{perspective}', error=e)

    # 6. 比較（保有銘柄同士、5銘柄ずつ分割して取得）
    compare_performance_list = []
    compare_scores_list = []
    if len(etf_codes) >= 2:
        for i in range(0, len(etf_codes), 5):
            chunk = etf_codes[i:i+5]
            if len(chunk) >= 2:
                try:
                    comparison = compare_service.get_comparison(chunk)
                    compare_performance_list.append(comparison)
                    record_status('compare_performance', data=comparison)
                except Exception as e:
                    print(f"比較データ取得エラー: {e}（スキップ）")
                    compare_performance_list.append(None)
                    record_status('compare_performance', error=e)

                try:
                    scores = compare_service.get_scores(chunk)
                    compare_scores_list.append(scores)
                    record_status('compare_scores', data=scores)
                except Exception as e:
                    print(f"比較スコア取得エラー: {e}（スキップ）")
                    compare_scores_list.append(None)
                    record_status('compare_scores', error=e)

    # 7. yfinance配当データ取得（3年分、年別集計）
    dividend_data = {}
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        three_years_ago = datetime.now() - timedelta(days=3*365)
        dividend_fetch_errors = []

        for code in etf_codes:
            try:
                ticker = yf.Ticker(f"{code}.T")
                dividends = ticker.dividends
                if dividends is not None and len(dividends) > 0:
                    # 3年以内のデータに絞り込み
                    recent = dividends[dividends.index >= three_years_ago.strftime('%Y-%m-%d')]
                    if len(recent) > 0:
                        yearly = {}
                        for idx, val in recent.items():
                            year = str(idx.year)
                            yearly[year] = yearly.get(year, 0) + float(val)
                        dividend_data[code] = yearly
                    else:
                        dividend_data[code] = {}
                else:
                    dividend_data[code] = {}
            except Exception as e:
                print(f"配当データ取得エラー（{code}）: {e}（スキップ）")
                dividend_fetch_errors.append(f"{code}: {str(e)[:100]}")
                dividend_data[code] = {}

        if dividend_data and any(len(v) > 0 for v in dividend_data.values()):
            record_status('dividend_data', data=dividend_data)
        elif dividend_fetch_errors:
            record_status('dividend_data', error=f"一部取得失敗: {'; '.join(dividend_fetch_errors[:3])}")
        else:
            record_status('dividend_data', data={})
            print("配当データ: 全銘柄で配当データなし")
    except ImportError:
        print("yfinanceがインストールされていません。配当データをスキップします。")
        dividend_data = None
        record_status('dividend_data', error="yfinanceモジュールが利用不可")
    except Exception as e:
        print(f"配当データ取得で予期しないエラー: {e}")
        dividend_data = None
        record_status('dividend_data', error=str(e)[:200])

    # _metadata生成（アナリストがフィールド名を正確に把握するため）
    def build_metadata(data, extra_info=None):
        if not data:
            return {"count": 0, "columns": [], "sample": None}
        first = data[0] if isinstance(data, list) else data
        meta = {"count": len(data), "columns": list(first.keys()), "sample": {k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v for k, v in first.items()}}
        if extra_info:
            meta.update(extra_info)
        return meta

    _metadata = {
        "score_cache": build_metadata(score_data, {
            "perspectives": sorted(set(r['perspective'] for r in score_data)) if score_data else [],
            "axes": ["dividend_power", "cost_efficiency", "scale_reliability", "trading_quality", "return_performance"]
        }),
        "performance_cache": build_metadata(performance_data, {
            "periods": sorted(set(r['period'] for r in performance_data)) if performance_data else []
        }),
        "price_data": build_metadata(price_data),
        "price_data_daily_30d": build_metadata(price_data_daily_30d),
        "price_data_close_250d": build_metadata(price_data_close_250d),
        "dividend_data": {
            "count": len(dividend_data) if dividend_data else 0,
            "columns": ["etf_code"],
            "sample": {k: v for k, v in list(dividend_data.items())[:1]} if dividend_data and len(dividend_data) > 0 else None
        },
        "etf_data": build_metadata(etf_data),
        "tag_data": build_metadata(tag_data),
        "etf_codes": etf_codes,
        "holding_count": len(etf_codes),
        "_data_status": data_status
    }

    # === 分析データ全失敗チェック ===
    api_sources = ['performance_cache', 'score_cache', 'etf_data', 'tag_data', 'price_data', 'price_data_daily_30d', 'price_data_close_250d']
    api_all_failed = all(data_status.get(s, {}).get('status') == 'error' for s in api_sources)
    if api_all_failed:
        print("分析データが全て取得失敗。有用な分析レポートを生成できません。")
        print("推奨: Docker環境・DB状態を確認してください。")
        sys.exit(1)

    # === 株式分割調整データの検証（必須） ===
    # 重要: holdingsデータは PortfolioService.get_holdings() 経由で取得された値。
    # サービス層はSplitAdjustmentServiceを内包して株式分割調整済みデータを返す。
    # DB（tradesテーブル）への直接クエリは一切含まれていない。
    #
    # 【禁止】tradesテーブルへの直接クエリ（SELECT * FROM trades等）は
    # 分割前の元の数量・単価が返されるため、絶対に使用しないこと。
    # 詳細: phase0-data-collection.md「禁止パターン」セクション参照
    print("--- データ整合性検証 ---")
    cash_v = summary.get('cash_balance', 0)
    total_asset_v = summary.get('total_asset', 0)

    validation_errors = []
    total_cv_v = 0
    for h in holdings:
        qty = h.get('quantity', 0)
        price = h.get('current_price', 0)
        cv = h.get('current_value', 0)
        calc_cv = qty * price
        if abs(calc_cv - cv) > 1:  # 1円以上の誤差
            validation_errors.append(
                f"評価額不整合: {h['etf_code']} {qty}口×{price}円={calc_cv}円 ≠ {cv}円"
            )
        avg_cost = h.get('average_cost', 0)
        total_cost_h = h.get('total_cost', 0)
        calc_tc = round(avg_cost * qty, 2)
        if abs(calc_tc - total_cost_h) > 1:
            validation_errors.append(
                f"取得原価不整合: {h['etf_code']} {avg_cost}円×{qty}口={calc_tc}円 ≠ {total_cost_h}円"
            )
        total_cv_v += cv

    calc_total_v = total_cv_v + cash_v
    if abs(calc_total_v - total_asset_v) > 10:  # 10円以上の誤差
        validation_errors.append(
            f"総資産不整合: 銘柄合計{total_cv_v}円 + 現金{cash_v}円 "
            f"= {calc_total_v}円 ≠ サマリー{total_asset_v}円"
        )

    if validation_errors:
        print("データ検証エラー:")
        for err in validation_errors:
            print(f"  - {err}")
        print("不正確なデータでの分析を防止するため、スクリプトを停止します。")
        sys.exit(1)

    print(f"検証OK: 総資産{total_asset_v:,.0f}円"
          f"（銘柄{total_cv_v:,.0f}円 + 現金{cash_v:,.0f}円）")

    # データ保存（holdingsとsummaryはサービス層の直接戻り値なのでラッパー不要）
    # ただし後方互換のため、API風の {"data": ...} 形式で保存
    output = {
        'user_id': USER_ID,
        '_metadata': _metadata,
        'holdings': {'data': holdings},
        'summary': {'data': summary},
        'valuation_history': {'data': valuation_history} if valuation_history else None,
        'performance_cache': performance_data if performance_data else None,
        'score_cache': score_data if score_data else None,
        'etf_data': etf_data if etf_data else None,
        'tag_data': tag_data if tag_data else None,
        'price_data': price_data if price_data else None,
        'price_data_daily_30d': price_data_daily_30d if price_data_daily_30d else None,
        'price_data_close_250d': price_data_close_250d if price_data_close_250d else None,
        'dividend_data': dividend_data,
        'recommendations': recommendations,
        'compare_performance': compare_performance_list if compare_performance_list else None,
        'compare_scores': compare_scores_list if compare_scores_list else None,
    }

    output_path = WORK_DIR / '00_portfolio_data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    # 00_portfolio_reference.md の生成（レポートのセクション1・11.2で使用するmarkdownテーブル）
    holdings_data = holdings
    cash = summary.get('cash_balance', 0)
    total_asset_from_summary = summary.get('total_asset', 0)

    total_cv = sum(h.get('current_value', 0) for h in holdings_data)
    total_pnl = sum(h.get('unrealized_pnl', 0) for h in holdings_data)
    total_cost = sum(h.get('total_cost', 0) for h in holdings_data)
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    ref_lines = []
    ref_lines.append("# ポートフォリオ参照データ（プログラマティック生成）")
    ref_lines.append("")
    ref_lines.append("> このファイルはPhase 0のPythonスクリプトで自動生成されました。")
    ref_lines.append("> Phase 3+4統合エージェントは、セクション1.1/1.2/11.2をこのファイルからそのまま転記してください。")
    ref_lines.append("> 数値の丸め・フォーマット変更は禁止です。")
    ref_lines.append("")

    # セクション1.1用テーブル
    ref_lines.append("## セクション1.1: 銘柄別保有状況")
    ref_lines.append("")
    ref_lines.append("| コード | 銘柄名 | 保有数量 | 平均取得単価 | 現在価格 | 評価額 | 損益 | 損益率 | 保有比率 |")
    ref_lines.append("|-------|--------|---------|------------|---------|-------|------|-------|---------|")
    for h in holdings_data:
        code = h['etf_code']
        etf_info = h.get('etf', {})
        name = etf_info.get('name', code) if isinstance(etf_info, dict) else code
        qty = h.get('quantity', 0)
        avg_cost = h.get('average_cost', 0)
        price = h.get('current_price', 0)
        cv = h.get('current_value', 0)
        pnl = h.get('unrealized_pnl', 0)
        pnl_pct = h.get('unrealized_pnl_percent', 0)
        ratio = (cv / total_cv * 100) if total_cv > 0 else 0
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_pct_sign = "+" if pnl_pct >= 0 else ""
        ref_lines.append(
            f"| {code} | {name} | {qty:,.0f}口 | {avg_cost:,.1f}円 | {price:,.0f}円 | {cv:,.0f}円 | {pnl_sign}{pnl:,.0f}円 | {pnl_pct_sign}{pnl_pct:.1f}% | {ratio:.1f}% |"
        )
    ref_lines.append("")

    # セクション1.2用サマリー
    ref_lines.append("## セクション1.2: サマリー")
    ref_lines.append("")
    ref_lines.append("```")
    ref_lines.append(f"合計評価額: {total_cv:,.0f}円")
    ref_lines.append(f"現金残高: {cash:,.0f}円")
    ref_lines.append(f"総資産: {total_asset_from_summary:,.0f}円")
    pnl_sign = "+" if total_pnl >= 0 else ""
    pnl_pct_sign = "+" if total_pnl_pct >= 0 else ""
    ref_lines.append(f"含み損益合計: {pnl_sign}{total_pnl:,.0f}円（{pnl_pct_sign}{total_pnl_pct:.1f}%）")
    ref_lines.append("```")
    ref_lines.append("")

    # セクション11.2用注記
    ref_lines.append("## セクション11.2: 現行ポートフォリオ（改善前）")
    ref_lines.append("")
    ref_lines.append("> セクション1.1のテーブルと同一内容をそのまま転記してください。")
    ref_lines.append("")

    # チェック値（検証用）
    ref_lines.append("## チェック値")
    ref_lines.append("")
    ref_lines.append(f"- 銘柄数: {len(holdings_data)}")
    ref_lines.append(f"- 合計評価額: {total_cv:,.0f}円")
    ref_lines.append(f"- 現金残高: {cash:,.0f}円")
    ref_lines.append(f"- 総資産: {total_asset_from_summary:,.0f}円")

    ref_path = WORK_DIR / '00_portfolio_reference.md'
    with open(ref_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ref_lines))
    print(f"参照データ生成: {ref_path}")

    # メインへの要約出力（この1行のみがメインのコンテキストに入る）
    total_value = summary.get('total_value', 0)
    print(f"データ収集完了: {len(etf_codes)}銘柄、総評価額{total_value:,.0f}円")
