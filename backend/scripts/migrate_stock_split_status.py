"""Migrate stock_splits table from status (string) to is_applied (boolean)."""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def migrate_stock_split_status(db_path: str = "/app/data/etf.db"):
    """Migrate stock_splits table schema.

    Changes:
    - Drop status column (string: pending/approved/rejected)
    - Add is_applied column (boolean: true/false)
    - Migrate data: approved -> true, others -> false
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Create backup table
        print("Creating backup table...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_splits_backup AS
            SELECT * FROM stock_splits
            """
        )
        backup_count = cursor.execute(
            "SELECT COUNT(*) FROM stock_splits_backup"
        ).fetchone()[0]
        print(f"Backup created: {backup_count} records")

        # 2. Create new table with is_applied column
        print("Creating new table with is_applied column...")
        cursor.execute(
            """
            CREATE TABLE stock_splits_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                etf_code VARCHAR(10) NOT NULL,
                split_date DATE NOT NULL,
                ratio FLOAT NOT NULL,
                is_applied BOOLEAN NOT NULL DEFAULT 0,
                detected_at DATETIME NOT NULL,
                reviewed_at DATETIME,
                reviewed_by INTEGER,
                previous_close FLOAT,
                current_close FLOAT,
                change_percent FLOAT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(etf_code, split_date)
            )
            """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX ix_stock_splits_new_etf_code ON stock_splits_new (etf_code)"
        )
        cursor.execute(
            "CREATE INDEX ix_stock_splits_new_split_date ON stock_splits_new (split_date)"
        )
        cursor.execute(
            "CREATE INDEX ix_stock_splits_new_is_applied ON stock_splits_new (is_applied)"
        )

        # 3. Migrate data (approved -> true, others -> false)
        print("Migrating data...")
        cursor.execute(
            """
            INSERT INTO stock_splits_new (
                id, etf_code, split_date, ratio, is_applied,
                detected_at, reviewed_at, reviewed_by,
                previous_close, current_close, change_percent,
                created_at, updated_at
            )
            SELECT
                id, etf_code, split_date, ratio,
                CASE WHEN status = 'approved' THEN 1 ELSE 0 END,
                detected_at, reviewed_at, reviewed_by,
                previous_close, current_close, change_percent,
                created_at, updated_at
            FROM stock_splits
            """
        )
        migrated_count = cursor.execute(
            "SELECT COUNT(*) FROM stock_splits_new"
        ).fetchone()[0]
        print(f"Migrated: {migrated_count} records")

        # Show migration summary
        approved_count = cursor.execute(
            "SELECT COUNT(*) FROM stock_splits WHERE status = 'approved'"
        ).fetchone()[0]
        applied_count = cursor.execute(
            "SELECT COUNT(*) FROM stock_splits_new WHERE is_applied = 1"
        ).fetchone()[0]
        print(f"Approved records: {approved_count} -> Applied records: {applied_count}")

        # 4. Drop old table and rename new table
        print("Replacing old table with new table...")
        cursor.execute("DROP TABLE stock_splits")
        cursor.execute("ALTER TABLE stock_splits_new RENAME TO stock_splits")

        # 5. Commit changes
        conn.commit()
        print("Migration completed successfully!")
        print(f"Backup table 'stock_splits_backup' is available for rollback if needed.")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        print("Rolling back changes...")
        # Try to restore from backup if new table was created
        try:
            cursor.execute("DROP TABLE IF EXISTS stock_splits_new")
            conn.commit()
            print("Cleanup completed. Original table is intact.")
        except Exception as cleanup_error:
            print(f"Cleanup error: {cleanup_error}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/app/data/etf.db"
    print(f"Starting migration for database: {db_path}")
    print(f"Time: {datetime.now().isoformat()}")
    print("-" * 60)
    migrate_stock_split_status(db_path)
