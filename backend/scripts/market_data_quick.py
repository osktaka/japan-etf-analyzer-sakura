"""市場データのクイック取得スクリプト（market-outlookスキル用）

yfinanceを使用して主要指標をJSON形式で標準出力に出力する。
DB接続は不要。

使い方:
  python market_data_quick.py        # AM用（米国指標のみ）
  python market_data_quick.py --pm   # PM用（米国指標 + 東証指標）
"""

import json
import sys
from datetime import datetime, timezone, timedelta

# Yahoo Finance API 429エラー対策: User-Agentを強制的に上書き
# yfinance 0.1.63が設定する古いUser-Agent (Chrome 39, 2014年) をブロック回避のため置換
import requests

original_prepare_request = requests.Session.prepare_request


def custom_prepare_request(self, request):
    request.headers[
        "User-Agent"
    ] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    return original_prepare_request(self, request)


requests.Session.prepare_request = custom_prepare_request

import yfinance as yf  # noqa: E402

# AM用ティッカー（米国指標）
TICKERS = {
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow": "^DJI",
    "vix": "^VIX",
    "us10y": "^TNX",
    "nikkei_futures": "NKD=F",
    "usdjpy": "USDJPY=X",
    "wti_oil": "CL=F",      # WTI原油先物
    "gold": "GC=F",          # 金先物
    "us3m": "^IRX",          # 米13週国債利回り（短期金利指標）
    "sox": "^SOX",            # フィラデルフィア半導体指数
}

# PM用追加ティッカー（東証指標）
# --pm 指定時にTICKERSと合わせて取得する
# NOTE: TOPIX (^TPX) はyfinanceで取得不可（delisted扱い）→ WebFetchフォールバック対象
PM_TICKERS = {
    "nikkei225": "^N225",       # 日経平均株価
    "topix_etf": "1306.T",     # TOPIX連動型ETF（TOPIX代替、^TPXはyfinance非対応）
    "growth250": "2516.T",      # MAXIS東証グロース250 ETF（グロース250指数の代替）
    "reit_index": "1343.T",     # NEXT FUNDS 東証REIT指数連動型ETF
    "bank_etf": "1615.T",      # 東証銀行業株価指数ETF（銀行セクター代替）
    "it_etf": "1626.T",        # NEXT FUNDS 情報通信・サービスその他ETF
}

JST = timezone(timedelta(hours=9))

# テクニカル指標を算出するティッカー名の定義
# AM用: S&P500, NASDAQ に RSI のみ
# PM用: 日経225 に全テクニカル指標
TECHNICAL_RSI_TARGETS = {"sp500", "nasdaq", "sox"}
TECHNICAL_FULL_TARGETS = {"nikkei225"}
# MACD対象: S&P500, NASDAQ, 日経225
TECHNICAL_MACD_TARGETS = {"sp500", "nasdaq", "nikkei225"}
# 一目均衡表対象: 日経225のみ
TECHNICAL_ICHIMOKU_TARGETS = {"nikkei225"}


def calc_sma(closes, period):
    """単純移動平均を算出"""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def calc_rsi(closes, period=14):
    """RSI(相対力指数)を Wilder's smoothing で算出"""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    # 最初のperiod分はSMA
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    # 以降はWilder's smoothing（指数平滑移動平均）
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def calc_bollinger(closes, period=20, num_std=2):
    """ボリンジャーバンドの位置を算出（-2σ〜+2σ）"""
    if len(closes) < period:
        return None
    window = closes[-period:]
    sma = sum(window) / period
    variance = sum((x - sma) ** 2 for x in window) / period
    std = variance ** 0.5
    if std == 0:
        return 0.0
    current = closes[-1]
    return round((current - sma) / std, 2)


def calc_volume_ratio(volumes, period=5):
    """出来高の5日平均対比を算出"""
    if len(volumes) < period + 1:
        return None
    avg = sum(volumes[-period - 1 : -1]) / period
    if avg == 0:
        return None
    return round(volumes[-1] / avg, 2)


