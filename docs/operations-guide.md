# Operations Guide

This guide covers the daily workflow, commands, learning loop, monitoring, parallel processing, and subscription management.

## One-Command Workflow

```bash
./run_and_learn.sh
```

This single command:
1. Processes 500 emails.
2. Shows classification breakdown.
3. Reports learning efficiency.
4. Suggests new automation rules.
5. Prompts to confirm and save rules.

## Common Tasks

### Run Daily Digest
```bash
python agent.py
```

### Run with Logging
```bash
python agent.py --log-file logs/digest.log
```

### Dry Run (No Side Effects)
```bash
python agent.py --dry-run --limit 50
```

### Launch Interactive Review UI
```bash
python agent.py --ui
# Opens http://127.0.0.1:8000 in your browser
# Process emails one batch at a time with live suggestions
```

### Resume and Reset
```bash
python agent.py --resume              # Continue from checkpoint
python agent.py --reset-checkpoint    # Start fresh
```

### Analyze Post-Run (What LLM Did)
```bash
python post_run_learner.py logs/digest.log
```

### Check Learning Progress
```bash
python monitor_efficiency.py
```

### Find New Patterns to Automate
```bash
python agent.py --analyze-patterns --limit 500
# Review suggestions in data/pattern_review.md
```

### Save a New Pattern
```bash
python agent.py --confirm-label <domain> <category>

# Examples:
python agent.py --confirm-label payroll.company.com work
python agent.py --confirm-label alerts.bank.co.in banking_investment
python agent.py --confirm-label hr.company.com work
```

### Reject a Pattern
```bash
python agent.py --reject-pattern generic-domain.com
```

## Learning Loop in 4 Steps

1. **Run Everything** (5 min)
   ```bash
   ./run_and_learn.sh
   ```

2. **Review Suggestions** (2 min)
   - Read what the LLM classified.
   - Look for patterns mentioned in the report.

3. **Confirm High-Confidence Rules** (1 min)
   ```bash
   # For patterns with >80% confidence:
   python agent.py --confirm-label pattern.domain.com category
   ```

4. **Monitor Progress** (30 sec)
   ```bash
   python monitor_efficiency.py
   # Watch local hits % increase each run
   ```

### Expected Progress (10 Runs)

| Run | Local Hits | LLM Calls | Status |
|-----|-----------|-----------|--------|
| 1   | 20%       | 80%       | Building initial rules |
| 2   | 35%       | 65%       | Patterns emerging |
| 3   | 45%       | 55%       | Learning accelerating |
| 4   | 52%       | 48%       | Getting good |
| 5   | 58%       | 42%       | Solid progress |
| 6   | 63%       | 37%       | High efficiency |
| 7   | 68%       | 32%       | Very good |
| 8   | 72%       | 28%       | Excellent |
| 9   | 76%       | 24%       | Mature system |
| 10  | 79%       | 21%       | Optimal |

## Monitoring LLM Usage

### Run with Log File (Recommended)
```bash
python agent.py --log-file logs/digest.log
python analyze_logs.py logs/digest.log
```

### Run with Console Logging (Real-time)
```bash
python agent.py --log-level INFO 2>&1 | tee logs/digest.log
```

### Understanding the Log Symbols

```
✓ SENDER OVERRIDE      → Hard rule matched (blocked LLM)
✓ DYNAMIC LABEL        → Confirmed pattern matched (blocked LLM)
✓ LOCAL INTEL          → Learned rule matched (blocked LLM)
🔴 LLM REQUIRED        → No shortcuts worked, must use AI
🔴 [LLM CALL]          → Actually calling the LLM API
🔴 [LLM RESULT]        → LLM response received
🔴 [LLM ERROR]         → LLM returned invalid response
⚠️  FALLBACK           → No LLM available, using basic rules
```

### Filter Just LLM Calls
```bash
grep "🔴 \[LLM" logs/digest.log
```

### Filter Just Local Hits
```bash
grep "✓ LOCAL INTEL" logs/digest.log
```

### Example Summary Output
```
📈 Summary (Total: 500 emails)
  ✓ Sender Override:     25  (  5.0%)
  ✓ Dynamic Labels:      30  (  6.0%)
  ✓ Local Intelligence: 280  ( 56.0%)
  🔴 LLM Required:      165  ( 33.0%)
  ⚠️  LLM Errors:         0  (  0.0%)

💡 Efficiency:
  Emails that SKIPPED LLM: 335 (67.0%)
  Emails that NEEDED LLM:  165 (33.0%)
```

### Performance Goals

| Metric | Target |
|--------|--------|
| Local Intel Hits | >60% |
| Avg LLM Time | <2s |
| False Positives | <5% |

## Parallel Processing

Parallel processing is **enabled by default** using an optimal worker count.

### Enable / Disable
```bash
# Default (parallel enabled)
python agent.py

# Sequential
export PARALLEL_PROCESSING=false
python agent.py
```

### Configure Workers
```bash
# Auto-detect (CPU count * 2, capped at 8) - DEFAULT
python agent.py

# Specific number
export PARALLEL_MAX_WORKERS=4
python agent.py
```

