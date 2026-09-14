#!/usr/bin/env python3
"""Send a security digest markdown file as an email via Gmail SMTP.

Usage: python send_digest_email.py <digest_md_path> [date_label]

Required env vars:
  GMAIL_USER          - sender Gmail address
  GMAIL_APP_PASSWORD  - Gmail App Password (not the account password)
Optional env vars:
  DIGEST_RECIPIENT     - recipient address (defaults to GMAIL_USER)
"""
import os
import smtplib
import sys
from email.header import Header
from email.mime.text import MIMEText


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: send_digest_email.py <digest_md_path> [date_label]", file=sys.stderr)
        return 2

    digest_path = sys.argv[1]
    date_label = sys.argv[2] if len(sys.argv) > 2 else ""

    sender = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not sender or not password:
        print("error: GMAIL_USER / GMAIL_APP_PASSWORD not set", file=sys.stderr)
        return 1

    recipient = os.environ.get("DIGEST_RECIPIENT", sender)

    with open(digest_path, encoding="utf-8") as f:
        body = f.read()

    subject = f"보안 뉴스 다이제스트 - {date_label}" if date_label else "보안 뉴스 다이제스트"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
    except smtplib.SMTPException as e:
        print(f"error: SMTP send failed: {e}", file=sys.stderr)
        return 1

    print(f"sent digest email to {recipient}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
