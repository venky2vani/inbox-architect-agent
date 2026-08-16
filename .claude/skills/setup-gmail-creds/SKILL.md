---
name: setup-gmail-creds
description: Configure Gmail API credentials and validate OAuth setup
---

## Credentials Status

!`cd ${CLAUDE_PROJECT_DIR} && [ -f credentials/credentials.json ] && echo "✓ credentials.json found" || echo "⚠ credentials.json missing"`

!`cd ${CLAUDE_PROJECT_DIR} && [ -f credentials/token.json ] && echo "✓ token.json found (OAuth already authorized)" || echo "⚠ token.json missing (first run will prompt OAuth)"`

## Task

Set up Gmail API credentials for the Inbox Architect Agent.

### Prerequisites

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 credential (Desktop app)
3. Download the JSON file

### Setup Steps

1. **Place credentials file**
   ```bash
   cp ~/Downloads/credentials.json ${CLAUDE_PROJECT_DIR}/credentials/
   ```

2. **Verify the file**
   ```bash
   cd ${CLAUDE_PROJECT_DIR} && python -c "
   import json
   with open('credentials/credentials.json') as f:
       data = json.load(f)
       print(f'Client ID: {data[\"installed\"][\"client_id\"][:30]}...')
       print(f'Scopes: Gmail API (read/modify/delete)')
   "
   ```

3. **Run agent to authorize**
   ```bash
   cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python agent.py
   ```
   On first run, a browser window opens for OAuth consent. Once approved, `credentials/token.json` is saved automatically.

4. **Verify authorization**
   ```bash
   cd ${CLAUDE_PROJECT_DIR} && [ -f credentials/token.json ] && echo "✓ OAuth authorized" || echo "✗ Authorization failed"
   ```

### Required Gmail API Scopes

The agent requests:
- `https://www.googleapis.com/auth/gmail.readonly` — Read email
- `https://www.googleapis.com/auth/gmail.modify` — Archive/mark as read
- `https://www.googleapis.com/auth/drive` — Store attachments
- `https://www.googleapis.com/auth/spreadsheets` — Write summaries

### Troubleshooting

**"Invalid credentials" error:**
- Download fresh `credentials.json` from Google Cloud Console
- Delete `credentials/token.json` and re-authorize

**"OAuth consent screen not configured":**
- Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → OAuth consent screen
- Add your email as a test user (for development)

**"Gmail API not enabled":**
- Go to [APIs Library](https://console.cloud.google.com/apis/library)
- Search and enable: Gmail API, Google Drive API, Google Sheets API