"""米国市場データのクイック取得スクリプト（market-outlookスキル用）

yfinanceを使用して米国主要指標をJSON形式で標準出力に出力する。
DB接続は不要。
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

# 取得対象ティッカー
TICKERS = {
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow": "^DJI",
    "vix": "^VIX",
    "us10y": "^TNX",
    "nikkei_futures": "NKD=F",
    "usdjpy": "USDJPY=X",
}

JST = timezone(timedelta(hours=9))


def fetch_market_data():
    """全ティッカーのデータを取得してJSON形式で返す。"""
    result = {}
    errors = []

    for name, ticker_symbol in TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")

            if len(hist) == 0:
                errors.append(f"{name} ({ticker_symbol}): データなし")
                continue

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

            result[name] = entry

        except Exception as e:
            errors.append(f"{name} ({ticker_symbol}): {str(e)}")

    # メタデータ
    result["fetched_at"] = datetime.now(JST).isoformat()
    result["errors"] = errors

    return result


def main():
    data = fetch_market_data()
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print()  # 末尾改行


if __name__ == "__main__":
    main()
