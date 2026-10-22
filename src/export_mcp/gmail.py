"""Gmail through the official Gmail API, read-only.

Your own Google Cloud OAuth client (credentials.json) sits in the config folder. The first sign-in opens your
browser once and saves token.json next to it. Nothing goes through any other service.
Config folder: EXPORT_MCP_HOME, else ~/.export-mcp.
"""
import base64
import os
from pathlib import Path

from .emails import from_bytes

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_QUERY = 'from:info@mail.shopee.vn subject:"Xác nhận thanh toán thành công"'


def home():
    return Path(os.environ.get("EXPORT_MCP_HOME") or Path.home() / ".export-mcp")


def _paths():
    h = home()
    return h / "credentials.json", h / "token.json"


def _creds(allow_browser):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    cred_file, token_file = _paths()
    creds = Credentials.from_authorized_user_file(token_file, SCOPES) if token_file.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not allow_browser:
            raise RuntimeError("Gmail is not signed in yet. Run once in a terminal: export-mcp gmail-auth")
        if not cred_file.exists():
            raise FileNotFoundError(f"put your OAuth client file at {cred_file} (see README, Gmail setup)")
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = InstalledAppFlow.from_client_secrets_file(str(cred_file), SCOPES).run_local_server(port=0)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def sign_in():
    """Opens the browser for the one-time Google consent and saves the token."""
    _creds(allow_browser=True)
    return str(_paths()[1])


def fetch(query=DEFAULT_QUERY, max_results=500, allow_browser=False):
    """Yield (gmail id, message) for each email the Gmail search finds, newest first, up to max_results."""
    from googleapiclient.discovery import build

    svc = build("gmail", "v1", credentials=_creds(allow_browser), cache_discovery=False)
    ids, page = [], None
    while len(ids) < max_results:
        resp = svc.users().messages().list(userId="me", q=query, pageToken=page,
                                           maxResults=min(500, max_results - len(ids))).execute()
        ids += [m["id"] for m in resp.get("messages", [])]
        page = resp.get("nextPageToken")
        if not page:
            break
    for mid in ids:
        raw = svc.users().messages().get(userId="me", id=mid, format="raw").execute()["raw"]
        yield f"gmail:{mid}", from_bytes(base64.urlsafe_b64decode(raw))
