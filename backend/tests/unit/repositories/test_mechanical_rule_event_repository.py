"""Tests for MechanicalRuleEventRepository."""
from __future__ import annotations

from datetime import date

from src.repositories import MechanicalRuleEventRepository


class TestExistsForToday:
    """exists_for_today の重複判定: notified=True のみ重複扱い."""

    def test_no_event_returns_false(self, db_session):
        repo = MechanicalRuleEventRepository()
        assert repo.exists_for_today("nonexistent-fp") is False

    def test_unnotified_event_returns_false(self, db_session):
        """notified=False は未送信扱い → 重複ではない（再送可）."""
        repo = MechanicalRuleEventRepository()
        ev = repo.create_event(
            fingerprint="fp-unsent",
            occurred_on=date(2026, 4, 29),
            rule_kind="loss_cut",
            user_id="test",
            etf_code="1306",
            severity="critical",
        )
        assert ev.notified is False
        # 未送信は重複扱いしない
        assert repo.exists_for_today("fp-unsent") is False

    def test_notified_event_returns_true(self, db_session):
        """notified=True は送信済み → 重複扱い."""
        repo = MechanicalRuleEventRepository()
        ev = repo.create_event(
            fingerprint="fp-sent",
            occurred_on=date(2026, 4, 29),
            rule_kind="loss_cut",
            user_id="test",
            etf_code="1306",
            severity="critical",
        )
        repo.mark_notified(ev.id)
        assert repo.exists_for_today("fp-sent") is True


class TestMarkNotified:
    def test_mark_notified_sets_flags(self, db_session):
        repo = MechanicalRuleEventRepository()
        ev = repo.create_event(
            fingerprint="fp-mark",
            occurred_on=date(2026, 4, 29),
            rule_kind="loss_cut",
            user_id="test",
            etf_code="2559",
            severity="info",
        )
        result = repo.mark_notified(ev.id)
        assert result is not None
        assert result.notified is True
        assert result.notified_at is not None

    def test_mark_notified_nonexistent_returns_none(self, db_session):
        repo = MechanicalRuleEventRepository()
        assert repo.mark_notified(99999) is None
