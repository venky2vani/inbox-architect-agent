# Inbox Architect Agent

An extensible, plugin-based email agent that connects to Gmail, processes emails
with an LLM, and stores summaries in Google Sheets while archiving attachments in
Google Drive.

## Features

- **Plugin architecture** — drop in new connectors (Outlook, etc.), processors,
  or persistence backends without changing core code.
- **Gmail connector** — fetches unread mail, downloads attachments, archives
  noise automatically.
- **Google Workspace persistence** — metadata index in Google Sheets, raw
  attachments organized by date in Google Drive.
- **LLM processor** — categorizes emails as `action_needed`, `waiting_for`,
  `reference`, or `noise`; assigns priority; extracts action items; and infers
  financial/bill/payment tags (`invoice`, `payment`, `bill`, `refund`,
  `subscription`, `salary`, `investment`, `tax`, etc.). Supports OpenAI, Anthropic
  Claude, and OpenAI-compatible APIs. Falls back to rule-based processing when no
  API key is configured.
- **Customizable prompts** — edit `prompts/system.txt` or point to your own
  prompt file via `LLM_SYSTEM_PROMPT_PATH`.
- **Local residual intelligence** — learns from LLM outputs and short-circuits
  future API calls for similar emails, reducing cost and latency.

## Project structure

```text
inbox-architect-agent/
├── agent.py                              # Orchestrator
├── plugins/
│   ├── base.py                           # Plugin interfaces
│   ├── gmail_connector.py                # Gmail source
│   ├── google_workspace_persistence.py   # Sheets + Drive storage
│   └── llm_processor.py                  # LLM categorizer
├── prompts/                              # LLM prompt templates
│   └── system.txt                        # Default system prompt
├── apps-script/                          # Zero-infrastructure GAS edition
├── credentials/                          # OAuth credentials (gitignored)
├── tests/                                # Unit tests
├── .github/workflows/ci.yml              # GitHub Actions CI
├── config.yaml                           # Runtime configuration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy the example environment file and add your LLM key (optional):

   ```bash
   cp .env.example .env
   ```

   Supports OpenAI (`OPENAI_API_KEY`), Anthropic Claude (`ANTHROPIC_API_KEY`
   with `LLM_PROVIDER=anthropic`), or any OpenAI-compatible endpoint.

3. Enable the Gmail API and Google Drive/Sheets APIs in Google Cloud Console and
   download `credentials.json`:
   <https://console.cloud.google.com/apis/credentials>

4. Place the downloaded file at:

   ```text
   credentials/credentials.json
   ```

5. Run the agent:

   ```bash
   python agent.py
   ```

   On first run, a browser window will open for OAuth authorization. The token
   is saved to `credentials/token.json` for subsequent runs.

## Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

For a one-off run:

```bash
docker build -t inbox-architect-agent .
docker run --rm -v $(pwd)/credentials:/app/credentials:ro --env-file .env inbox-architect-agent
```

## Scheduling

Run daily at 08:00 via cron:

```cron
0 8 * * * cd /home/venkatesh/inbox-architect-agent && /home/venkatesh/inbox-architect-agent/.venv/bin/python agent.py --log-file /tmp/inbox_architect.log >> /tmp/inbox_architect.log 2>&1
```

Or use the Google Apps Script edition in `apps-script/` for fully hosted scheduling.

## Adding a new connector

Create `plugins/outlook_connector.py` that inherits from `EmailConnector` and
name the class `OutlookConnector`. The orchestrator will auto-discover it on the
next run.

## Local residual intelligence

The agent can learn from the LLM and skip future API calls for similar emails.
Configure it in `config.yaml`:

```yaml
processor:
  local_intelligence:
    enabled: true
    rules_path: "data/local_rules.json"
    confidence_threshold: 0.85
    min_hits: 3
    prune_after_days: 30
```

Rules are learned from sender domain, sender email, subject keywords, and body
keywords. A cached rule is only used when its confidence and hit count meet the
thresholds.

## Large-batch resilience

For runs with many emails, the agent supports:

- **Batching** — process emails in chunks and persist intermediate results.
- **Checkpoint/resume** — skip already-processed emails when restarting.
- **Per-email error isolation** — one bad email does not stop the whole run.
- **Retry/backoff** — transient API errors are retried automatically.
- **Rate limiting** — optional delay between LLM calls.

```yaml
agent:
  daily_digest:
    limit: 1000
    batch_size: 50
    checkpoint_path: "data/checkpoint.json"

processor:
  rate_limit_delay: 0.2
```

Run with resume after a crash:

```bash
python agent.py --limit 1000 --resume --log-file run.log
```

Reset the checkpoint when starting fresh:

```bash
python agent.py --reset-checkpoint
```

## Testing

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```
