"""Fetch questions from a Google Sheet (or a CSV file) stored in Google Drive.

Two ways to connect:

* "link"   - the sheet is shared as "Anyone with the link: Viewer". No login,
             no setup. The app downloads the sheet as CSV.
* "google" - sign in with your Google account (OAuth, read-only). Works for
             private sheets. Needs a `credentials.json` OAuth client file in the
             data folder (see README).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from . import paths
from .storage import Question, parse_csv_text

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TIMEOUT = 20


class SyncError(Exception):
    """Readable error shown to the user."""


@dataclass
class SheetRef:
    file_id: str
    gid: str | None
    is_sheet: bool


def parse_link(link: str) -> SheetRef:
    """Accept a Google Sheets link, a Drive file link, or a bare file id."""
    link = (link or "").strip()
    if not link:
        raise SyncError("Paste the link of your Google Sheet in Settings first.")

    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", link):
        return SheetRef(link, None, True)

    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    fragment = parse_qs(parsed.fragment)
    gid = (query.get("gid") or fragment.get("gid") or [None])[0]

    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        return SheetRef(match.group(1), gid, True)
    match = re.search(r"/file/d/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        return SheetRef(match.group(1), None, False)
    if "id" in query:
        return SheetRef(query["id"][0], None, False)
    raise SyncError("This does not look like a Google Sheets or Google Drive link.")


def sheet_url(ref: SheetRef) -> str:
    if ref.is_sheet:
        tail = f"#gid={ref.gid}" if ref.gid else ""
        return f"https://docs.google.com/spreadsheets/d/{ref.file_id}/edit{tail}"
    return f"https://drive.google.com/file/d/{ref.file_id}/view"


def _export_url(ref: SheetRef) -> str:
    if ref.is_sheet:
        url = f"https://docs.google.com/spreadsheets/d/{ref.file_id}/export?format=csv"
        return url + (f"&gid={ref.gid}" if ref.gid else "")
    return f"https://drive.google.com/uc?export=download&id={ref.file_id}"


def _check_csv(response: requests.Response) -> str:
    content_type = response.headers.get("Content-Type", "")
    if response.status_code in (401, 403, 404) or "text/html" in content_type:
        raise SyncError(
            "Google did not return the sheet. Open the sheet, click Share, set "
            "'General access' to 'Anyone with the link' (Viewer), then try again. "
            "Or switch to 'Google sign-in' in Settings."
        )
    if response.status_code != 200:
        raise SyncError(f"Google Drive answered with error {response.status_code}.")
    response.encoding = "utf-8"
    return response.text


def _fetch_with_link(ref: SheetRef) -> str:
    try:
        response = requests.get(_export_url(ref), timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        raise SyncError(f"No connection to Google Drive ({exc.__class__.__name__}).") from exc
    return _check_csv(response)


# --------------------------------------------------------------- Google sign-in
def credentials_path() -> Path:
    return paths.data_dir() / "credentials.json"


def token_path() -> Path:
    return paths.data_dir() / "token.json"


def _google_session():
    try:
        from google.auth.transport.requests import AuthorizedSession, Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:      # pragma: no cover - only if packages are missing
        raise SyncError("Google sign-in packages are not installed (see requirements.txt).") from exc

    creds = None
    if token_path().exists():
        creds = Credentials.from_authorized_user_file(str(token_path()), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if not credentials_path().exists():
            raise SyncError(
                f"Google sign-in needs an OAuth client file. Save it as "
                f"'credentials.json' in {paths.data_dir()} (see README, part 'Google sign-in')."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path()), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True,
                                      authorization_prompt_message="",
                                      success_message="SpeakDaily is connected. You can close this tab.")
        token_path().write_text(creds.to_json(), encoding="utf-8")
    return AuthorizedSession(creds)


def _fetch_with_google(ref: SheetRef) -> str:
    session = _google_session()
    if ref.is_sheet:
        url = _export_url(ref)
    else:
        url = f"https://www.googleapis.com/drive/v3/files/{ref.file_id}?alt=media"
    try:
        response = session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise SyncError(f"No connection to Google Drive ({exc.__class__.__name__}).") from exc
    if response.status_code in (403, 404):
        raise SyncError("Your Google account cannot open this file. Check the link and sharing.")
    return _check_csv(response)


def sign_out() -> None:
    try:
        token_path().unlink()
    except OSError:
        pass


def fetch_questions(link: str, mode: str = "link") -> list[Question]:
    ref = parse_link(link)
    text = _fetch_with_google(ref) if mode == "google" else _fetch_with_link(ref)
    try:
        questions = parse_csv_text(text, source="drive")
    except ValueError as exc:
        raise SyncError(str(exc)) from exc
    if not questions:
        raise SyncError("The sheet has no questions yet. Add rows under the header row.")
    return questions
