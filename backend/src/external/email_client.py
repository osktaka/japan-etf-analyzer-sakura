"""SMTP Email Client: STARTTLS + retries."""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class EmailConfigError(Exception):
    """環境変数不足など."""


class EmailClient:
    """smtplib をラップしたメール送信クライアント."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ):
        self.host = host or os.environ.get("SMTP_HOST", "")
        self.port = int(port or os.environ.get("SMTP_PORT", "587"))
        self.username = username or os.environ.get("SMTP_USER", "")
        self.password = password or os.environ.get("SMTP_PASSWORD", "")
        self.sender = (
            sender or os.environ.get("SMTP_SENDER") or self.username
        )
        self.recipient = recipient or os.environ.get("NOTIFY_TO_EMAIL", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    def _validate(self) -> None:
        missing = [
            name
            for name, val in (
                ("SMTP_HOST", self.host),
                ("SMTP_USER", self.username),
                ("SMTP_PASSWORD", self.password),
                ("NOTIFY_TO_EMAIL", self.recipient),
            )
            if not val
        ]
        if missing:
            raise EmailConfigError(
                f"Email config missing: {missing}"
            )

    def send(
        self,
        subject: str,
        plain_body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """メール送信. 成功 True / 失敗 False."""
        try:
            self._validate()
        except EmailConfigError as e:
            logger.error("Email config error: %s", e)
            return False

        msg = self._build_message(subject, plain_body, html_body)
        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self._send_once(msg)
                logger.info(
                    "Email sent: subject=%r attempt=%d", subject, attempt
                )
                return True
            except Exception as e:  # noqa: BLE001
                last_err = e
                logger.warning(
                    "Email send failed (attempt %d/%d): %s",
                    attempt, self.max_retries, e,
                )
                if attempt < self.max_retries:
                    sleep_s = self.backoff_base ** (attempt - 1)
                    time.sleep(sleep_s)
        logger.error(
            "Email send permanently failed: subject=%r last_err=%s",
            subject, last_err,
        )
        return False

    def _build_message(
        self, subject: str, plain_body: str, html_body: Optional[str]
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))
        return msg

    def _send_once(self, msg: MIMEMultipart) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(self.username, self.password)
            server.send_message(msg)
