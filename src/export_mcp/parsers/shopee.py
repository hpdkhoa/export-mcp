"""Shopee "Xác nhận thanh toán thành công" (payment confirmed) emails.

One email is one card payment, so it gives one row (owner's choice):
  Transaction date = Ngày thanh toán (payment date), as dd/mm like the statement
  Post date        = the payment date too (the email has none; owner's choice)
  Description      = Shopee, then each order: its id, its shop and its items
  Amount           = Số tiền thanh toán (amount paid), a debit
Name, phone and address in the email are never read into the row.
"""
import re
import unicodedata

from ..excel import row

PAID_DATE = re.compile(r"(\d{1,2})\s*Th\s*(\d{1,2})\s*(\d{4})(?:\s+(\d{1,2}:\d{2}:\d{2}))?")
ITEM = re.compile(r"^\d+\.\s+(.+)$")


def matches(sender, lines):
    return "shopee.vn" in sender.lower() and any(ln.startswith("Số tiền thanh toán") for ln in lines)


def _clean(s):
    # Shopee writes some item names in mathematical bold letters; NFKC turns them back into plain letters.
    s = unicodedata.normalize("NFC", unicodedata.normalize("NFKC", s))
    s = re.sub(r"\[\s*(.*?)\s*\]", r"[\1]", s)
    return re.sub(r"\s+", " ", s).strip()


def _value(lines, i):
    """The value of label line i: after its colon, or the next line when the label stands alone."""
    rest = lines[i].split(":", 1)[1].strip() if ":" in lines[i] else ""
    return rest or (lines[i + 1] if i + 1 < len(lines) else "")


def _amount(s):
    digits = re.sub(r"\D", "", s)
    if not digits:
        raise ValueError(f"no amount in {s!r}")
    return float(digits)


def parse(lines):
    orders, paid, amount = [], None, None
    in_items = False
    for i, ln in enumerate(lines):
        if ln.startswith("Mã đơn hàng"):
            orders.append({"id": _value(lines, i).lstrip("#"), "shop": "", "items": []})
            in_items = False
        elif ln.startswith("Người bán") and orders:
            orders[-1]["shop"] = _value(lines, i)
            in_items = True
        elif ln.startswith("THÔNG TIN NHẬN HÀNG"):
            in_items = False
        elif in_items and ITEM.match(ln):
            orders[-1]["items"].append(_clean(ITEM.match(ln).group(1)))
        elif ln.startswith("Ngày thanh toán"):
            paid = PAID_DATE.search(_value(lines, i))
        elif ln.startswith("Số tiền thanh toán"):
            amount = _amount(_value(lines, i))
    if not paid or amount is None:
        raise ValueError("Shopee email without a payment date or amount")
    d, m, y, t = paid.groups()
    date = f"{int(d):02d}/{int(m):02d}"
    parts = [f"#{o['id']} {o['shop']}: {', '.join(o['items'])}".strip() for o in orders]
    desc = "Shopee " + " | ".join(parts) if parts else "Shopee"
    return {"row": row(date, date, desc, amount), "when": f"{y}-{int(m):02d}-{int(d):02d} {t or ''}"}
