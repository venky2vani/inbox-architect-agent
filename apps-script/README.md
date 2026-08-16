# Inbox Architect Agent — Google Apps Script Edition

A zero-infrastructure version of the Inbox Architect Agent that runs entirely
inside Google's cloud.

## What it does

1. Runs on a daily trigger (default: 08:00).
2. Reads unread Gmail messages.
3. Sends each message to OpenAI for categorization and summarization.
4. Stores attachments in `Drive/EmailAgent/YYYY-MM-DD/`.
5. Appends metadata to a Google Sheet named **Email Agent Index**.
6. Archives emails categorized as `noise`.

## Setup

1. Go to <https://script.google.com> and create a new project.
2. Copy the contents of `Code.gs` into the script editor.
3. Save the project.
4. Run `setOpenAIApiKey('sk-...')` once in the editor to store your OpenAI key
   securely in Script Properties.
5. Run `createDailyTrigger()` once to schedule daily execution at 08:00.
6. Run `runInboxArchitect()` manually to test.

## Required OAuth Scopes

The first time you run the script, Google will prompt for these scopes:

- Gmail (read, modify, archive)
- Google Drive (create folders/files)
- Google Sheets (create spreadsheet, append rows)

## Configuration

Edit the `CONFIG` object at the top of `Code.gs`:

```js
const CONFIG = {
  SHEET_NAME: 'Email Agent Index',
  DRIVE_ROOT_FOLDER: 'EmailAgent',
  OPENAI_MODEL: 'gpt-4o-mini',
  MAX_EMAILS: 50,
  ARCHIVE_NOISE: true,
};
```

## Manual controls

| Function | Purpose |
| --- | --- |
| `runInboxArchitect()` | Run the agent once manually |
| `createDailyTrigger()` | Schedule daily 08:00 run |
| `removeTriggers()` | Remove all agent triggers |
| `setOpenAIApiKey('sk-...')` | Save OpenAI key |

## Notes

- If no OpenAI key is set, the script falls back to simple keyword-based
  categorization.
- The script processes only the newest message in each unread thread.
