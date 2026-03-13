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
TECHNICAL_RSI_TARGETS = {"sp500", "nasdaq"}
TECHNICAL_FULL_TARGETS = {"nikkei225"}


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


def build_technical(name, closes, volumes):
    """ティッカー名に応じたテクニカル指標dictを構築する。

    対象外のティッカーはNoneを返す。
    エラー時は空dictを返す。
    """
    if name not in TECHNICAL_RSI_TARGETS and name not in TECHNICAL_FULL_TARGETS:
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
            bb = calc_bollinger(closes, 20)
            if bb is not None:
                tech["bollinger_position"] = bb
            vr = calc_volume_ratio(volumes, 5)
            if vr is not None:
                tech["volume_ratio"] = vr

        return tech
    except Exception:
        return {}


def fetch_market_data(include_pm=False):
    """ティッカーのデータを取得してJSON形式で返す。

    Args:
        include_pm: TrueならPM用東証指標も取得する
    """
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
            tech = build_technical(name, closes, volumes)
            if tech is not None:
                entry["technical"] = tech

            result[name] = entry

        except Exception as e:
            errors.append(f"{name} ({ticker_symbol}): {str(e)}")

    # nikkei225のvolume_ratioフォールバック
    # ^N225のVolumeはyfinanceで常に0を返すため、1306.T（TOPIX連動ETF）で代替
    if (
        "nikkei225" in result
        and "technical" in result["nikkei225"]
        and not result["nikkei225"]["technical"].get("volume_ratio")
        and "topix_etf" in hist_cache
    ):
        try:
            topix_hist = hist_cache["topix_etf"]
            topix_volumes = [
                float(row["Volume"]) for _, row in topix_hist.iterrows()
            ]
            fallback_vr = calc_volume_ratio(topix_volumes, 5)
            if fallback_vr is not None:
                result["nikkei225"]["technical"]["volume_ratio"] = fallback_vr
                result["nikkei225"]["technical"][
                    "volume_ratio_source"
                ] = "1306.T"
        except Exception as e:
            errors.append(f"volume_ratio fallback (1306.T): {str(e)}")

    # メタデータ
    result["fetched_at"] = datetime.now(JST).isoformat()
    result["errors"] = errors

    return result


def main():
    include_pm = "--pm" in sys.argv
    data = fetch_market_data(include_pm=include_pm)
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print()  # 末尾改行


if __name__ == "__main__":
    main()
