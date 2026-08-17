# Inbox Architect Agent

An extensible, plugin-based email agent that connects to Gmail, processes emails with an LLM, and stores summaries in Google Sheets while archiving attachments in Google Drive.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your LLM key to .env (optional)
python agent.py
```

On first run, a browser window opens for OAuth authorization. The token is saved to `credentials/token.json` for subsequent runs.

## Documentation

All documentation has been consolidated into the `docs/` directory:

- **[docs/user-guide.md](docs/user-guide.md)** — Setup, Docker, scheduling, and project overview
- **[docs/operations-guide.md](docs/operations-guide.md)** — Daily commands, learning loop, monitoring, parallel processing, subscription tracking
- **[docs/classification-guide.md](docs/classification-guide.md)** — Categories, tags, smart detection, extraction schemas
- **[docs/architecture.md](docs/architecture.md)** — Plugin system, classification pipeline, internals for contributors
- **[docs/apps-script.md](docs/apps-script.md)** — Zero-infrastructure Google Apps Script edition
- **[docs/README.md](docs/README.md)** — Documentation index

## Key Features

- **Plugin architecture** — add connectors, processors, or persistence backends without touching core code.
- **Gmail connector** — fetches unread mail, downloads attachments, archives noise automatically.
- **Google Workspace persistence** — metadata index in Google Sheets, raw attachments organized by date in Google Drive.
- **LLM processor** — categorizes emails and extracts action items. Supports OpenAI, Anthropic Claude, and OpenAI-compatible APIs.
- **Local residual intelligence** — learns from LLM outputs and short-circuits future API calls for similar emails.
- **Dynamic labels** — confirm sender-domain patterns to bypass the LLM.
- **Review-mode UI** — process emails one batch at a time with live suggestions (`python agent.py --ui`).

## Testing

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

## Docker

```bash
docker compose up --build
```

For details, see [docs/user-guide.md](docs/user-guide.md#docker).

## License / Contributing

See the project source and [docs/architecture.md](docs/architecture.md) for development conventions.
