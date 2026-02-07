"""BatchLog model for tracking batch job executions."""

from . import db
from .base import TimestampMixin


class BatchLog(db.Model, TimestampMixin):
    """Model for storing batch job execution logs."""

    __tablename__ = "batch_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_name = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    # Progress tracking columns
    last_heartbeat = db.Column(db.DateTime, nullable=True)
    total_count = db.Column(db.Integer, default=0)
    processed_count = db.Column(db.Integer, default=0)
    last_item_code = db.Column(db.String(20), nullable=True)

    # Retry tracking columns
    parent_batch_log_id = db.Column(
        db.Integer, db.ForeignKey("batch_logs.id"), nullable=True
    )
    retry_count = db.Column(db.Integer, default=0)

    # Status constants
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "batch_name": self.batch_name,
            "status": self.status,
            "started_at": (
                self.started_at.isoformat() + "Z" if self.started_at else None
            ),
            "finished_at": (
                self.finished_at.isoformat() + "Z" if self.finished_at else None
            ),
            "error_message": self.error_message,
            "created_at": (
                self.created_at.isoformat() + "Z" if self.created_at else None
            ),
            "last_heartbeat": (
                self.last_heartbeat.isoformat() + "Z" if self.last_heartbeat else None
            ),
            "total_count": self.total_count,
            "processed_count": self.processed_count,
            "last_item_code": self.last_item_code,
            "parent_batch_log_id": self.parent_batch_log_id,
            "retry_count": self.retry_count,
        }

    def __repr__(self) -> str:
        return f"<BatchLog {self.batch_name} - {self.status}>"
