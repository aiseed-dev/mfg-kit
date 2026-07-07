"""メール送信の集約点(CLAUDE.md)。実体は localhost の Stalwart へ SMTP。

MAIL_BACKEND=console で標準出力に切替(dev・テスト)。
プレーンテキスト・日本語。テンプレートはこのファイルの関数。
"""

import smtplib
from email.message import EmailMessage
from typing import Any

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


def _sender_label(user: dict[str, Any]) -> str:
    company = user.get("company_name")
    return (
        f"{company} {user['display_name']}様"
        if company
        else f"{user['display_name']}様"
    )


def quote_requested(
    quote_no: str,
    customer: dict[str, Any],
    items: list[dict[str, Any]],
    note: str | None,
) -> None:
    """見積依頼の受付を会社へ通知(C-04)"""
    lines = [f"見積依頼 {quote_no} を受け付けました。", ""]
    lines += [f"依頼者: {_sender_label(customer)}", "", "品目:"]
    lines += [
        f"- {i['name']}({i['code']})× {i['quantity']}"
        + (f" / {i['spec_note']}" if i.get("spec_note") else "")
        for i in items
    ]
    if note:
        lines += ["", f"要望: {note}"]
    send(settings.company_mail_to, f"【見積依頼】{quote_no}", "\n".join(lines))


def message_received(quote_no: str, sender: dict[str, Any], body: str) -> None:
    """顧客からの新着メッセージを会社へ通知(送信時に即時)"""
    text = (
        f"見積 {quote_no} に {_sender_label(sender)}から"
        f"新しいメッセージが届きました。\n\n{body}"
    )
    send(settings.company_mail_to, f"【新着メッセージ】{quote_no}", text)
