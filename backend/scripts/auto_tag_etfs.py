"""自動タグ付けスクリプト.

全ETF銘柄に対してタグを自動付与する。
レバレッジ・インバース銘柄はスキップ。

使用方法:
    開発環境: docker compose exec backend python scripts/auto_tag_etfs.py
    本番環境: cd ~/www/japan-etf-analyzer && python backend/scripts/auto_tag_etfs.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import create_app  # noqa: E402
from src.models import db  # noqa: E402
from scripts.etf_tags_data import ETF_TAG_MAPPING  # noqa: E402


def should_skip(name: str) -> bool:
    """レバレッジ・インバース銘柄かどうかを判定.

    Args:
        name: ETF銘柄名

    Returns:
        スキップすべき場合True
    """
    # ブルームバーグ、ブルサは除外対象外
    if "ブルームバーグ" in name or "ブルサ" in name:
        return False

    skip_keywords = ["レバレッジ", "2倍", "ベア", "インバース", "ダブル", "ブル"]
    for kw in skip_keywords:
        if kw in name:
            return True
    return False


def get_all_etfs():
    """全ETF銘柄を取得."""
    result = db.session.execute(
        db.text("SELECT code, name, category_id FROM etfs ORDER BY code")
    )
    return result.fetchall()


def get_all_tags():
    """全タグを取得."""
    result = db.session.execute(db.text("SELECT id, name FROM tags ORDER BY id"))
    return {row[1]: row[0] for row in result.fetchall()}


def clear_tag_relations():
    """既存のタグ関連をクリア."""
    db.session.execute(db.text("DELETE FROM etf_tag_relations"))
    db.session.commit()
    print("  -> 既存のetf_tag_relationsをクリアしました")


def insert_tag_relations(relations: list):
    """タグ関連をバルク挿入.

    Args:
        relations: (etf_code, tag_id) のタプルリスト
    """
    if not relations:
        return 0

    # SQLiteのバルクインサート（created_atを含む）
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    values = ", ".join([f"('{code}', {tag_id}, '{now}')" for code, tag_id in relations])
    sql = (
        f"INSERT INTO etf_tag_relations (etf_code, tag_id, created_at) VALUES {values}"
    )
    db.session.execute(db.text(sql))
    db.session.commit()
    return len(relations)


def main():
    """メイン処理."""
    app = create_app()
    with app.app_context():
        print("=== ETF自動タグ付け開始 ===")

        # 全ETFを取得
        etfs = get_all_etfs()
        print(f"ETF総数: {len(etfs)}件")

        # DBのタグ名→IDマッピングを取得（念のため）
        db_tags = get_all_tags()
        print(f"タグ総数: {len(db_tags)}件")

        # タグマッピングデータの検証
        missing_tags = []
        for tags in ETF_TAG_MAPPING.values():
            for tag_name in tags:
                if tag_name not in db_tags:
                    missing_tags.append(tag_name)

        if missing_tags:
            print(f"警告: DBに存在しないタグ: {set(missing_tags)}")

        # 既存のタグ関連をクリア
        print("\n既存のタグ関連をクリア中...")
        clear_tag_relations()

        # タグ関連を作成
        print("\nタグ付け処理中...")
        relations = []
        tagged_count = 0
        skipped_count = 0
        no_mapping_count = 0
        no_mapping_codes = []

        for code, name, category_id in etfs:
            # レバレッジ・インバースはスキップ
            if should_skip(name):
                skipped_count += 1
                continue

            # マッピングデータからタグを取得
            tag_names = ETF_TAG_MAPPING.get(code)
            if not tag_names:
                no_mapping_count += 1
                no_mapping_codes.append(code)
                continue

            # タグ関連を追加
            for tag_name in tag_names:
                tag_id = db_tags.get(tag_name)
                if tag_id:
                    relations.append((code, tag_id))

            tagged_count += 1

        # バルクインサート
        inserted = insert_tag_relations(relations)

        # 結果表示
        print("\n=== 結果 ===")
        print(f"タグ付け完了: {tagged_count}件")
        print(f"スキップ（レバ/インバース）: {skipped_count}件")
        print(f"マッピングなし: {no_mapping_count}件")
        print(f"挿入されたタグ関連: {inserted}件")

        if no_mapping_codes:
            print("\n=== マッピングなし銘柄 ===")
            for code in no_mapping_codes[:20]:
                result = db.session.execute(
                    db.text("SELECT name FROM etfs WHERE code = :code"),
                    {"code": code},
                )
                row = result.fetchone()
                if row:
                    print(f"  {code}: {row[0]}")
            if len(no_mapping_codes) > 20:
                print(f"  ...他{len(no_mapping_codes) - 20}件")

        print("\n=== 完了 ===")


if __name__ == "__main__":
    main()
