"""Command line, for use without any AI client (by hand or from Task Scheduler)."""
import argparse
import json
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="export-mcp", description="Statement PDFs and payment emails into Excel.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("statement", help="a card statement PDF into Excel")
    s.add_argument("pdf")
    s.add_argument("--out")
    e = sub.add_parser("emails", help=".eml / .mbox files or folders into Excel")
    e.add_argument("paths", nargs="+")
    e.add_argument("--out", required=True)
    g = sub.add_parser("gmail", help="payment emails from Gmail into Excel")
    g.add_argument("--out", required=True)
    g.add_argument("--query")
    g.add_argument("--max", type=int, default=500)
    sub.add_parser("gmail-auth", help="one-time Google sign-in (opens the browser)")
    sub.add_parser("serve", help="run the MCP server on stdio")
    a = p.parse_args(argv)

    from . import export as X

    try:
        if a.cmd == "serve":
            from .server import main as serve
            return serve()
        if a.cmd == "gmail-auth":
            from .gmail import sign_in
            print(f"signed in; token saved at {sign_in()}")
            return 0
        if a.cmd == "statement":
            r = X.statement_to_excel(a.pdf, a.out)
        elif a.cmd == "emails":
            r = X.emails_to_excel(a.paths, a.out)
        else:
            r = X.gmail_to_excel(a.out, a.query, a.max, allow_browser=True)
    except (RuntimeError, ValueError, FileNotFoundError, PermissionError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    print(f"{r['rows']} rows -> {r['out']}")
    for key in ("unmatched_lines", "skipped"):
        if r.get(key):
            print(f"{key}: {json.dumps(r[key], ensure_ascii=False, indent=1)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
