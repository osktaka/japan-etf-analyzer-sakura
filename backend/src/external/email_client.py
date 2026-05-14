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
        # 引数が None の場合のみ環境変数フォールバック。
        # 空文字列("")が渡された場合は明示的に「未設定」を意図しているため、
        # 環境変数を参照せずそのまま空文字列として扱う。
        self.host = host if host is not None else os.environ.get("SMTP_HOST", "")
        self.port = int(
            port if port is not None else os.environ.get("SMTP_PORT", "587")
        )
        self.username = (
            username if username is not None else os.environ.get("SMTP_USER", "")
        )
        self.password = (
            password if password is not None
            else os.environ.get("SMTP_PASSWORD", "")
        )
        if sender is not None:
            self.sender = sender
        else:
            self.sender = os.environ.get("SMTP_SENDER") or self.username
        self.recipient = (
            recipient if recipient is not None
            else os.environ.get("NOTIFY_TO_EMAIL", "")
        )
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
