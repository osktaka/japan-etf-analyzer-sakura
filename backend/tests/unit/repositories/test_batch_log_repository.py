"""Tests for BatchLogRepository."""
from datetime import datetime, timedelta, timezone

from src.models.batch_log import BatchLog
from src.repositories import BatchLogRepository


class TestBatchLogRepository:
    """Test cases for BatchLogRepository."""

    def _jst_today_start_utc(self) -> datetime:
        """JST今日0:00をUTC naive datetimeで返す."""
        jst = timezone(timedelta(hours=9))
        now_jst = datetime.now(jst)
        today_start_jst = now_jst.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return today_start_jst.astimezone(timezone.utc).replace(tzinfo=None)

    def test_has_succeeded_today_true(self, db_session):
        """今日成功レコードあり → has_succeeded_today = True."""
        repo = BatchLogRepository()
        today_utc = self._jst_today_start_utc() + timedelta(hours=1)

        log = BatchLog(
            batch_name="test_batch",
            status=BatchLog.STATUS_SUCCESS,
            started_at=today_utc,
        )
        db_session.add(log)
        db_session.commit()

        assert repo.has_succeeded_today("test_batch") is True

    def test_has_succeeded_today_false_no_record(self, db_session):
        """今日成功レコードなし → has_succeeded_today = False."""
        repo = BatchLogRepository()

        assert repo.has_succeeded_today("test_batch") is False

    def test_has_run_today_running(self, db_session):
        """今日running中 → has_run_today = True, has_succeeded_today = False."""
        repo = BatchLogRepository()
        today_utc = self._jst_today_start_utc() + timedelta(hours=1)

        log = BatchLog(
            batch_name="test_batch",
            status=BatchLog.STATUS_RUNNING,
            started_at=today_utc,
        )
        db_session.add(log)
        db_session.commit()

        assert repo.has_run_today("test_batch") is True
        assert repo.has_succeeded_today("test_batch") is False

    def test_has_succeeded_today_false_yesterday(self, db_session):
        """昨日の成功レコードのみ → has_succeeded_today = False."""
        repo = BatchLogRepository()
        yesterday_utc = self._jst_today_start_utc() - timedelta(hours=1)

        log = BatchLog(
            batch_name="test_batch",
            status=BatchLog.STATUS_SUCCESS,
            started_at=yesterday_utc,
        )
        db_session.add(log)
        db_session.commit()

        assert repo.has_succeeded_today("test_batch") is False

    # --- get_latest_success_time tests ---

    def test_get_latest_success_time_returns_finished_at(self, db_session):
        """今日成功ログあり → finished_at を返す."""
        repo = BatchLogRepository()
        today_utc = self._jst_today_start_utc() + timedelta(hours=1)
        finished = today_utc + timedelta(minutes=30)

        log = BatchLog(
            batch_name="test_batch",
            status=BatchLog.STATUS_SUCCESS,
            started_at=today_utc,
            finished_at=finished,
        )
        db_session.add(log)
        db_session.commit()

        result = repo.get_latest_success_time("test_batch")
        assert result == finished

    def test_get_latest_success_time_none_when_no_success(self, db_session):
        """今日成功ログなし → None を返す."""
        repo = BatchLogRepository()

        assert repo.get_latest_success_time("test_batch") is None

    def test_get_latest_success_time_excludes_yesterday(self, db_session):
        """前日の成功ログのみ → None を返す."""
        repo = BatchLogRepository()
        yesterday_utc = self._jst_today_start_utc() - timedelta(hours=1)
        finished = yesterday_utc + timedelta(minutes=30)

        log = BatchLog(
            batch_name="test_batch",
            status=BatchLog.STATUS_SUCCESS,
            started_at=yesterday_utc,
            finished_at=finished,
        )
        db_session.add(log)
        db_session.commit()

        assert repo.get_latest_success_time("test_batch") is None

    def test_get_latest_success_time_returns_latest(self, db_session):
        """複数の成功ログ → 最新の finished_at を返す."""
        repo = BatchLogRepository()
        today_utc = self._jst_today_start_utc() + timedelta(hours=1)

        # 1回目の成功
        log1 = BatchLog(
            batch_name="test_batch",
            status=BatchLog.STATUS_SUCCESS,
            started_at=today_utc,
            finished_at=today_utc + timedelta(minutes=30),
        )
        # 2回目の成功（より新しい）
        log2 = BatchLog(
            batch_name="test_batch",
            status=BatchLog.STATUS_SUCCESS,
            started_at=today_utc + timedelta(hours=2),
            finished_at=today_utc + timedelta(hours=2, minutes=30),
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        result = repo.get_latest_success_time("test_batch")
        assert result == today_utc + timedelta(hours=2, minutes=30)
