"""メール送信の集約点(CLAUDE.md)。実体は localhost の Stalwart へ SMTP。

MAIL_BACKEND=console で標準出力に切替(dev・テスト)。
業務テンプレート(依頼受付・新着メッセージ・expired)は Phase 2 で足す。
"""

import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send(to: str, subject: str, body: str) -> None:
    if settings.mail_backend == "console":
        print(f"--- mail to={to} subject={subject}\n{body}\n---")
        return
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
        if settings.smtp_user:
            s.starttls()
            s.login(settings.smtp_user, settings.smtp_pass)
        s.send_message(msg)
