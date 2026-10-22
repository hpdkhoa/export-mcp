"""Payment emails as table rows, from .eml files, .mbox files (Google Takeout) or raw Gmail messages."""
import email
import html
import mailbox
import re
from email import policy
from pathlib import Path

from .parsers import PARSERS


def from_bytes(data):
    return email.message_from_bytes(data, policy=policy.default)


def body_text(msg):
    """The email body as plain text lines: the HTML part with tags removed, or the plain part."""
    part = msg.get_body(("html", "plain"))
    if part is None:
        return []
    text = part.get_content()
    if part.get_content_type() == "text/html":
        text = re.sub(r"(?is)<(style|script|head).*?</\1>", "", text)
        text = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|td|th|li|h\d|table)>", "\n", text)
        text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return [ln.strip() for ln in text.replace("\xa0", " ").splitlines() if ln.strip()]


def parse_message(msg):
    """(row, None) when a parser knows the email, else (None, why)."""
    sender = str(msg.get("From", ""))
    lines = body_text(msg)
    for parser in PARSERS:
        if parser.matches(sender, lines):
            return parser.parse(lines), None
    return None, "no parser for this sender or layout"


def messages_from_paths(paths):
    """Yield (source, message) for each .eml, each message of each .mbox, and both inside folders."""
    for p in map(Path, paths):
        if p.is_dir():
            yield from messages_from_paths(sorted(x for x in p.rglob("*") if x.suffix.lower() in (".eml", ".mbox")))
        elif not p.is_file():
            raise FileNotFoundError(f"no such file or folder: {p}")
        elif p.suffix.lower() == ".mbox":
            for i, m in enumerate(mailbox.mbox(p, factory=None)):
                yield f"{p}#{i}", from_bytes(m.as_bytes())
        else:
            yield str(p), from_bytes(p.read_bytes())


def parse_all(sourced_messages):
    """Rows in date order, plus the emails left out and why."""
    found, skipped = [], []
    for source, msg in sourced_messages:
        try:
            parsed, why = parse_message(msg)
        except ValueError as e:
            parsed, why = None, str(e)
        if parsed:
            found.append(parsed)
        else:
            skipped.append({"source": source, "subject": str(msg.get("Subject", "")), "why": why})
    found.sort(key=lambda p: p["when"])
    return [p["row"] for p in found], skipped
