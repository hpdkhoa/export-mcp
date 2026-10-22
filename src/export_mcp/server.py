"""Export MCP. Run: export-mcp serve (or export-mcp-server)."""
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from . import __version__, export as X

mcp = MCPServer("export", title="Export", version=__version__, instructions=(
    "Export turns a card statement PDF and payment emails into one Excel table with the statement's columns: "
    "Transaction date, Post date, Description, Amount (VND), Type (DR or CR; credits are negative). It keeps only "
    "the table rows. Emails come from .eml or .mbox files, or straight from Gmail through the read-only Gmail API. "
    "Each result lists the lines or emails it left out, so none is lost silently."))


def _err(f, *a, **k):
    try:
        return f(*a, **k)
    except (RuntimeError, ValueError, FileNotFoundError) as e:
        raise ToolError(str(e))


@mcp.tool()
def statement_to_excel(pdf_path: Annotated[str, Field(description="the statement PDF")],
                       out_path: Annotated[str | None, Field(description="the .xlsx to write; default: next to the PDF")] = None) -> dict:
    """The transaction table of a card statement PDF into Excel. Returns the rows and any dated line it could not read."""
    return _err(X.statement_to_excel, pdf_path, out_path)


@mcp.tool()
def emails_to_excel(paths: Annotated[list[str], Field(description=".eml files, .mbox files (Google Takeout) or folders of them")],
                    out_path: Annotated[str, Field(description="the .xlsx to write")]) -> dict:
    """Payment emails into Excel in the statement's columns, one row per payment, in date order."""
    return _err(X.emails_to_excel, paths, out_path)


@mcp.tool()
def gmail_to_excel(out_path: Annotated[str, Field(description="the .xlsx to write")],
                   query: Annotated[str | None, Field(description="a Gmail search; default: Shopee payment confirmations")] = None,
                   max_results: int = 500) -> dict:
    """Payment emails straight from Gmail (read-only) into Excel. Needs a one-time sign-in: export-mcp gmail-auth."""
    return _err(X.gmail_to_excel, out_path, query, max_results)


def main():
    mcp.run()
