"""etfsテーブルのmomentum_labelのみを再計算・更新するスクリプト.

performance_cacheの既存値を使い、株価の再取得や履歴テーブルへの書き込みは行わない。
"""
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
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

from src.app import create_app  # noqa: E402
from src.models import db  # noqa: E402
from src.models.etf import ETF  # noqa: E402
from src.models.performance_cache import PerformanceCache  # noqa: E402
from src.utils.momentum import get_momentum_label  # noqa: E402


def main():
    dry_run = "--dry-run" in sys.argv
    app = create_app()

    with app.app_context():
        etfs = ETF.query.all()
        updated = 0
        changes = []

        for etf in etfs:
            cache_1m = PerformanceCache.query.filter_by(
                etf_code=etf.code, period="1m"
            ).first()
            cache_3m = PerformanceCache.query.filter_by(
                etf_code=etf.code, period="3m"
            ).first()

            rate_1m = cache_1m.regression_rate if cache_1m else None
            rate_3m = cache_3m.regression_rate if cache_3m else None

            label = get_momentum_label(rate_1m, rate_3m)

            if etf.momentum_label != label:
                changes.append(
                    f"  {etf.code}: {etf.momentum_label} -> {label}"
                )
                if not dry_run:
                    etf.momentum_label = label
                updated += 1

        if not dry_run:
            db.session.commit()

        mode = "[DRY-RUN] " if dry_run else ""
        print(f"{mode}モメンタムラベル更新: {updated}/{len(etfs)}件")
        for line in changes:
            print(line)


if __name__ == "__main__":
    main()
