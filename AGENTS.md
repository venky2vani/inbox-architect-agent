# AGENTS.md — inbox-architect-agent

> This file is intended for AI coding agents working on this project.

## Project overview

- Project name: `inbox-architect-agent`
- Technology stack: **Python 3.10+**
- Runtime architecture: Console/command-line application
- Main entry point: `agent.py`
- Also available: Google Apps Script edition in `apps-script/`

## Project structure

```text
inbox-architect-agent/
├── agent.py                              # Orchestrator
├── ui/                                   # Interactive review-mode UI
│   ├── review_server.py                  # FastAPI server
│   ├── review_runner.py                  # Batch-by-batch review orchestrator
│   └── index.html                        # Web frontend
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

## Build and test commands

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run the agent
python agent.py

# Dry-run 10 emails without side effects
python agent.py --dry-run --limit 10

# Run tests
python -m pytest tests/ -q

# Syntax check
python -m py_compile agent.py plugins/*.py tests/*.py ui/*.py

# Start the interactive review UI
python -m uvicorn ui.review_server:app --reload --host 127.0.0.1 --port 8000

# Docker
 docker compose up --build
```

## Code style guidelines

- Follow PEP 8 and run `python -m py_compile` before committing.
- Keep plugins isolated: each connector/processor/persistence backend must
  inherit from the base classes in `plugins/base.py`.
- Use type hints for public functions and methods.
- Do not commit credentials or `token.json`.

## Testing instructions

Add `tests/test_*.py` files and run:

```bash
python -m pytest tests/ -q
```

## Security considerations

- Store OAuth credentials in `credentials/` only; this directory is gitignored.
- Do not log email bodies or attachment contents.
- Use environment variables or `.env` for API keys.

## Notes for agents

- Update `requirements.txt` and `requirements-dev.txt` when adding dependencies.
- The agent uses a plugin discovery convention: filenames ending in
  `_connector.py`, `_persistence.py`, or `_processor.py` are auto-loaded.
  Plugin classes may differ from the PascalCase filename (e.g.
  `llm_processor.py` contains `SmartInboxProcessor`); discovery falls back to
  inheritance in that case.
- Configuration is layered: CLI args > `config.yaml` > hardcoded defaults.
- The LLM processor supports OpenAI, Anthropic Claude, and OpenAI-compatible APIs
  via env vars (`LLM_PROVIDER`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `OPENAI_BASE_URL`).
- The system prompt is loaded from `prompts/system.txt` by default; the path
  can be overridden with `LLM_SYSTEM_PROMPT_PATH` or `processor.prompt_path`.
- The LLM prompt schema outputs `tags` and `extracted_data.type` with values such
  as `invoice`, `payment`, `bill`, `refund`, `subscription`, `salary`,
  `investment`, `tax`, `medical`, `meeting`, `deadline`, `travel`, and `notification`.
  Keep `plugins/llm_processor.py`, `plugins/google_workspace_persistence.py`,
  and `prompts/system.txt` in sync when changing these fields.
- Medical document classification: The system automatically detects and classifies
  medical documents including lab results, prescriptions, appointment confirmations,
  discharge summaries, vaccination records, and health insurance documents. Medical
  emails are tagged with "medical" and "health" for easy filtering. Prescription
  and appointment emails are marked as "action_needed" for immediate attention.
- `plugins/local_intelligence.py` implements a self-updating rule cache that
  learns from LLM outputs to avoid repeated API calls. Configure it via
  `processor.local_intelligence` in `config.yaml` or the corresponding
  `LOCAL_INTELLIGENCE_*` env vars.
- `plugins/retry.py` provides a retry/backoff decorator for transient API errors.
- `plugins/checkpoint.py` tracks processed email IDs so long runs can resume.
- Large-batch settings live under `agent.daily_digest` (`batch_size`,
  `checkpoint_path`) and `processor.rate_limit_delay`.
- `plugins/llm_processor.py` exposes an `on_llm_required` callback so callers can
  be notified whenever an email bypasses sender overrides, dynamic labels, and
  local intelligence and reaches the LLM.
- The review-mode UI (`ui/`) wraps the agent to process emails one batch at a
  time, pause on LLM-required items, suggest domain/keyword rules, and persist
  accepted rules to `data/dynamic_labels.json` or `data/local_rules.json`.
- Update this file when project structure or conventions change.
