"""X API 接続確認スクリプト - 3つの認証方式をテスト"""
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import requests
import tweepy


def test_bearer_token():
    """Bearer Token (App-Only) でGETテスト"""
    token = os.environ.get("X_BEARER_TOKEN", "")
    if not token:
        return "SKIP", "X_BEARER_TOKEN 未設定"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get("https://api.twitter.com/2/users/by/username/X", headers=headers)
    if r.status_code == 200:
        return "OK", f"Bearer認証成功 (status={r.status_code})"
    return "NG", f"status={r.status_code} body={r.text[:200]}"


def test_oauth1_get_me():
    """OAuth 1.0a で GET /2/users/me テスト"""
    client = tweepy.Client(
        consumer_key=os.environ.get("X_API_KEY", ""),
        consumer_secret=os.environ.get("X_API_SECRET", ""),
        access_token=os.environ.get("X_ACCESS_TOKEN", ""),
        access_token_secret=os.environ.get("X_ACCESS_SECRET", ""),
    )
    try:
        me = client.get_me()
        if me and me.data:
            return "OK", f"@{me.data.username} (id={me.data.id})"
        return "NG", "ユーザー情報を取得できませんでした"
    except tweepy.Unauthorized:
        return "NG", "401 Unauthorized (トークン無効または失効)"
    except tweepy.Forbidden as e:
        return "WARN", f"403 Forbidden (権限不足) {e}"


def test_oauth1_search():
    """OAuth 1.0a で検索APIの読み取り権限テスト"""
    client = tweepy.Client(
        consumer_key=os.environ.get("X_API_KEY", ""),
        consumer_secret=os.environ.get("X_API_SECRET", ""),
        access_token=os.environ.get("X_ACCESS_TOKEN", ""),
        access_token_secret=os.environ.get("X_ACCESS_SECRET", ""),
    )
    try:
        result = client.search_recent_tweets(query="test", max_results=10)
        return "OK", "OAuth1.0a READ権限あり"
    except tweepy.Unauthorized:
        return "NG", "401 Unauthorized"
    except tweepy.Forbidden as e:
        return "WARN", f"403 Forbidden (権限不足またはプラン制限) {e}"


if __name__ == "__main__":
    print("=" * 60)
    print("X API 接続確認")
    print("=" * 60)

    keys = {
        "X_API_KEY": os.environ.get("X_API_KEY", ""),
        "X_API_SECRET": os.environ.get("X_API_SECRET", ""),
        "X_ACCESS_TOKEN": os.environ.get("X_ACCESS_TOKEN", ""),
        "X_ACCESS_SECRET": os.environ.get("X_ACCESS_SECRET", ""),
        "X_BEARER_TOKEN": os.environ.get("X_BEARER_TOKEN", ""),
    }
    print("\n[環境変数]")
    for k, v in keys.items():
        if v:
            print(f"  {k}: 設定済み (長さ={len(v)}, 先頭={v[:8]}...)")
        else:
            print(f"  {k}: 未設定")

    tests = [
        ("1. Bearer Token (App-Only GET)", test_bearer_token),
        ("2. OAuth 1.0a GET /2/users/me", test_oauth1_get_me),
        ("3. OAuth 1.0a 検索API (READ)", test_oauth1_search),
    ]

    print()
    for name, func in tests:
        try:
            status, msg = func()
        except Exception as e:
            status, msg = "ERR", str(e)
        mark = {"OK": "✅", "NG": "❌", "SKIP": "⏭️", "WARN": "⚠️", "ERR": "💥"}.get(status, "?")
        print(f"{mark} {name}: [{status}] {msg}")

    print("\n" + "=" * 60)
