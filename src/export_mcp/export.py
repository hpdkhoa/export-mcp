"""The three exports, shared by the MCP server and the command line."""
from pathlib import Path

from . import emails, statement
from .excel import HEADERS, write_xlsx


def _report(rows, out, **extra):
    return {"rows": len(rows), "out": str(out), "columns": HEADERS, "table": rows, **extra}


def statement_to_excel(pdf, out=None):
    pdf = Path(pdf)
    rows, unmatched = statement.read_statement(pdf)
    if not rows:
        raise ValueError(f"no table rows found in {pdf}")
    out = write_xlsx(rows, out or pdf.with_suffix(".xlsx"))
    return _report(rows, out, unmatched_lines=unmatched)


def emails_to_excel(paths, out):
    rows, skipped = emails.parse_all(emails.messages_from_paths(paths))
    if not rows:
        raise ValueError(f"no payment emails read; skipped: {skipped}")
    return _report(rows, write_xlsx(rows, out), skipped=skipped)


def gmail_to_excel(out, query=None, max_results=500, allow_browser=False):
    from . import gmail

    rows, skipped = emails.parse_all(gmail.fetch(query or gmail.DEFAULT_QUERY, max_results, allow_browser))
    if not rows:
        raise ValueError(f"no payment emails found for the query; skipped: {skipped}")
    return _report(rows, write_xlsx(rows, out), skipped=skipped, query=query or gmail.DEFAULT_QUERY)
