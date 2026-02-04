"""BatchLog repository for database operations."""
from datetime import datetime, timedelta
from typing import List, Optional

from src.models import db
from src.models.batch_log import BatchLog

from .base_repository import BaseRepository


class BatchLogRepository(BaseRepository[BatchLog]):
    """Repository for BatchLog entity."""

    model = BatchLog

    def create(
        self,
        batch_name: str,
        status: str,
        started_at: datetime,
        total_count: int = 0,
        parent_batch_log_id: Optional[int] = None,
        retry_count: int = 0,
    ) -> BatchLog:
        """
        Create a new batch log entry.

        Args:
            batch_name: Name of the batch job
            status: Initial status (e.g., 'running')
            started_at: When the batch started
            total_count: Total number of items to process
            parent_batch_log_id: ID of parent batch log (for retries)
            retry_count: Retry count (inherited from parent + 1)

        Returns:
            Created BatchLog instance
        """
        log = BatchLog(
            batch_name=batch_name,
            status=status,
            started_at=started_at,
            total_count=total_count,
            parent_batch_log_id=parent_batch_log_id,
            retry_count=retry_count,
            last_heartbeat=started_at,
        )
        db.session.add(log)
        db.session.commit()
        return log

    def update(self, log_id: int, **kwargs) -> Optional[BatchLog]:
        """
        Update a batch log entry.

        Args:
            log_id: ID of the log to update
            **kwargs: Fields to update (status, finished_at, error_message)

        Returns:
            Updated BatchLog instance or None if not found
        """
        log = self.get_by_id(log_id)
        if not log:
            return None

        for key, value in kwargs.items():
            if hasattr(log, key):
                setattr(log, key, value)

        db.session.commit()
        return log

    def get_all(self, limit: int = 100) -> List[BatchLog]:
        """
        Get all batch logs, ordered by newest first.

        Args:
            limit: Maximum number of logs to return (default: 100)

        Returns:
            List of BatchLog instances
        """
        return (
            db.session.query(BatchLog)
            .order_by(BatchLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def delete_old_logs(self, days: int = 90) -> int:
        """
        Delete logs older than specified days.

        Args:
            days: Number of days to retain logs (default: 90)

        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = (
            db.session.query(BatchLog)
            .filter(BatchLog.created_at < cutoff_date)
            .delete()
        )
        db.session.commit()
        return deleted_count

    def update_progress(
        self,
        log_id: int,
        processed_count: int,
        last_item_code: Optional[str] = None,
    ) -> Optional[BatchLog]:
        """
        Update batch progress and heartbeat.

        Args:
            log_id: ID of the log to update
            processed_count: Number of items processed so far
            last_item_code: Code of the last processed item

        Returns:
            Updated BatchLog instance or None if not found
        """
        log = self.get_by_id(log_id)
        if not log:
            return None

        log.processed_count = processed_count
        log.last_heartbeat = datetime.utcnow()
        if last_item_code:
            log.last_item_code = last_item_code

        db.session.commit()
        return log

    def get_retryable_jobs(self) -> List[BatchLog]:
        """
        Get failed jobs that are eligible for retry.

        Returns jobs that:
        - Status is 'failed'
        - Failed between 10-20 minutes ago
        - retry_count < 3

        Returns:
            List of BatchLog instances eligible for retry
        """
        now = datetime.utcnow()
        min_time = now - timedelta(minutes=20)
        max_time = now - timedelta(minutes=10)

        return (
            db.session.query(BatchLog)
            .filter(
                BatchLog.status == BatchLog.STATUS_FAILED,
                BatchLog.finished_at.between(min_time, max_time),
                BatchLog.retry_count < 3,
            )
            .all()
        )

    def get_timed_out_jobs(self) -> List[BatchLog]:
        """
        Get running jobs that have timed out (no heartbeat for 10+ minutes).

        Returns:
            List of BatchLog instances that have timed out
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=10)

        return (
            db.session.query(BatchLog)
            .filter(
                BatchLog.status == BatchLog.STATUS_RUNNING,
                db.or_(
                    BatchLog.last_heartbeat.is_(None),
                    BatchLog.last_heartbeat < cutoff_time,
                ),
            )
            .all()
        )

    def create_retry(self, parent_id: int) -> Optional[BatchLog]:
        """
        Create a retry batch log based on a failed parent job.

        Args:
            parent_id: ID of the parent batch log to retry

        Returns:
            Created BatchLog instance or None if parent not found
        """
        parent = self.get_by_id(parent_id)
        if not parent:
            return None

        retry_log = BatchLog(
            batch_name=parent.batch_name,
            status=BatchLog.STATUS_RUNNING,
            started_at=datetime.utcnow(),
            total_count=parent.total_count,
            parent_batch_log_id=parent_id,
            retry_count=parent.retry_count + 1,
            last_heartbeat=datetime.utcnow(),
        )
        db.session.add(retry_log)
        db.session.commit()
        return retry_log

    def has_running_job(self, batch_name: str) -> bool:
        """
        指定されたbatch_nameで実行中のジョブがあるかチェック.

        Args:
            batch_name: バッチ名

        Returns:
            実行中のジョブがある場合True
        """
        return (
            db.session.query(BatchLog)
            .filter(
                BatchLog.batch_name == batch_name,
                BatchLog.status == BatchLog.STATUS_RUNNING,
            )
            .first()
            is not None
        )
