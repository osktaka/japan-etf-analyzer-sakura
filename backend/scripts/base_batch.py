#!/usr/bin/env python3
"""Base class for batch scripts."""
import argparse
import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Load .env using python-dotenv
from dotenv import load_dotenv

# プロジェクトルートとパス設定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent

# .env読み込み
load_dotenv(PROJECT_ROOT / ".env")

# sys.path追加
sys.path.insert(0, str(BACKEND_DIR))

from src.app import create_app
from src.repositories import BatchLogRepository


class BaseBatchScript(ABC):
    """Base class for batch scripts with Flask app context management."""

    # サブクラスで設定
    batch_name: str = ""
    description: str = ""

    # 機能フラグ
    enable_batch_log: bool = True
    enable_progress: bool = False
    enable_resume: bool = False
    progress_interval: int = 10  # 何件ごとに進捗更新するか

    # 依存チェック
    depends_on: list = []          # 前提バッチ名リスト（AND条件）
    check_window: tuple = None     # ("16:30", "22:00") JST

    def __init__(self):
        self.logger = self._setup_logging()
        self.app = None
        self.ctx = None
        self.batch_log = None
        self.batch_log_repo = None
        self.args = None
        self.processed_count = 0

    def _setup_logging(self) -> logging.Logger:
        """ロギング設定"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return logging.getLogger(self.__class__.__name__)

    def _create_parser(self) -> argparse.ArgumentParser:
        """引数パーサー作成（サブクラスでオーバーライド可能）"""
        parser = argparse.ArgumentParser(description=self.description)

        # 共通オプション
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

        parser.add_argument(
            "--skip-dep-check",
            action="store_true",
            help="Skip dependency check (for direct execution)",
        )

        # resume機能有効時のみ追加
        if self.enable_resume:
            parser.add_argument(
                "--resume",
                type=int,
                help="Resume from failed batch log ID",
            )

        return parser

    def add_custom_arguments(self, parser: argparse.ArgumentParser) -> None:
        """サブクラスでカスタム引数を追加"""
        pass

    def _enter_context(self) -> None:
        """Flask app context開始"""
        os.environ["USE_MOCK_DATA"] = "false"
        self.app = create_app()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def _exit_context(self) -> None:
        """Flask app context終了"""
        if self.ctx:
            self.ctx.pop()

    def _check_dependencies(self) -> bool:
        """依存バッチの完了チェック.

        Returns:
            実行可能な場合True、スキップすべき場合False
        """
        # depends_onが空ならチェック不要
        if not self.depends_on:
            return True

        # --skip-dep-checkフラグあり
        if self.args.skip_dep_check:
            return True

        # --resumeフラグあり（リトライ時はスキップ）
        if self.enable_resume and getattr(self.args, "resume", None):
            return True

        # check_window指定あり → 現在時刻(JST)が範囲外ならスキップ
        if self.check_window:
            jst = timezone(timedelta(hours=9))
            now_jst = datetime.now(jst)
            start_str, end_str = self.check_window
            start_h, start_m = map(int, start_str.split(":"))
            end_h, end_m = map(int, end_str.split(":"))
            start_time = now_jst.replace(
                hour=start_h, minute=start_m, second=0, microsecond=0
            )
            end_time = now_jst.replace(
                hour=end_h, minute=end_m, second=0, microsecond=0
            )
            if not (start_time <= now_jst <= end_time):
                self.logger.info(
                    f"Outside check window {start_str}-{end_str} JST, skipping"
                )
                return False

        repo = BatchLogRepository()

        # 依存バッチが全て今日成功しているかチェック
        for dep_name in self.depends_on:
            if not repo.has_succeeded_today(dep_name):
                self.logger.info(
                    f"Dependency '{dep_name}' not completed today, skipping"
                )
                return False

        # 自バッチの今日の最新成功時刻を取得
        my_latest = repo.get_latest_success_time(self.batch_name)
        if my_latest is not None:
            # 依存バッチの最新成功時刻と比較
            # いずれかの依存が自バッチより新しければ実行（新データあり）
            has_newer_dep = False
            for dep_name in self.depends_on:
                dep_latest = repo.get_latest_success_time(dep_name)
                if dep_latest and dep_latest > my_latest:
                    has_newer_dep = True
                    break
            if not has_newer_dep:
                self.logger.info(
                    f"{self.batch_name} already processed latest dependency data, skipping"
                )
                return False

        return True

    def _start_batch_log(self, total_count: int = 0) -> None:
        """バッチログ開始"""
        if not self.enable_batch_log or self.args.dry_run:
            return

        self.batch_log_repo = BatchLogRepository()

        if self.enable_resume and self.args.resume:
            # リトライレコード作成
            self.batch_log = self.batch_log_repo.create_retry(self.args.resume)
            if not self.batch_log:
                raise ValueError(f"Parent batch log not found: id={self.args.resume}")
            self.logger.info(f"Resuming from batch log {self.args.resume}")
        else:
            # 新規バッチログ作成
            self.batch_log = self.batch_log_repo.create(
                batch_name=self.batch_name,
                status="running",
                started_at=datetime.utcnow(),
                total_count=total_count,
            )
            self.logger.info(f"Batch log created: id={self.batch_log.id}")

    def _finish_batch_log(self, success: bool, error_message: str = None) -> None:
        """バッチログ終了"""
        if not self.batch_log_repo or not self.batch_log:
            return

        status = "success" if success else "failed"
        self.batch_log_repo.update(
            self.batch_log.id,
            status=status,
            finished_at=datetime.utcnow(),
            error_message=error_message,
        )
        self.logger.info(f"Batch log updated: id={self.batch_log.id}, status={status}")

    def _update_progress(self, last_item_code: str = None) -> None:
        """進捗更新（progress_interval件ごと）"""
        self.processed_count += 1

        if not self.enable_progress or not self.batch_log_repo or not self.batch_log:
            return

        if self.args.dry_run:
            return

        if self.processed_count % self.progress_interval == 0:
            self.batch_log_repo.update_progress(
                self.batch_log.id,
                processed_count=self.processed_count,
                last_item_code=last_item_code,
            )
            self.logger.info(f"Progress updated: {self.processed_count} processed")

    def _final_progress_update(self, last_item_code: str = None) -> None:
        """最終進捗更新"""
        if not self.enable_progress or not self.batch_log_repo or not self.batch_log:
            return

        if self.args.dry_run:
            return

        self.batch_log_repo.update_progress(
            self.batch_log.id,
            processed_count=self.processed_count,
            last_item_code=last_item_code,
        )

    def get_resume_start_code(self) -> Optional[str]:
        """resume時の開始コードを取得"""
        if not self.enable_resume or not self.args.resume:
            return None

        parent = self.batch_log_repo.get_by_id(self.args.resume)
        return parent.last_item_code if parent else None

    @abstractmethod
    def execute(self) -> int:
        """メイン処理（サブクラスで実装）

        Returns:
            終了コード（0: 成功, 1: 失敗）
        """
        pass

    def run(self) -> int:
        """バッチ実行のエントリーポイント"""
        # 引数パース
        parser = self._create_parser()
        self.add_custom_arguments(parser)
        self.args = parser.parse_args()

        # 開始ログ
        self.logger.info("=" * 60)
        self.logger.info(f"{self.batch_name} Started at {datetime.now()}")
        if self.args.dry_run:
            self.logger.info("DRY RUN MODE - No changes will be made")
        self.logger.info("=" * 60)

        try:
            # Flask app context開始
            self._enter_context()

            # 依存チェック（depends_on設定時のみ）
            if self.depends_on:
                if not self._check_dependencies():
                    return 0  # スキップ（正常終了）

            # メイン処理実行
            exit_code = self.execute()

            return exit_code

        except Exception as e:
            self.logger.exception(f"Fatal error: {e}")
            self._finish_batch_log(success=False, error_message=str(e))
            return 1

        finally:
            # 終了ログ
            self.logger.info("=" * 60)
            self.logger.info(f"{self.batch_name} Completed at {datetime.now()}")
            self.logger.info("=" * 60)

            # Flask app context終了
            self._exit_context()


class SimpleBatchScript(BaseBatchScript):
    """バッチログなしのシンプルなバッチスクリプト（batch_monitor用）"""

    enable_batch_log = False
    enable_progress = False
    enable_resume = False
