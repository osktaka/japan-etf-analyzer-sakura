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
    ) -> BatchLog:
        """
        Create a new batch log entry.

        Args:
            batch_name: Name of the batch job
            status: Initial status (e.g., 'running')
            started_at: When the batch started

        Returns:
            Created BatchLog instance
        """
        log = BatchLog(
            batch_name=batch_name,
            status=status,
            started_at=started_at,
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