def calc_ema_series(closes, period):
    """EMA（指数移動平均）系列を算出"""
    if len(closes) < period:
        return []
    multiplier = 2 / (period + 1)
    ema_val = sum(closes[:period]) / period
    result = [ema_val]
    for i in range(period, len(closes)):
        ema_val = (closes[i] - ema_val) * multiplier + ema_val
        result.append(ema_val)
    return result


def calc_macd(closes, fast=12, slow=26, signal_period=9):
    """MACD(12,26,9)を算出。ゴールデンクロス/デッドクロス検出付き"""
    if len(closes) < slow + signal_period:
        return None
    fast_ema = calc_ema_series(closes, fast)
    slow_ema = calc_ema_series(closes, slow)
    # MACD系列の算出（fast_emaとslow_emaのアライメント調整）
    offset = slow - fast
    macd_series = []
    for i in range(len(slow_ema)):
        macd_series.append(fast_ema[i + offset] - slow_ema[i])
    if len(macd_series) < signal_period:
        return None
    # シグナルライン = MACD系列のEMA(9)
    signal_ema = calc_ema_series(macd_series, signal_period)
    if not signal_ema:
        return None
    macd_val = macd_series[-1]
    signal_val = signal_ema[-1]
    histogram = macd_val - signal_val
    # クロス検出（直近1日）
    cross = "none"
    if len(macd_series) >= 2 and len(signal_ema) >= 2:
        prev_diff = macd_series[-2] - signal_ema[-2]
        curr_diff = macd_val - signal_val
        if prev_diff <= 0 and curr_diff > 0:
            cross = "golden_cross"
        elif prev_diff >= 0 and curr_diff < 0:
            cross = "dead_cross"
    return {
        "macd": round(macd_val, 2),
        "signal": round(signal_val, 2),
        "histogram": round(histogram, 2),
        "cross": cross,
    }


def calc_ichimoku(highs, lows, closes):
    """一目均衡表の5線分析（日経225用）"""
    if len(closes) < 52 or len(highs) < 52 or len(lows) < 52:
        return None
    tenkan = (max(highs[-9:]) + min(lows[-9:])) / 2
    kijun = (max(highs[-26:]) + min(lows[-26:])) / 2
    senkou_a = (tenkan + kijun) / 2
    senkou_b = (max(highs[-52:]) + min(lows[-52:])) / 2
    current = closes[-1]
    cloud_top = max(senkou_a, senkou_b)
    cloud_bottom = min(senkou_a, senkou_b)
    if current > cloud_top:
        position = "above_cloud"
    elif current < cloud_bottom:
        position = "below_cloud"
    else:
        position = "in_cloud"

    # 遅行スパン: 当日終値を26日前と比較
    chikou_span = closes[-1]
    chikou_reference = closes[-26] if len(closes) >= 26 else None

    # 三役好転/三役逆転の判定
    if chikou_reference is not None:
        tenkan_above_kijun = tenkan > kijun
        above_cloud = current > cloud_top
        chikou_above = chikou_span > chikou_reference

        if tenkan_above_kijun and above_cloud and chikou_above:
            three_signals = "bullish"  # 三役好転
        elif (not tenkan_above_kijun) and (current < cloud_bottom) and (not chikou_above):
            three_signals = "bearish"  # 三役逆転
        else:
            three_signals = "mixed"
    else:
        three_signals = "mixed"

    return {
        "tenkan": round(tenkan, 2),
        "kijun": round(kijun, 2),
        "cloud_top": round(cloud_top, 2),
        "cloud_bottom": round(cloud_bottom, 2),
        "cloud_position": position,
        "chikou_span": round(chikou_span, 2),
        "chikou_reference": round(chikou_reference, 2) if chikou_reference else None,
        "three_signals": three_signals,
    }


