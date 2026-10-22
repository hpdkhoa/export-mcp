"""The transaction table of a card statement PDF.

A table row is a line with two dates, a description and an amount, with CR after the amount for a credit
("247,328.00CR" or "247,328.00 CR"). Every other line (headers, card number, limits, balances) is left out.
"""
import re
from pathlib import Path

from .excel import row

ROW = re.compile(r"^(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+([\d,]+\.\d{2})(\s*CR)?\s*$")
DATED = re.compile(r"^\d{2}/\d{2}\s+\d{2}/\d{2}\s")


def parse_lines(lines):
    """Rows, plus the lines that start with two dates but do not read as a row (so none is lost silently)."""
    rows, unmatched = [], []
    for line in lines:
        line = line.strip()
        m = ROW.match(line)
        if m:
            tdate, pdate, desc, amount, cr = m.groups()
            rows.append(row(tdate, pdate, desc, float(amount.replace(",", "")), bool(cr)))
        elif DATED.match(line):
            unmatched.append(line)
    return rows, unmatched


def read_lines(path):
    import pdfplumber

    lines = []
    with pdfplumber.open(Path(path)) as pdf:
        for page in pdf.pages:
            lines.extend((page.extract_text() or "").splitlines())
    return lines


def read_statement(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no such PDF: {path}")
    return parse_lines(read_lines(path))
