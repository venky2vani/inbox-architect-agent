# AGENTS.md — inbox-architect-agent

> This file is intended for AI coding agents working on this project.

For full architecture, plugin system, and internals documentation, see **[docs/architecture.md](docs/architecture.md)**.

## Quick Reference

- **Stack:** Python 3.10+
- **Entry point:** `agent.py`
- **Tests:** `python -m pytest tests/ -q`
- **Syntax check:** `python -m py_compile agent.py plugins/*.py tests/*.py ui/*.py`
- **Review UI:** `python -m uvicorn ui.review_server:app --reload --host 127.0.0.1 --port 8000`
- **Docker:** `docker compose up --build`

## Code Style & Security

- Follow PEP 8.
- Plugins must inherit from base classes in `plugins/base.py`.
- Use type hints for public functions and methods.
- Do not commit credentials, `token.json`, or `.env` secrets.
- Do not log email bodies or attachment contents.

## Key Conventions

- Plugin discovery: filenames ending in `_connector.py`, `_persistence.py`, or `_processor.py` are auto-loaded.
- Configuration precedence: CLI args > `config.yaml` > hardcoded defaults.
- Keep `plugins/llm_processor.py`, `plugins/google_workspace_persistence.py`, and `prompts/system.txt` in sync when changing output schema fields.
- Update `requirements.txt` / `requirements-dev.txt` and [docs/architecture.md](docs/architecture.md) when adding dependencies or changing conventions.

## See Also

- [docs/README.md](docs/README.md) — Documentation index
- [docs/user-guide.md](docs/user-guide.md) — Setup and daily use
- [docs/operations-guide.md](docs/operations-guide.md) — Commands, learning loop, monitoring
- [docs/classification-guide.md](docs/classification-guide.md) — Categories, tags, schemas
