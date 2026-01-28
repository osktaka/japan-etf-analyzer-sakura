"""Create or update admin user script."""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import create_app  # noqa: E402
from src.models import User, db  # noqa: E402
from src.repositories.user_repository import UserRepository  # noqa: E402

ADMIN_EMAIL = "admin@example.com"
ADMIN_USERNAME = "admin"


def get_password(args: argparse.Namespace) -> Optional[str]:
    """Get password from args or environment variable."""
    if args.password:
        return args.password
    return os.environ.get("ADMIN_PASSWORD")


def create_admin(password: str) -> Tuple[bool, str]:
    """Create or update admin user.

    Returns:
        tuple: (created, message) - created is True if new user, False if updated
    """
    user_repo = UserRepository()
    existing_user = user_repo.get_by_email(ADMIN_EMAIL)

    if existing_user:
        # 既存ユーザーの場合は is_admin を True に更新（パスワードは更新しない）
        if not existing_user.is_admin:
            existing_user.is_admin = True
            db.session.commit()
            return False, f"Updated existing user '{ADMIN_EMAIL}' to admin role"
        return False, f"User '{ADMIN_EMAIL}' is already an admin"

    # 新規ユーザー作成
    admin_user = User(
        email=ADMIN_EMAIL,
        username=ADMIN_USERNAME,
        password_hash="",  # 一時的な値
        is_admin=True,
        is_active=True,
    )
    admin_user.set_password(password)
    user_repo.create(admin_user)

    return True, f"Created admin user '{ADMIN_EMAIL}'"


def main():
    """Run create admin script."""
    parser = argparse.ArgumentParser(description="Create or update admin user")
    parser.add_argument(
        "--password",
        "-p",
        type=str,
        help="Admin password (can also use ADMIN_PASSWORD env var)",
    )
    args = parser.parse_args()

    password = get_password(args)
    if not password:
        print("Error: Password is required.")
        print(
            "  Use --password or -p option, or set ADMIN_PASSWORD environment variable."
        )
        sys.exit(1)

    app = create_app()
    with app.app_context():
        created, message = create_admin(password)
        print(message)

        if created:
            print("Admin user created successfully!")
        else:
            print("Note: Password was not updated for security reasons.")


if __name__ == "__main__":
    main()
