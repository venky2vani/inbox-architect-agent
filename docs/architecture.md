# Architecture & Internals

This document is for contributors and AI agents working on the project. It covers the plugin system, classification pipeline, local intelligence, dynamic labels, and key configuration layers.

## Project Architecture

```text
inbox-architect-agent/
├── agent.py                              # Orchestrator
├── plugins/                              # Plugin implementations
│   ├── base.py                           # Plugin interfaces
│   ├── gmail_connector.py                # Gmail source
│   ├── google_workspace_persistence.py   # Sheets + Drive storage
│   ├── llm_processor.py                  # LLM categorizer + fallback heuristics
│   ├── local_intelligence.py           # Self-updating rule cache
│   ├── dynamic_classifier.py             # Pattern discovery engine
│   ├── checkpoint.py                     # Processed-email tracking
│   └── retry.py                          # Retry/backoff decorator
├── prompts/                              # LLM prompt templates
│   └── system.txt                        # Default system prompt
├── ui/                                   # Review-mode UI
│   ├── review_server.py                  # FastAPI server
│   ├── review_runner.py                  # Batch review orchestrator
│   └── index.html                        # Web frontend
├── data/                                 # Runtime data (rules, checkpoints)
├── credentials/                          # OAuth credentials (gitignored)
└── tests/                                # Unit tests
```

## Plugin System

All connectors, processors, and persistence backends inherit from the base classes in `plugins/base.py`.

- **Connectors** end in `_connector.py`
- **Processors** end in `_processor.py`
- **Persistence** ends in `_persistence.py`

Plugin classes may differ from the PascalCase filename (e.g., `llm_processor.py` contains `SmartInboxProcessor`). Discovery falls back to inheritance.

### Adding a New Connector

Create `plugins/outlook_connector.py` that inherits from `EmailConnector` and name the class `OutlookConnector`. The orchestrator auto-discovers it on the next run.

## Classification Pipeline

For each email, the agent tries classifiers in this order:

1. **Sender overrides** — hard rules that bypass everything.
2. **Dynamic labels** — confirmed sender-domain patterns (`data/dynamic_labels.json`).
3. **Local intelligence** — learned rules (`data/local_rules.json`).
4. **LLM** — AI categorization when no shortcut matches.
5. **Fallback heuristics** — keyword-based rules when no LLM is configured.

### Pipeline Symbols

```
✓ SENDER OVERRIDE      → Hard rule matched (blocked LLM)
✓ DYNAMIC LABEL        → Confirmed pattern matched (blocked LLM)
✓ LOCAL INTEL          → Learned rule matched (blocked LLM)
🔴 LLM REQUIRED        → No shortcuts worked, must use AI
🔴 [LLM CALL]          → Actually calling the LLM API
🔴 [LLM RESULT]        → LLM response received
⚠️  FALLBACK           → No LLM available, using basic rules
```

### LLM Output Schema

The system prompt (`prompts/system.txt`) asks the LLM to produce:

```json
{
  "category": "action_needed|waiting_for|reference|noise",
  "priority": 1-5,
  "tags": ["medical", "finance", ...],
  "action_items": [...],
  "extracted_data": {
    "type": "invoice|payment|bill|refund|subscription|salary|investment|tax|medical|meeting|deadline|travel|notification|...",
    ...type-specific fields...
  }
}
```

When changing these fields, keep `plugins/llm_processor.py`, `plugins/google_workspace_persistence.py`, and `prompts/system.txt` in sync.

## Local Intelligence

`plugins/local_intelligence.py` implements a self-updating rule cache that learns from LLM outputs to avoid repeated API calls.

### How It Works

1. **Feature extraction**
   - `sender_domain` — Email domain (e.g., `netflix.com`)
   - `sender_email` — Full sender address
   - `subject_keyword` — Words in subject line
   - `body_keyword` — Words in email body

2. **Confidence scoring**
   - Confidence = Hits / (Hits + Misses)
   - Only applies patterns with confidence above the threshold

3. **Learning from LLM**
   - Every LLM classification updates rules
   - Similar future emails skip the LLM
   - Stale rules are pruned automatically

### Per-Email Flow

```
Email 1:
├─ Check local_intel.classify() → no match
├─ Call LLM
├─ LLM returns classification
└─ local_intel.learn() updates rules in memory AND saves to disk

Email 2 (same processor instance):
├─ Check local_intel.classify() → uses memory rules
├─ If confident match → NO LLM CALL
└─ Otherwise call LLM and learn again
```

A cached rule is used only when both confidence and hit count meet thresholds (defaults: confidence 0.85, min_hits 3).

### Configuration

```yaml
processor:
  local_intelligence:
    enabled: true
    rules_path: "data/local_rules.json"
    confidence_threshold: 0.85
    min_hits: 3
    prune_after_days: 30
```

