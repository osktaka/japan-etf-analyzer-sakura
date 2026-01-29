#!/usr/bin/env python3
"""Add is_chart_applied column to stock_splits table.

Usage:
    python scripts/add_is_chart_applied_column.py
"""
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> int:
    """Add is_chart_applied column to stock_splits table."""
    os.environ["USE_MOCK_DATA"] = "false"
    from src.app import create_app
    from src.models import db

    app = create_app()
    with app.app_context():
        # Check if column already exists
        result = db.session.execute(
            db.text("PRAGMA table_info(stock_splits)")
        ).fetchall()

        column_names = [row[1] for row in result]
        if "is_chart_applied" in column_names:
            print("is_chart_applied column already exists")
            return 0

        # Add the column with default value False
        db.session.execute(
            db.text(
                "ALTER TABLE stock_splits ADD COLUMN is_chart_applied BOOLEAN DEFAULT 0"
            )
        )
        db.session.commit()
        print("Successfully added is_chart_applied column to stock_splits table")

        # Verify all existing records have is_chart_applied=False
        count = db.session.execute(
            db.text("SELECT COUNT(*) FROM stock_splits WHERE is_chart_applied = 1")
        ).scalar()
        print(f"Verified: {count} records have is_chart_applied=True (should be 0)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
