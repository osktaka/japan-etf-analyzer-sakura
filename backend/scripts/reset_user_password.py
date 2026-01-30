"""Reset user password to pbkdf2:sha256 hash method."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import create_app  # noqa: E402
from src.models import User  # noqa: E402
from src.models import db  # noqa: E402


def reset_password(email: str, new_password: str) -> bool:
    """
    Reset user password with pbkdf2:sha256 hash method.

    Args:
        email: User email address
        new_password: New password (plain text)

    Returns:
        True if password was reset successfully, False otherwise
    """
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"Error: User with email '{email}' not found")
        return False

    user.set_password(new_password)
    db.session.commit()
    print(f"Success: Password for user '{email}' has been reset")
    return True


def reset_all_users_password(default_password: str = "testpass123") -> int:
    """
    Reset all users' passwords to pbkdf2:sha256 hash method.

    Args:
        default_password: Default password to set for all users

    Returns:
        Number of users whose passwords were reset
    """
    users = User.query.all()
    count = 0

    for user in users:
        user.set_password(default_password)
        count += 1
        print(f"Reset password for: {user.email}")

    db.session.commit()
    return count


def main():
    """Run password reset script."""
    import argparse

    parser = argparse.ArgumentParser(description="Reset user passwords to pbkdf2:sha256")
    parser.add_argument(
        "--email",
        help="Email address of specific user to reset",
    )
    parser.add_argument(
        "--password",
        help="New password (required with --email)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reset all users to default password (testpass123)",
    )

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.all:
            print("Resetting all users' passwords to default...")
            count = reset_all_users_password()
            print(f"\nTotal: {count} users' passwords reset")
        elif args.email:
            if not args.password:
                print("Error: --password is required when using --email")
                sys.exit(1)
            reset_password(args.email, args.password)
        else:
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
