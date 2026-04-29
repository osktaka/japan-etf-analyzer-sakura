#!/usr/bin/env python3
"""毎日の朝7時通知（平日）: 当日のアクション + 前日終値ベース要約."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# プロジェクトルート特定
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 環境変数
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from base_batch import BaseBatchScript  # noqa: E402

from _shared.advisor_runner import AdvisorRunner  # noqa: E402


class DailyAdvisorMorningScript(BaseBatchScript):
    batch_name = "daily_advisor_morning"
    description = "Daily advisor morning notification"

    def execute(self) -> int:
        self._start_batch_log()
        try:
            user_id = os.environ.get("ADVISOR_USER_ID", "test")
            strategy_file = Path(
                os.environ.get(
                    "STRATEGY_FILE",
                    str(PROJECT_ROOT / "docs" / "12_personal_strategy.md"),
                )
            )
            reports_dir = Path(
                os.environ.get(
                    "ADVISOR_REPORTS_DIR",
                    str(PROJECT_ROOT / "reports" / "test" / "daily-tasks"),
                )
            )
            runner = AdvisorRunner(
                project_root=PROJECT_ROOT,
                strategy_file=strategy_file,
                reports_dir=reports_dir,
                user_id_str=user_id,
                dry_run=self.args.dry_run,
            )
            rc = runner.run("morning")
            self._finish_batch_log(success=(rc == 0))
            return rc
        except Exception as e:
            self._finish_batch_log(success=False, error_message=str(e))
            raise


if __name__ == "__main__":
    sys.exit(DailyAdvisorMorningScript().run())
