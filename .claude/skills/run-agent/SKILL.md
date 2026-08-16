---
name: run-agent
description: Run the inbox agent locally for testing and development
---

## Environment Check

!`cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate 2>/dev/null && python --version && echo "✓ Virtual env active" || echo "⚠ Virtual env not active"`

## Current Configuration

!`cd ${CLAUDE_PROJECT_DIR} && [ -f config.yaml ] && echo "✓ config.yaml found" || echo "⚠ config.yaml missing"`

## Task

Run the Inbox Architect Agent with the following options:

1. **Standard run** — Process unread emails with current config
2. **Debug mode** — Run with verbose logging to see LLM prompts and decisions
3. **Dry run** — Process emails without making changes to Gmail/Sheets/Drive
4. **Test run** — Process only a small batch for quick validation

Choose the mode and Claude will execute the appropriate command.

### Standard Run
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python agent.py
```

### Debug Run (verbose output)
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python agent.py --debug
```

### Dry Run (no side effects)
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python agent.py --dry-run
```

### With Log File
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python agent.py --log-file /tmp/inbox_architect.log
```

Monitor logs in another terminal with:
```bash
tail -f /tmp/inbox_architect.log
```