### Important: Rate Limiting

Without rate limiting, parallel workers can exceed API quotas:

```bash
# BAD: 8 workers × 3 LLM calls/sec = 24 calls/sec
export PARALLEL_MAX_WORKERS=8
export LLM_RATE_LIMIT_DELAY=0
```

```bash
# GOOD: slower, safer
export PARALLEL_MAX_WORKERS=8
export LLM_RATE_LIMIT_DELAY=0.5
```

### Recommended Settings

| Environment | Workers | Delay |
|-------------|---------|-------|
| Small inbox (< 100 emails) | 4 | 0.5s |
| Medium inbox (100-500 emails) | 8 | 0.3s |
| Large inbox (500+ emails) | 8 | 0.2s |
| Limited API quota | 4 | 1.0s |

### Tuning for Performance Issues

- **Rate limit errors:** increase `LLM_RATE_LIMIT_DELAY`
- **Memory too high:** reduce `PARALLEL_MAX_WORKERS`
- **Emails getting stuck:** reduce workers or increase timeout
- **Debug a single email:** disable parallel and use `--limit 1`

## Subscription Tracking

The agent detects subscription emails and flags expensive or soon-renewing ones.

### What Gets Detected

| Category | Examples |
|----------|----------|
| Streaming | Netflix, Spotify, Hulu, Disney+, Prime Video |
| Software | Adobe, Microsoft 365, Slack, Figma, Notion |
| Cloud | Dropbox, Google One, iCloud, OneDrive |
| News | Medium, Wall Street Journal, NY Times |
| Fitness | Peloton, Headspace, Calm, Gym |
| Membership | Annual subscriptions, auto-renew |

### Extracted Fields

```json
{
  "type": "subscription",
  "subscription": {
    "service": "Netflix",
    "amount": "$15.99",
    "renewal_date": "2026-09-16",
    "category": "streaming"
  },
  "tags": ["subscription", "streaming"],
  "priority": 2
}
```

### Priority & Tags

| Condition | Priority | Tag |
|-----------|----------|-----|
| >$15/month | 4 | `expensive` |
| Renews ≤3 days | 4 | `renews-soon` |
| Renews ≤7 days | 3 | `renews-week` |
| Normal | 2 | `subscription` |

### Money-Saving Workflow

1. Run classification:
   ```bash
   python agent.py --dry-run --limit 100
   ```
2. In Google Sheets, filter: `type = "subscription"`
3. Sort by amount (highest first)
4. Identify unused services
5. Cancel unused subscriptions
6. Track savings

## Files Reference

```text
data/
├── dynamic_labels.json      ← Confirmed patterns
├── local_rules.json         ← Learned rules
├── pattern_review.md        ← Suggestions from --analyze-patterns
└── checkpoint.json          ← Resume progress

logs/
└── digest.log               ← Full run logs

scripts/
├── run_and_learn.sh         ← All-in-one workflow
├── post_run_learner.py      ← Post-run suggestions
├── analyze_logs.py          ← Log analysis
└── monitor_efficiency.py    ← Progress tracking
```

## Cost Estimation

**Per 500 emails:**
- With 80% local hits (20% LLM): 100 × $0.0002 = **$0.02**
- With 50% local hits (50% LLM): 250 × $0.0002 = **$0.05**
- With 20% local hits (80% LLM): 400 × $0.0002 = **$0.08**

**Monthly** (assuming 2 runs/day):
- Optimized: ~**$0.72**
- Unoptimized: ~**$4.80**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Local hits not increasing | Run `--analyze-patterns`, confirm patterns with `--confirm-label` |
| LLM calls still high | Increase pattern analysis limit: `--limit 1000` |
| No patterns found | Needs more data, run with `--limit 1000` |
| Emails going to LLM despite dynamic labels | Check exact domain in `data/dynamic_labels.json` and use `--confirm-label` |
| Classifications seem random | Review `tail -50 logs/digest.log | grep "LLM RESULT"` and verify `prompts/system.txt` |
| Rate limit errors | Increase `LLM_RATE_LIMIT_DELAY` or reduce `PARALLEL_MAX_WORKERS` |
| High memory usage | Reduce `PARALLEL_MAX_WORKERS` |
| Want to reset | `rm data/local_rules.json && python agent.py --reset-checkpoint` |

## Full Command Cheat Sheet

```bash
# Run & Learn (recommended)
./run_and_learn.sh

# Core operations
python agent.py                           # Run digest
python agent.py --limit 500               # Process 500 emails
python agent.py --dry-run --limit 10      # No side effects
python agent.py --analyze-patterns        # Find patterns
python agent.py --ui                      # Interactive review UI

# Confirm/Reject patterns
python agent.py --confirm-label domain category
python agent.py --reject-pattern domain

# Analysis tools
python post_run_learner.py logs/digest.log
python analyze_logs.py logs/digest.log
python monitor_efficiency.py

# Logging options
python agent.py --log-level DEBUG
python agent.py --log-file logs/custom.log

# Resume & Reset
python agent.py --resume
python agent.py --reset-checkpoint

# Help
python agent.py --help
```
