"""OAuth scope diagnostic for the Inbox Architect Agent.

Run this script to verify that Google has granted all required scopes and that
each API (Gmail, Drive, Sheets) is reachable.
"""

import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Same scopes used by the agent.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def main() -> int:
    credentials_path = Path("credentials/credentials.json")
    token_path = Path("credentials/token.json")

    print(f"Credentials file: {credentials_path.absolute()}")
    print(f"Token file: {token_path.absolute()}")

    if not credentials_path.exists():
        print("ERROR: credentials/credentials.json not found.")
        return 1

    creds: Credentials | None = None
    if token_path.exists():
        print("Found existing token.json; loading...")
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        print("Token expired; refreshing...")
        creds.refresh(Request())
    elif not creds or not creds.valid:
        print("Starting interactive OAuth flow...")
        print("Make sure you grant ALL requested scopes on the Google page.")
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)

    # Persist token.
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    print("\n=== Granted scopes ===")
    for scope in creds.scopes or []:
        print(f"  - {scope}")

    missing = set(SCOPES) - set(creds.scopes or [])
    if missing:
        print("\nERROR: Missing scopes:")
        for scope in missing:
            print(f"  - {scope}")
        print("\nFix: add these scopes to your OAuth consent screen, delete token.json,")
        print("and run this script again.")
        return 1

    print("\nAll required scopes present. Testing APIs...")

    # Test Gmail API.
    try:
        gmail = build("gmail", "v1", credentials=creds)
        profile = gmail.users().getProfile(userId="me").execute()
        print(f"  [OK] Gmail API — {profile.get('emailAddress')}")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"  [FAIL] Gmail API — {exc}")

    # Test Drive API.
    try:
        drive = build("drive", "v3", credentials=creds)
        about = drive.about().get(fields="user").execute()
        print(f"  [OK] Drive API — {about.get('user', {}).get('emailAddress')}")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"  [FAIL] Drive API — {exc}")

    # Test Sheets API.
    try:
        sheets = build("sheets", "v4", credentials=creds)
        # List a sample spreadsheet; if none exist, just verify the service builds.
        sheets.spreadsheets().get(spreadsheetId="dummy", ranges=[]).execute()
    except Exception as exc:  # pylint: disable=broad-except
        # We expect a 404 because "dummy" does not exist; any other error is real.
        error = str(exc)
        if "notFound" in error or "Requested entity was not found" in error:
            print("  [OK] Sheets API — service reachable")
        else:
            print(f"  [FAIL] Sheets API — {exc}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
