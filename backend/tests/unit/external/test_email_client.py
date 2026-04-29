"""Tests for EmailClient (smtplib mocked)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.external.email_client import EmailClient, EmailConfigError


@pytest.fixture
def client():
    return EmailClient(
        host="smtp.example.com",
        port=587,
        username="u@example.com",
        password="pw",
        sender="u@example.com",
        recipient="r@example.com",
        max_retries=3,
        backoff_base=1.0,
    )


class TestSend:
    def test_send_success_first_try(self, client):
        with patch("smtplib.SMTP") as smtp_cls:
            inst = MagicMock()
            smtp_cls.return_value.__enter__.return_value = inst
            ok = client.send("subj", "plain", "<html></html>")
            assert ok is True
            inst.starttls.assert_called_once()
            inst.login.assert_called_once_with("u@example.com", "pw")
            inst.send_message.assert_called_once()

    def test_send_retry_until_success(self, client):
        with patch("smtplib.SMTP") as smtp_cls, patch("time.sleep") as sleep_mock:
            inst = MagicMock()
            # 1回目は send_message で失敗、2回目で成功
            inst.send_message.side_effect = [Exception("flaky"), None]
            smtp_cls.return_value.__enter__.return_value = inst
            ok = client.send("s", "p")
            assert ok is True
            # リトライ間に sleep が呼ばれている
            assert sleep_mock.call_count == 1

    def test_send_all_retries_fail(self, client):
        with patch("smtplib.SMTP") as smtp_cls, patch("time.sleep"):
            inst = MagicMock()
            inst.send_message.side_effect = Exception("down")
            smtp_cls.return_value.__enter__.return_value = inst
            ok = client.send("s", "p")
            assert ok is False
            assert inst.send_message.call_count == 3

    def test_missing_config_returns_false(self):
        c = EmailClient(
            host="", port=587, username="", password="",
            sender="", recipient="",
        )
        assert c.send("s", "p") is False

    def test_html_attached_when_provided(self, client):
        with patch("smtplib.SMTP") as smtp_cls:
            inst = MagicMock()
            smtp_cls.return_value.__enter__.return_value = inst
            client.send("s", "plain text", "<b>html</b>")
            sent_msg = inst.send_message.call_args[0][0]
            payloads = sent_msg.get_payload()
            # MIMEMultipart → 2 parts (plain, html)
            assert len(payloads) == 2

    def test_subject_set(self, client):
        with patch("smtplib.SMTP") as smtp_cls:
            inst = MagicMock()
            smtp_cls.return_value.__enter__.return_value = inst
            client.send("Hello", "body")
            msg = inst.send_message.call_args[0][0]
            assert msg["Subject"] == "Hello"
            assert msg["From"] == "u@example.com"
            assert msg["To"] == "r@example.com"
