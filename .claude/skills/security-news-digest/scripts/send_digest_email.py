#!/usr/bin/env python3
"""Send a security digest markdown file as an email via Gmail SMTP.

Renders the digest's markdown table(s) as an actual HTML table so the
email looks like a table in the recipient's client instead of raw
pipe characters. Falls back to a plain-text part for clients that
prefer it.

Usage: python send_digest_email.py <digest_md_path> [date_label]

Required env vars:
  GMAIL_USER          - sender Gmail address
  GMAIL_APP_PASSWORD  - Gmail App Password (not the account password)
Optional env vars:
  DIGEST_RECIPIENT     - recipient address (defaults to GMAIL_USER)
"""
import html
import os
import re
import smtplib
import sys
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def inline_html(text: str) -> str:
    text = html.escape(text)
    text = BOLD_RE.sub(r"<b>\1</b>", text)
    # bare URLs -> links
    text = re.sub(r"(https?://\S+)", r'<a href="\1">\1</a>', text)
    return text


def markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("# "):
            out.append(f"<h1>{inline_html(stripped[2:])}</h1>")
            i += 1
            continue
        if stripped.startswith("## "):
            out.append(f"<h2>{inline_html(stripped[3:])}</h2>")
            i += 1
            continue
        if stripped == "---":
            out.append("<hr>")
            i += 1
            continue
        if stripped.startswith(">"):
            out.append(f"<blockquote>{inline_html(stripped.lstrip('> ').strip())}</blockquote>")
            i += 1
            continue

        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            out.append(render_table(table_lines))
            continue

        out.append(f"<p>{inline_html(stripped)}</p>")
        i += 1

    return "\n".join(out)


def split_row(row: str):
    cells = row.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator_row(cells) -> bool:
    return all(re.fullmatch(r":?-+:?", c) for c in cells if c != "")


def render_table(table_lines) -> str:
    rows = [split_row(r) for r in table_lines]
    if len(rows) >= 2 and is_separator_row(rows[1]):
        header, body_rows = rows[0], rows[2:]
    else:
        header, body_rows = None, rows

    parts = ['<table style="border-collapse:collapse;width:100%;font-family:sans-serif;font-size:14px;">']
    if header:
        parts.append("<thead><tr>")
        for cell in header:
            parts.append(
                f'<th style="border:1px solid #ddd;padding:6px 8px;background:#f5f5f5;text-align:left;">{inline_html(cell)}</th>'
            )
        parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in body_rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f'<td style="border:1px solid #ddd;padding:6px 8px;vertical-align:top;">{inline_html(cell)}</td>')
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "\n".join(parts)


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
        plain_body = f.read()

    html_body = f"<html><body>{markdown_to_html(plain_body)}</body></html>"

    subject = f"보안 뉴스 다이제스트 - {date_label}" if date_label else "보안 뉴스 다이제스트"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

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
