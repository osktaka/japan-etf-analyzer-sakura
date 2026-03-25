"""X (Twitter) API v2 投稿スクリプト."""
import argparse
import json
import os
import sys
from pathlib import Path

# プロジェクトルートを特定（backend/scripts/ → backend/ → project root）
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 環境変数設定（本番環境用）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))

# .envファイル読み込み（dotenvがなくても動作するように）
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                os.environ.setdefault(key, value)


def get_client():
    """tweepy Client を取得する."""
    try:
        import tweepy
    except ImportError:
        print(
            json.dumps(
                {"success": False, "error": "tweepy not installed. Run: pip install tweepy"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    api_key = os.environ.get("X_API_KEY")
    api_secret = os.environ.get("X_API_SECRET")
    access_token = os.environ.get("X_ACCESS_TOKEN")
    access_secret = os.environ.get("X_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        missing = []
        for name in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]:
            if not os.environ.get(name):
                missing.append(name)
        print(
            json.dumps(
                {"success": False, "error": f"Missing env vars: {', '.join(missing)}"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )


def post_tweet(text, dry_run=False, client=None):
    """ツイートを投稿する."""
    if dry_run:
        result = {"success": True, "dry_run": True, "text": text, "length": len(text)}
        print(json.dumps(result, ensure_ascii=False))
        return

    if client is None:
        client = get_client()
    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        result = {
            "success": True,
            "tweet_id": tweet_id,
            "url": f"https://x.com/ETF_Analyzer/status/{tweet_id}",
        }
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


def parse_posts_file(file_path):
    """tmp_x_posts_v2.md から投稿を抽出する."""
    path = Path(file_path)
    if not path.exists():
        print(
            json.dumps(
                {"success": False, "error": f"File not found: {file_path}"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    posts = []
    sections = content.split("## 投稿")

    for section in sections[1:]:  # 最初の空セクションをスキップ
        lines = section.strip().split("\n")
        # 最初の行は "N" のような番号行
        post_lines = []
        for line in lines[1:]:  # 番号行をスキップ
            if line.strip() == "---":
                break
            post_lines.append(line)
        post_text = "\n".join(post_lines).strip()
        if post_text:
            posts.append(post_text)

    return posts


def main():
    """メイン処理."""
    parser = argparse.ArgumentParser(description="X (Twitter) API v2 投稿")
    parser.add_argument("--text", help="投稿テキスト")
    parser.add_argument("--file", help="投稿ファイル（tmp_x_posts_v2.md形式）")
    parser.add_argument("--dry-run", action="store_true", help="実投稿せずプレビュー")
    args = parser.parse_args()

    if args.text:
        post_tweet(args.text, dry_run=args.dry_run)
    elif args.file:
        posts = parse_posts_file(args.file)
        if not args.dry_run:
            client = get_client()
        results = []
        for i, post in enumerate(posts, 1):
            print(f"--- Post {i}/{len(posts)} ---", file=sys.stderr)
            post_tweet(post, dry_run=args.dry_run, client=client)
            results.append({"post_number": i, "text_preview": post[:50]})
        print(
            json.dumps({"success": True, "total": len(results), "posts": results}, ensure_ascii=False),
            file=sys.stderr,
        )
    else:
        parser.error("--text or --file is required")


if __name__ == "__main__":
    main()
