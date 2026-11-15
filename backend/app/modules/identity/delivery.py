"""Optional private SMTP transport for H-05 one-use setup and invitation tokens.

No tokens in URLs, database, application logs or API responses. Fail closed when
SMTP TLS credentials are absent. Operator and identity router can both use this.
"""
from __future__ import annotations

from collections.abc import Callable
from email.message import EmailMessage
import os
import smtplib
import ssl


def smtp_delivery_from_env() -> Callable[[str, str], None] | None:
    host = os.environ.get("HESABYAR_SMTP_HOST", "")
    user = os.environ.get("HESABYAR_SMTP_USER", "")
    password = os.environ.get("HESABYAR_SMTP_PASSWORD", "")
    sender = os.environ.get("HESABYAR_SMTP_FROM", "")
    if not all((host, user, password, sender)):
        return None
    try:
        port = int(os.environ.get("HESABYAR_SMTP_PORT", "465"))
    except ValueError as exc:
        raise ValueError("Invalid private SMTP port") from exc
    if not 1 <= port <= 65535:
        raise ValueError("Invalid private SMTP port")

    def deliver(email: str, token: str) -> None:
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = email
        msg["Subject"] = "Hesabyar - private account activation token"
        msg.set_content(
            "Use the following confidential one-use token in the approved "
            "Hesabyar activation form. Do not put the token in a URL.\n\n"
            f"{token}\n\nIf you did not expect this message, contact your operator."
        )
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=10) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    return deliver
