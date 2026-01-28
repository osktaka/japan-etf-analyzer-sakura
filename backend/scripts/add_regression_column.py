#!/usr/bin/env python3
"""Add regression_rate column to performance_cache table.

Usage:
    python scripts/add_regression_column.py
"""
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> int:
    """Add regression_rate column to performance_cache table."""
    os.environ["USE_MOCK_DATA"] = "false"
    from src.app import create_app
    from src.models import db

    app = create_app()
    with app.app_context():
        # Check if column already exists
        result = db.session.execute(
            db.text("PRAGMA table_info(performance_cache)")
        ).fetchall()

        column_names = [row[1] for row in result]
        if "regression_rate" in column_names:
            print("regression_rate column already exists")
            return 0

        # Add the column
        db.session.execute(
            db.text("ALTER TABLE performance_cache ADD COLUMN regression_rate FLOAT")
        )
        db.session.commit()
        print("Successfully added regression_rate column to performance_cache table")

    return 0


if __name__ == "__main__":
    sys.exit(main())
