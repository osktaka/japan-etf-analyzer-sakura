#!/usr/bin/env python3
"""東証取引中（5分間隔）: 機械ルール発動を監視・通知.

batch_log は記録しない（軽量・高頻度）.
fingerprint で同日同銘柄同ルールの重複を抑止.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

from base_batch import BaseBatchScript  # noqa: E402

from _shared.advisor_runner import AdvisorRunner  # noqa: E402


class MechanicalRuleWatcherScript(BaseBatchScript):
    batch_name = "mechanical_rule_watcher"
    description = "Watch mechanical rules during market hours"
    enable_batch_log = False  # 軽量化（5分間隔 × 78回/日）

    def execute(self) -> int:
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
            return runner.run("alert")
        except Exception as e:
            self.logger.exception("Watcher failed: %s", e)
            return 1


if __name__ == "__main__":
    sys.exit(MechanicalRuleWatcherScript().run())
