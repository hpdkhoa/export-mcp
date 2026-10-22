"""Made-up data only: no real names, phones or addresses in the repo."""
import base64
import mailbox
from email.message import EmailMessage

import openpyxl
import pytest

from export_mcp import emails, export, gmail
from export_mcp.excel import HEADERS
from export_mcp.statement import parse_lines

STATEMENT = """Ngày giao dịch
Transaction date
4378 4100 xxxx 0000 TEST HOLDER
Your Credit Limit: VND100,000,000
ACCOUNT BALANCE AS IN LAST STATEMENT 1,000,000.00
21/09 22/09 VNPAY*SHOP A HCM VN 18,105,500.00
20/09 23/09 PLX_SAI GON_CH51 HCM VN 65,116.00
22/09 23/09 CASHBACK CREDITED 247,328.00CR
22/09 23/09 REFUND SHOP B 1,000.00 CR
STATEMENT BALANCE 18,924,288.00""".splitlines()

SHOPEE_HTML = """<html><head><style>p{}</style></head><body>
<p>Xin chào test,</p>
<table><tr><td>Mã đơn hàng:</td><td>#AAA111</td></tr>
<tr><td>Ngày đặt hàng:</td><td>20 Th10 2026 09:08:25</td></tr>
<tr><td>Người bán:</td><td>shop.one</td></tr>
<tr><td>1.&nbsp; [ 𝗛𝗮̀𝗻𝗴 𝗰𝗮𝗼 𝗰𝗮̂́𝗽 ] Váy test</td></tr>
<tr><td>Giá:</td><td>₫480,000</td></tr>
<tr><td>2.&nbsp; Cài tóc test</td></tr>
<tr><td>Tổng thanh toán:</td><td>₫364,000</td></tr>
<tr><td>Mã đơn hàng:</td><td>#BBB222</td></tr>
<tr><td>Người bán:</td><td>shop.two</td></tr>
<tr><td>1.&nbsp; Bodysuit test</td></tr>
<tr><td>Tổng thanh toán:</td><td>₫90,966</td></tr></table>
<p>THÔNG TIN NHẬN HÀNG</p><p>Tên người nhận:</p><p>SECRET NAME</p><p>Số điện thoại:</p><p>84900000000</p>
<p>THÔNG TIN THANH TOÁN</p><p>Ngày thanh toán:</p><p>{day} Th 10 2026 09:08:30</p>
<p>Số tiền thanh toán:</p><p>₫{amount}</p></body></html>"""


def shopee_email(day="20", amount="454,966"):
    m = EmailMessage()
    m["From"] = "Shopee <info@mail.shopee.vn>"
    m["Subject"] = "Xác nhận thanh toán thành công"
    m.set_content(SHOPEE_HTML.replace("{day}", day).replace("{amount}", amount), subtype="html")
    return m


def table(path):
    return list(openpyxl.load_workbook(path).active.iter_rows(values_only=True))


def test_statement_keeps_only_rows_and_reads_cr_with_or_without_space():
    rows, unmatched = parse_lines(STATEMENT)
    assert [r[2] for r in rows] == ["VNPAY*SHOP A HCM VN", "PLX_SAI GON_CH51 HCM VN", "CASHBACK CREDITED", "REFUND SHOP B"]
    assert [r[3] for r in rows] == [18105500.0, 65116.0, -247328.0, -1000.0]
    assert [r[4] for r in rows] == ["DR", "DR", "CR", "CR"]
    assert unmatched == []


def test_statement_lists_dated_lines_it_cannot_read():
    _, unmatched = parse_lines(["21/09 22/09 SHOP WITH NO AMOUNT"])
    assert unmatched == ["21/09 22/09 SHOP WITH NO AMOUNT"]


def test_shopee_email_is_one_row_per_payment():
    parsed, why = emails.parse_message(shopee_email())
    assert why is None
    tdate, pdate, desc, amount, kind = parsed["row"]
    assert (tdate, pdate, amount, kind) == ("20/10", "20/10", 454966.0, "DR")
    assert desc == ("Shopee #AAA111 shop.one: [Hàng cao cấp] Váy test, Cài tóc test"
                    " | #BBB222 shop.two: Bodysuit test")
    assert "SECRET" not in desc and "849" not in desc


def test_unknown_email_is_skipped_with_a_reason(tmp_path):
    other = EmailMessage()
    other["From"] = "news@example.com"
    other["Subject"] = "Hello"
    other.set_content("nothing to see")
    (tmp_path / "a.eml").write_bytes(bytes(shopee_email()))
    (tmp_path / "b.eml").write_bytes(bytes(other))
    r = export.emails_to_excel([tmp_path], tmp_path / "out.xlsx")
    assert r["rows"] == 1
    assert r["skipped"][0]["subject"] == "Hello"
    assert table(tmp_path / "out.xlsx")[0] == tuple(HEADERS)


def test_mbox_rows_come_in_date_order(tmp_path):
    box = mailbox.mbox(tmp_path / "takeout.mbox")
    box.add(shopee_email("21", "100,000"))
    box.add(shopee_email("05", "200,000"))
    box.flush()
    r = export.emails_to_excel([tmp_path / "takeout.mbox"], tmp_path / "out.xlsx")
    assert [row[0] for row in r["table"]] == ["05/10", "21/10"]
    assert [row[3] for row in table(tmp_path / "out.xlsx")[1:]] == [200000, 100000]


def test_gmail_decodes_raw_messages(monkeypatch):
    raw = base64.urlsafe_b64encode(bytes(shopee_email())).decode()

    class Call:
        def __init__(self, value):
            self.value = value

        def execute(self):
            return self.value

    class Messages:
        def list(self, **kw):
            assert kw["q"] == gmail.DEFAULT_QUERY
            return Call({"messages": [{"id": "m1"}]})

        def get(self, **kw):
            assert kw["format"] == "raw"
            return Call({"raw": raw})

    class Service:
        def users(self):
            return self

        def messages(self):
            return Messages()

    monkeypatch.setattr(gmail, "_creds", lambda allow_browser: None)
    monkeypatch.setattr("googleapiclient.discovery.build", lambda *a, **k: Service())
    rows, skipped = emails.parse_all(gmail.fetch())
    assert skipped == [] and rows[0][3] == 454966.0


def test_gmail_without_sign_in_says_how(monkeypatch, tmp_path):
    monkeypatch.setenv("EXPORT_MCP_HOME", str(tmp_path))
    with pytest.raises(RuntimeError, match="gmail-auth"):
        gmail._creds(allow_browser=False)