Environment variables:
```bash
export LOCAL_INTELLIGENCE_ENABLED=true
export LOCAL_INTELLIGENCE_CONFIDENCE_THRESHOLD=0.75
```

### Tuning

- **More aggressive** (skip more LLM):
  ```yaml
  confidence_threshold: 0.70
  min_hits: 2
  ```

- **More conservative** (trust LLM more):
  ```yaml
  confidence_threshold: 0.95
  min_hits: 10
  ```

## Dynamic Labels

`plugins/dynamic_classifier.py` analyzes emails by sender domain and suggests patterns to auto-classify.

### Commands

```bash
# Analyze for patterns
python agent.py --analyze-patterns --limit 500

# Confirm a pattern
python agent.py --confirm-label payroll.company.com work

# Reject a pattern
python agent.py --reject-pattern unwanted.domain.com
```

### Data File (`data/dynamic_labels.json`)

```json
{
  "discovered_patterns": {},
  "confirmed_labels": [],
  "rejected_patterns": [],
  "last_analysis": null
}
```

Confirmed labels are checked before local intelligence in the classification pipeline.

## Configuration Layers

Configuration is layered:

1. **CLI arguments** — highest priority
2. **`config.yaml`** — project-level defaults
3. **Hardcoded defaults** — lowest priority

### Key Settings

```yaml
agent:
  name: "Inbox Architect Agent"
  plugins_dir: "plugins"
  daily_digest:
    limit: 500
    archive_noise: true
    batch_size: 50
    checkpoint_path: "data/checkpoint.json"

processor:
  rate_limit_delay: 0.2
  local_intelligence:
    enabled: true
    rules_path: "data/local_rules.json"
    confidence_threshold: 0.85
    min_hits: 3
    prune_after_days: 30
```

## Parallel Processing

The pipeline uses `ThreadPoolExecutor` for batch processing. Each batch is parallelized independently.

- Worker count defaults to `min(8, (os.cpu_count() or 4) * 2)`.
- Each email has a 120-second timeout.
- Errors are logged per email without stopping the batch.

Environment variables:
```bash
export PARALLEL_PROCESSING=true
export PARALLEL_MAX_WORKERS=8
export LLM_RATE_LIMIT_DELAY=0.2
```

## Review-Mode UI

`ui/` wraps the agent to process emails one batch at a time, pause on LLM-required items, suggest domain/keyword rules, and persist accepted rules to `data/dynamic_labels.json` or `data/local_rules.json`.

Start it with:
```bash
python agent.py --ui
# or
python -m uvicorn ui.review_server:app --reload --host 127.0.0.1 --port 8000
```

## LLM Provider Setup

Supported providers via environment variables:

```bash
# Anthropic (default)
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
export OPENAI_API_KEY=sk-...

# OpenAI-compatible endpoint
export OPENAI_BASE_URL=https://api.example.com/v1
export OPENAI_API_KEY=sk-...
```

The system prompt path can be overridden:
```bash
export LLM_SYSTEM_PROMPT_PATH=path/to/system.txt
```

## Retry and Checkpointing

- `plugins/retry.py` provides retry/backoff for transient API errors.
- `plugins/checkpoint.py` tracks processed email IDs so long runs can resume.
- Large-batch settings live under `agent.daily_digest` and `processor.rate_limit_delay`.

## Medical & Bill Classification

`plugins/llm_processor.py` contains keyword dictionaries and extraction helpers for medical and bill documents.

### Medical Keywords

```python
medical_keywords = {
    "lab_result": ["lab result", "laboratory result", "test result", "blood work", "pathology report"],
    "prescription": ["prescription", "rx", "refill", "medication"],
    "appointment": ["appointment", "doctor's visit", "consultation", "checkup"],
    "discharge": ["discharge summary", "discharge note", "hospital discharge"],
    "vaccination": ["vaccination", "vaccine", "immunization"],
    "health_insurance": ["insurance", "claim", "policy", "coverage", "deductible"],
    "doctor_note": ["doctor's note", "medical note", "physician note", "clinical note"],
}
```

### Bill Priority Logic

```python
if days_left <= 3:
    priority = max(priority, 5)
    tags.append("urgent")
elif days_left <= 7:
    priority = max(priority, 4)
    tags.append("due-soon")
```

## Development Notes for Agents

- Follow PEP 8 and run `python -m py_compile` before committing.
- Keep plugins isolated: each backend must inherit from base classes.
- Use type hints for public functions and methods.
- Do not commit credentials or `token.json`.
- Update `requirements.txt` and `requirements-dev.txt` when adding dependencies.
- Update this document when project structure or conventions change.

## See Also

- [user-guide.md](user-guide.md) — Setup and daily use
- [classification-guide.md](classification-guide.md) — Categories, tags, and schemas
- [operations-guide.md](operations-guide.md) — Commands, learning loop, and monitoring
