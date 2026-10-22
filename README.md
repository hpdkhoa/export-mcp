# export-mcp

Card statement PDFs and payment emails into one Excel table. It works as an MCP server and as a command line.

Every export has the statement's columns:

| Transaction date | Post date | Description | Amount (VND) | Type |
|---|---|---|---|---|
| 21/09 | 22/09 | VNPAY*ILA 1039 HB P.PHU LAM VN | 18,105,500.00 | DR |
| 22/09 | 23/09 | CASHBACK CREDITED | -247,328.00 | CR |
| 20/10 | 20/10 | Shopee #2610204P78NHDA congchua.vn: ... \| #2610204P78NHDB dolakidhena: ... | 454,966.00 | DR |

Credits (CR) are negative, so the column adds up. Only table rows go in. Each run lists the lines or emails it
left out, so you can see that nothing is lost.

## Sources

| Source | How |
|---|---|
| Statement PDF | A row is a line with two dates, a description and an amount, with `CR` after a credit. Headers, card number, limits and balances stay out. |
| `.eml` files | Save an email from Gmail with "Download message". |
| `.mbox` files | Google Takeout export of a Gmail label. |
| Gmail | The official Gmail API with read-only access, with your own OAuth client. No other service sits in between. |

Emails: one email is one payment, so it gives one row. Today it reads Shopee "Xác nhận thanh toán thành công"
emails:

* Transaction date and Post date: the payment date (the email has no post date).
* Description: Shopee, then each order's id, shop and items.
* Amount: the amount paid.

It never reads the name, phone or address into the table. To add another merchant, add a module in
`src/export_mcp/parsers/` like `shopee.py`.

## Install

```bash
pip install git+https://github.com/hpdkhoa/export-mcp
```

## Command line

```bash
export-mcp statement statement.pdf
export-mcp emails mail/ takeout.mbox --out shopee.xlsx
export-mcp gmail --out shopee.xlsx --query "from:info@mail.shopee.vn after:2026/10/01"
```

Without `--query`, `gmail` finds every Shopee payment confirmation. The command line needs no AI client, so it can
run from Windows Task Scheduler.

## MCP

```json
{ "mcpServers": { "export": { "command": "python", "args": ["-m", "export_mcp", "serve"] } } }
```

With the pip Scripts folder on PATH, `"command": "export-mcp-server"` works too. For Claude Code:

```bash
claude mcp add export -- python -m export_mcp serve
```

Tools: `statement_to_excel`, `emails_to_excel`, `gmail_to_excel`.

## Gmail setup (one time)

1. Open https://console.cloud.google.com and create a project.
2. APIs and Services, Library: enable the **Gmail API**.
3. OAuth consent screen: user type External, add your Gmail address as a test user.
4. Credentials, Create credentials, OAuth client ID, type **Desktop app**. Download the JSON.
5. Save it as `~/.export-mcp/credentials.json` (`C:\Users\<you>\.export-mcp\credentials.json`).
   Set `EXPORT_MCP_HOME` to use another folder.
6. Run `export-mcp gmail-auth`. Your browser opens once. Approve read-only access.
   The token goes to `token.json` in the same folder.

The scope is `gmail.readonly`, so the tool cannot send, change or delete mail. You can remove its access at any
time at https://myaccount.google.com/permissions. Keep `credentials.json` and `token.json` private.

## Google Takeout

1. Open https://takeout.google.com, deselect all, select Mail.
2. Pick the label that holds the payment emails (a Gmail filter on `from:info@mail.shopee.vn` can label them).
3. Export, download, unzip, then run `export-mcp emails <the .mbox> --out shopee.xlsx`.

## License

MIT