def calc_volume_analysis(closes, volumes, period=5):
    """出来高分析: トレンド判定 + 価格出来高ダイバージェンス検出"""
    if len(volumes) < period + 1 or len(closes) < period + 1:
        return None
    # 出来高比
    avg_vol = sum(volumes[-period - 1 : -1]) / period
    if avg_vol == 0:
        return None
    ratio = round(volumes[-1] / avg_vol, 2)
    # 出来高トレンド（直近3日の出来高が連続増加/減少か）
    if len(volumes) >= 4:
        recent = volumes[-3:]
        if recent[0] < recent[1] < recent[2]:
            trend = "increasing"
        elif recent[0] > recent[1] > recent[2]:
            trend = "decreasing"
        else:
            trend = "flat"
    else:
        trend = "flat"
    # 価格出来高ダイバージェンス
    price_change = closes[-1] - closes[-2]
    vol_change = volumes[-1] - volumes[-2]
    divergence = None
    if price_change > 0 and vol_change < 0:
        divergence = "bearish"  # 価格上昇+出来高減少=弱い上昇
    elif price_change < 0 and vol_change < 0:
        divergence = "bullish"  # 価格下落+出来高減少=弱い下落（反発期待）
    return {
        "ratio": ratio,
        "trend": trend,
        "divergence": divergence,
    }


def build_technical(name, closes, volumes, highs=None, lows=None):
    """ティッカー名に応じたテクニカル指標dictを構築する。

    対象外のティッカーはNoneを返す。
    エラー時は空dictを返す。
    """
    is_target = (
        name in TECHNICAL_RSI_TARGETS
        or name in TECHNICAL_FULL_TARGETS
        or name in TECHNICAL_MACD_TARGETS
        or name in TECHNICAL_ICHIMOKU_TARGETS
    )
    if not is_target:
        return None

    try:
        tech = {}
        # RSI は全対象共通
        rsi14 = calc_rsi(closes, 14)
        if rsi14 is not None:
            tech["rsi14"] = rsi14

        # フル指標は nikkei225 のみ
        if name in TECHNICAL_FULL_TARGETS:
            sma25 = calc_sma(closes, 25)
            sma75 = calc_sma(closes, 75)
            if sma25 is not None:
                tech["sma25"] = round(sma25, 2)
                tech["sma25_deviation"] = round(
                    (closes[-1] - sma25) / sma25 * 100, 2
                )
            if sma75 is not None:
                tech["sma75"] = round(sma75, 2)
                tech["sma75_deviation"] = round(
                    (closes[-1] - sma75) / sma75 * 100, 2
                )

            # SMA25×75クロス判定
            if sma25 is not None and sma75 is not None and len(closes) >= 76:
                prev_closes = closes[:-1]
                prev_sma25 = calc_sma(prev_closes, 25)
                prev_sma75 = calc_sma(prev_closes, 75)
                if prev_sma25 is not None and prev_sma75 is not None:
                    prev_spread = prev_sma25 - prev_sma75
                    curr_spread = sma25 - sma75
                    if prev_spread <= 0 and curr_spread > 0:
                        cross_type = "golden_cross"
                    elif prev_spread >= 0 and curr_spread < 0:
                        cross_type = "dead_cross"
                    else:
                        cross_type = "none"
                    tech["sma_cross"] = {
                        "type": cross_type,
                        "sma25": round(sma25, 2),
                        "sma75": round(sma75, 2),
                        "spread": round(curr_spread, 2),
                    }

            bb = calc_bollinger(closes, 20)
            if bb is not None:
                tech["bollinger_position"] = bb
            vr = calc_volume_ratio(volumes, 5)
            if vr is not None:
                tech["volume_ratio"] = vr

            # 出来高分析（volume_ratioの強化版）
            va = calc_volume_analysis(closes, volumes)
            if va is not None:
                tech["volume_analysis"] = va

            # 週足RSI（マルチタイムフレーム分析）
            if len(closes) >= 75:  # 最低75日（15週分）必要
                weekly_closes = [
                    closes[i] for i in range(4, len(closes), 5)
                ]  # 5営業日ごと
                weekly_rsi = calc_rsi(weekly_closes, 14)
                if weekly_rsi is not None:
                    tech["weekly_rsi14"] = weekly_rsi
                    # 日足RSIと週足RSIのダイバージェンス検出
                    if "rsi14" in tech:
                        daily_rsi = tech["rsi14"]
                        if (daily_rsi > 55 and weekly_rsi < 45) or (
                            daily_rsi < 45 and weekly_rsi > 55
                        ):
                            tech["timeframe_divergence"] = True
                        else:
                            tech["timeframe_divergence"] = False

        # MACD（S&P500, NASDAQ, 日経225）
        if name in TECHNICAL_MACD_TARGETS:
            macd = calc_macd(closes)
            if macd is not None:
                tech["macd"] = macd

        # 一目均衡表（日経225のみ）
        if name in TECHNICAL_ICHIMOKU_TARGETS and highs and lows:
            ichimoku = calc_ichimoku(highs, lows, closes)
            if ichimoku is not None:
                tech["ichimoku"] = ichimoku

        return tech
    except Exception:
        return {}


