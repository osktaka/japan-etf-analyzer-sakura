#!/bin/bash
# マイグレーション実行スクリプト（本番環境用）
# 使用方法: ./migrate.sh
#
# 機能:
#   1. 新しいテーブル追加（db.create_all）
#   2. 既存テーブル変更（scripts/migrations/*.sql）
#
# マイグレーションファイルの命名規則:
#   scripts/migrations/001_create_xxx.sql
#   scripts/migrations/002_add_column_yyy.sql
#   番号順に実行され、実行済みはスキップされる

set -e  # エラー時は即座に終了

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Japan ETF Analyzer - Database Migration ===${NC}"
echo ""

# 1. 環境確認
echo -e "${YELLOW}[1/5] 環境確認中...${NC}"
PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
DB_PATH="${PROJECT_ROOT}/data/etf.db"
BACKUP_DIR="${PROJECT_ROOT}/data/backups"
MIGRATIONS_DIR="${PROJECT_ROOT}/scripts/migrations"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/etf.db.backup_${TIMESTAMP}"

if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}エラー: データベースファイルが見つかりません: ${DB_PATH}${NC}"
    exit 1
fi

echo "  プロジェクトルート: ${PROJECT_ROOT}"
echo "  データベース: ${DB_PATH}"
echo ""

# 2. バックアップ作成
echo -e "${YELLOW}[2/5] データベースをバックアップ中...${NC}"
mkdir -p "$BACKUP_DIR"
cp "$DB_PATH" "$BACKUP_PATH"
echo -e "${GREEN}✓ バックアップ完了: ${BACKUP_PATH}${NC}"
echo ""

# 3. マイグレーション履歴テーブル作成
echo -e "${YELLOW}[3/5] マイグレーション履歴テーブル確認...${NC}"
sqlite3 "$DB_PATH" "CREATE TABLE IF NOT EXISTS migrations_applied (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"
echo -e "${GREEN}✓ マイグレーション履歴テーブル準備完了${NC}"
echo ""

# 4. SQLマイグレーションファイル実行
echo -e "${YELLOW}[4/5] SQLマイグレーション実行中...${NC}"
MIGRATION_COUNT=0
SKIP_COUNT=0

if [ -d "$MIGRATIONS_DIR" ] && [ "$(ls -A $MIGRATIONS_DIR/*.sql 2>/dev/null)" ]; then
    for migration_file in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort); do
        migration_name=$(basename "$migration_file")

        # 既に適用済みかチェック
        applied=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM migrations_applied WHERE migration_name='${migration_name}';")

        if [ "$applied" -eq 0 ]; then
            echo -e "  ${BLUE}実行中: ${migration_name}${NC}"

            # SQLファイル実行
            if sqlite3 "$DB_PATH" < "$migration_file" 2>&1; then
                # 成功時は履歴に記録
                sqlite3 "$DB_PATH" "INSERT INTO migrations_applied (migration_name) VALUES ('${migration_name}');"
                echo -e "  ${GREEN}✓ 完了: ${migration_name}${NC}"
                MIGRATION_COUNT=$((MIGRATION_COUNT + 1))
            else
                echo -e "  ${RED}✗ 失敗: ${migration_name}${NC}"
                echo ""
                echo -e "${RED}マイグレーション失敗。バックアップから復元してください:${NC}"
                echo "  cp ${BACKUP_PATH} ${DB_PATH}"
                exit 1
            fi
        else
            echo -e "  ${GREEN}スキップ（適用済み）: ${migration_name}${NC}"
            SKIP_COUNT=$((SKIP_COUNT + 1))
        fi
    done
else
    echo "  マイグレーションファイルなし"
fi

echo ""
echo "  実行: ${MIGRATION_COUNT}件, スキップ: ${SKIP_COUNT}件"
echo ""

# 5. Flaskモデルからの自動マイグレーション（新規テーブル作成のみ）
echo -e "${YELLOW}[5/5] Flaskモデル同期中...${NC}"

# venv確認
if [ ! -d "${PROJECT_ROOT}/backend/venv" ]; then
    echo -e "${YELLOW}警告: 仮想環境が見つかりません。Flaskモデル同期をスキップします。${NC}"
else
    # 仮想環境をアクティベート
    source "${PROJECT_ROOT}/backend/venv/bin/activate"

    # 環境変数設定とマイグレーション実行
    export PYTHONPATH="${PROJECT_ROOT}/backend:${PYTHONPATH}"
    export APP_BASE_DIR="${PROJECT_ROOT}"
    export APP_DATA_DIR="${PROJECT_ROOT}/data"
    export FLASK_ENV=production

    python - << 'PYTHON_SCRIPT'
import sys
try:
    from backend.src.models import db
    from backend.src.app import create_app

    app = create_app('production')

    with app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        db.create_all()

        new_tables = set(inspector.get_table_names()) - existing_tables
        # migrations_applied は除外（このスクリプトで作成したため）
        new_tables.discard('migrations_applied')

        if new_tables:
            print(f"✓ 新しいテーブルを作成: {', '.join(new_tables)}")
        else:
            print("✓ Flaskモデル同期完了（変更なし）")

        sys.exit(0)

except Exception as e:
    print(f"警告: Flaskモデル同期スキップ - {e}")
    sys.exit(0)  # エラーでも続行（SQLマイグレーションが主）
PYTHON_SCRIPT

    # venv無効化
    deactivate
fi

# 6. 結果サマリー
echo ""
echo -e "${GREEN}=== マイグレーション完了 ===${NC}"
echo ""
echo "テーブル一覧:"
sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;" | while read table; do
    count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "N/A")
    printf "  %-25s %s records\n" "$table" "$count"
done

echo ""
echo "適用済みマイグレーション:"
sqlite3 "$DB_PATH" "SELECT '  ' || migration_name || ' (' || applied_at || ')' FROM migrations_applied ORDER BY id;"

echo ""
echo -e "${GREEN}バックアップ: ${BACKUP_PATH}${NC}"
echo ""
echo "問題があれば以下で復元:"
echo "  cp ${BACKUP_PATH} ${DB_PATH}"
