"""Repository for MechanicalRuleEvent."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from src.models import db
from src.models.mechanical_rule_event import MechanicalRuleEvent

from .base_repository import BaseRepository


class MechanicalRuleEventRepository(BaseRepository[MechanicalRuleEvent]):
    """機械ルールイベントの永続化."""

    model = MechanicalRuleEvent

    def get_by_fingerprint(self, fingerprint: str) -> Optional[MechanicalRuleEvent]:
        return (
            db.session.query(MechanicalRuleEvent)
            .filter(MechanicalRuleEvent.fingerprint == fingerprint)
            .first()
        )

    def exists_for_today(self, fingerprint: str) -> bool:
        """送信済み(notified=True)の同 fingerprint イベントが存在するか.

        通知失敗（notified=False）のレコードは未送信扱いとし、
        次回 watcher 実行時に再送できるよう False を返す.
        """
        ev = self.get_by_fingerprint(fingerprint)
        return ev is not None and bool(ev.notified)

    def create_event(
        self,
        fingerprint: str,
        occurred_on: date,
        rule_kind: str,
        user_id: str,
        etf_code: Optional[str] = None,
        severity: str = "info",
        payload_json: Optional[str] = None,
    ) -> MechanicalRuleEvent:
        event = MechanicalRuleEvent(
            fingerprint=fingerprint,
            occurred_on=occurred_on,
            rule_kind=rule_kind,
            etf_code=etf_code,
            user_id=user_id,
            severity=severity,
            payload_json=payload_json,
            notified=False,
        )
        db.session.add(event)
        db.session.commit()
        return event

    def mark_notified(self, event_id: int) -> Optional[MechanicalRuleEvent]:
        event = self.get_by_id(event_id)
        if not event:
            return None
        event.notified = True
        event.notified_at = datetime.utcnow()
        db.session.commit()
        return event

    def get_recent(
        self, user_id: str, since_days: int = 7
    ) -> List[MechanicalRuleEvent]:
        """直近N日のイベントを取得."""
        cutoff = date.today() - timedelta(days=since_days)
        return (
            db.session.query(MechanicalRuleEvent)
            .filter(
                MechanicalRuleEvent.user_id == user_id,
                MechanicalRuleEvent.occurred_on >= cutoff,
            )
            .order_by(MechanicalRuleEvent.occurred_on.desc())
            .all()
        )