def fetch_market_data(include_pm=False):
    """ティッカーのデータを取得してJSON形式で返す。

    Args:
        include_pm: TrueならPM用東証指標も取得する
    """
    start_time = datetime.now(JST)
    tickers = dict(TICKERS)
    if include_pm:
        tickers.update(PM_TICKERS)

    result = {}
    errors = []
    hist_cache = {}  # ヒストリデータキャッシュ（volume_ratioフォールバック用）

    for name, ticker_symbol in tickers.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="6mo")

            if len(hist) == 0:
                errors.append(f"{name} ({ticker_symbol}): データなし")
                continue

            hist_cache[name] = hist

            latest = hist.iloc[-1]
            price = float(latest["Close"])

            # 前日比の計算
            if len(hist) >= 2:
                prev_close = float(hist.iloc[-2]["Close"])
                change_pct = ((price - prev_close) / prev_close) * 100
            else:
                prev_close = None
                change_pct = 0.0

            # 市場ステータス判定（簡易）
            # 最新データの日付が今日ならtrading の可能性、それ以外はclosed
            latest_date = hist.index[-1].date()
            today = datetime.now().date()
            status = "trading" if latest_date == today else "closed"

            entry = {
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "status": status,
            }

            # VIXのみポイント変動も追加
            if name == "vix" and prev_close is not None:
                entry["change"] = round(price - prev_close, 2)

            # テクニカル指標の算出
            closes = [float(row["Close"]) for _, row in hist.iterrows()]
            volumes = [float(row["Volume"]) for _, row in hist.iterrows()]
            highs = [float(row["High"]) for _, row in hist.iterrows()]
            lows = [float(row["Low"]) for _, row in hist.iterrows()]
            tech = build_technical(name, closes, volumes, highs, lows)
            if tech is not None:
                entry["technical"] = tech

            result[name] = entry

        except Exception as e:
            errors.append(f"{name} ({ticker_symbol}): {str(e)}")

    # nikkei225のvolume_ratio/volume_analysisフォールバック
    # ^N225のVolumeはyfinanceで常に0を返すため、1306.T（TOPIX連動ETF）で代替
    if (
        "nikkei225" in result
        and "technical" in result["nikkei225"]
        and "topix_etf" in hist_cache
    ):
        try:
            nk_tech = result["nikkei225"]["technical"]
            topix_hist = hist_cache["topix_etf"]
            topix_volumes = [
                float(row["Volume"]) for _, row in topix_hist.iterrows()
            ]
            topix_closes = [
                float(row["Close"]) for _, row in topix_hist.iterrows()
            ]
            # volume_ratioフォールバック
            if not nk_tech.get("volume_ratio"):
                fallback_vr = calc_volume_ratio(topix_volumes, 5)
                if fallback_vr is not None:
                    nk_tech["volume_ratio"] = fallback_vr
                    nk_tech["volume_ratio_source"] = "1306.T"
            # volume_analysisフォールバック（ratio=0.0はnikkei225のVolume=0が原因）
            va = nk_tech.get("volume_analysis")
            if not va or va.get("ratio") == 0.0:
                fallback_va = calc_volume_analysis(topix_closes, topix_volumes)
                if fallback_va is not None:
                    nk_tech["volume_analysis"] = fallback_va
                    nk_tech["volume_analysis_source"] = "1306.T"
        except Exception as e:
            errors.append(f"volume fallback (1306.T): {str(e)}")

    # イールドカーブスプレッド（10年-3ヶ月）
    if "us10y" in result and "us3m" in result:
        try:
            spread = result["us10y"]["price"] - result["us3m"]["price"]
            result["yield_curve"] = {
                "spread_10y3m": round(spread, 2),
                "status": "inverted" if spread < 0
                else "normal" if spread > 1.0
                else "flat",
            }
        except Exception:
            pass

    # テクニカルシグナル集計（方向一致度）
    bullish_signals = 0
    bearish_signals = 0
    signal_count = 0
    for ticker_name in ["sp500", "nasdaq", "nikkei225"]:
        if ticker_name in result and "technical" in result[ticker_name]:
            tech = result[ticker_name]["technical"]
            # RSI
            if "rsi14" in tech:
                signal_count += 1
                if tech["rsi14"] > 50:
                    bullish_signals += 1
                elif tech["rsi14"] < 50:
                    bearish_signals += 1
            # MACD
            if "macd" in tech:
                signal_count += 1
                if tech["macd"]["histogram"] > 0:
                    bullish_signals += 1
                elif tech["macd"]["histogram"] < 0:
                    bearish_signals += 1
    # 日経225固有
    if "nikkei225" in result and "technical" in result["nikkei225"]:
        nk_tech = result["nikkei225"]["technical"]
        if "bollinger_position" in nk_tech:
            signal_count += 1
            if nk_tech["bollinger_position"] > 0:
                bullish_signals += 1
            elif nk_tech["bollinger_position"] < 0:
                bearish_signals += 1
        # 一目均衡表: 三役好転/三役逆転で判定（常にthree_signalsが存在）
        if "ichimoku" in nk_tech:
            signal_count += 1
            if nk_tech["ichimoku"]["three_signals"] == "bullish":
                bullish_signals += 1
            elif nk_tech["ichimoku"]["three_signals"] == "bearish":
                bearish_signals += 1
        # SMAクロス
        if "sma_cross" in nk_tech:
            signal_count += 1
            if nk_tech["sma_cross"]["type"] == "golden_cross" or nk_tech["sma_cross"]["spread"] > 0:
                bullish_signals += 1
            elif nk_tech["sma_cross"]["type"] == "dead_cross" or nk_tech["sma_cross"]["spread"] < 0:
                bearish_signals += 1
        # 週足RSI
        if "weekly_rsi14" in nk_tech:
            signal_count += 1
            if nk_tech["weekly_rsi14"] > 50:
                bullish_signals += 1
            elif nk_tech["weekly_rsi14"] < 50:
                bearish_signals += 1
        # 出来高ダイバージェンス
        if "volume_analysis" in nk_tech and nk_tech["volume_analysis"].get("divergence"):
            signal_count += 1
            if nk_tech["volume_analysis"]["divergence"] == "bullish":
                bullish_signals += 1
            elif nk_tech["volume_analysis"]["divergence"] == "bearish":
                bearish_signals += 1
    if signal_count > 0:
        result["technical_summary"] = {
            "bullish": bullish_signals,
            "bearish": bearish_signals,
            "neutral": signal_count - bullish_signals - bearish_signals,
            "total": signal_count,
            "direction": "bullish" if bullish_signals > bearish_signals
            else "bearish" if bearish_signals > bullish_signals
            else "neutral",
        }

    # メタデータ
    end_time = datetime.now(JST)
    result["fetched_at"] = end_time.isoformat()
    result["fetch_duration_sec"] = round((end_time - start_time).total_seconds(), 1)
    result["ticker_count"] = len(tickers)
    result["errors"] = errors

    return result


def main():
    include_pm = "--pm" in sys.argv
    data = fetch_market_data(include_pm=include_pm)
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print()  # 末尾改行


if __name__ == "__main__":
    main()
