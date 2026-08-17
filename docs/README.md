# Inbox Architect Agent — Documentation

This directory contains the consolidated documentation for the Inbox Architect Agent.

## Start Here

- **[user-guide.md](user-guide.md)** — Project overview, setup, Docker, scheduling, and local intelligence configuration.
- **[operations-guide.md](operations-guide.md)** — Daily commands, learning loop, monitoring, parallel processing, and subscription tracking.
- **[classification-guide.md](classification-guide.md)** — Categories, tags, smart detection, extraction schemas, and Gmail filter examples.
- **[architecture.md](architecture.md)** — Plugin system, classification pipeline, local intelligence, dynamic labels, and internals for contributors.
- **[apps-script.md](apps-script.md)** — Zero-infrastructure Google Apps Script edition.

## What Kind of AI Agent Is This?

Inbox Architect Agent is a **task-oriented autonomous agent** for email management. It combines an LLM reasoning layer with external tool use, persistent memory, and a learning loop:

- **Perceives:** Fetches unread emails via the Gmail connector.
- **Reasons:** Uses an LLM (OpenAI, Anthropic, or OpenAI-compatible) to classify priority, summarize content, and extract structured data.
- **Acts:** Archives noise, applies Gmail labels, writes metadata to Google Sheets, and uploads attachments to Google Drive.
- **Learns:** Builds local rules and confirmed sender-domain labels so similar emails skip the LLM in the future.

The classification pipeline runs every email through sender overrides → dynamic labels → local intelligence → LLM → fallback heuristics. See [architecture.md](architecture.md#classification-pipeline) for details.

### Agentic features

| Feature | Description |
|---------|-------------|
| Autonomous triage | Decides category, priority, and actions without user input |
| Multi-tool use | Gmail, Google Sheets, Google Drive, and LLM APIs orchestrated together |
| Memory | `data/local_rules.json` and `data/dynamic_labels.json` persist learned patterns |
| Self-improvement | `python agent.py --analyze-patterns` suggests new classification rules |
| Resilience | Checkpoints, retry/backoff, parallel processing, per-email timeouts |
| Human-in-the-loop | Review UI (`python agent.py --ui`) and pattern confirmation/rejection |

## Quick Reference

| If you want to... | Read |
|-------------------|------|
| Set up the agent | [user-guide.md](user-guide.md#setup) |
| Run the daily digest | [operations-guide.md](operations-guide.md#common-tasks) |
| Learn how classification works | [classification-guide.md](classification-guide.md) |
| Understand the plugin system | [architecture.md](architecture.md#plugin-system) |
| Tune parallel processing | [operations-guide.md](operations-guide.md#parallel-processing) |
| Add or confirm automation rules | [operations-guide.md](operations-guide.md#learning-loop-in-4-steps) |
| Deploy with Google Apps Script | [apps-script.md](apps-script.md) |
| Review retired/historical docs | [archived/README.md](archived/README.md) |

## Archived Documentation

Historical and superseded documents are preserved in [archived/](archived/README.md) for reference.
