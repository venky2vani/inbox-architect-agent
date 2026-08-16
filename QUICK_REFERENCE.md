# 🚀 Quick Reference - Learning Loop Commands

## One-Command Workflow

```bash
./run_and_learn.sh
```

This single command:
1. ✅ Processes 500 emails
2. 📊 Shows classification breakdown
3. 📈 Reports learning efficiency  
4. 🤖 Suggests new automation rules
5. 💾 Prompts to confirm and save rules

---

## Common Tasks

### Run Daily Digest
```bash
python agent.py
```

### Run with Logging
```bash
python agent.py --log-file logs/digest.log
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
```

### Launch Interactive Review UI
```bash
python agent.py --ui
# Opens http://127.0.0.1:8000 in your browser
# Process emails one batch at a time with live suggestions
```

### Save a New Pattern
```bash
python agent.py --confirm-label <domain> <category>

# Examples:
python agent.py --confirm-label payroll.company.com work
python agent.py --confirm-label alerts.bank.co.in banking_investment
python agent.py --confirm-label hr.company.com work
```

### Reject a Pattern (Don't Auto-Classify)
```bash
python agent.py --reject-pattern generic-domain.com
```

---

## Learning Loop in 4 Steps

### Step 1: Run Everything (5 min)
```bash
./run_and_learn.sh
```

### Step 2: Review Suggestions (2 min)
```bash
# Read what LLM classified
# Look for patterns mentioned in the report
```

### Step 3: Confirm High-Confidence Rules (1 min)
```bash
# For patterns with >80% confidence:
python agent.py --confirm-label pattern.domain.com category
```

### Step 4: Monitor Progress (30 sec)
```bash
python monitor_efficiency.py
# Watch local hits % increase each run
```

---

## Expected Progress (10 Runs)

| Run | Local Hits | LLM Calls | Status |
|-----|-----------|-----------|--------|
| 1   | 20%       | 80%       | 🟡 Building initial rules |
| 2   | 35%       | 65%       | 🟡 Patterns emerging |
| 3   | 45%       | 55%       | 🟡 Learning accelerating |
| 4   | 52%       | 48%       | 🟢 Getting good |
| 5   | 58%       | 42%       | 🟢 Solid progress |
| 6   | 63%       | 37%       | 🟢 High efficiency |
| 7   | 68%       | 32%       | 🟢 Very good |
| 8   | 72%       | 28%       | 🟢 Excellent |
| 9   | 76%       | 24%       | 🟢 Mature system |
| 10  | 79%       | 21%       | 🟢 Optimal |

---

## Log Analysis

### See Classification Pipeline
```bash
python analyze_logs.py logs/digest.log
```

Output shows:
- ✓ Sender overrides (hard rules)
- ✓ Dynamic labels (confirmed patterns)
- ✓ Local intelligence hits
- 🔴 LLM required (why they went to AI)

### Filter Just LLM Calls
```bash
grep "🔴 LLM" logs/digest.log
```

### Filter Just Local Hits
```bash
grep "✓ LOCAL" logs/digest.log
```

---

## Files Reference

```
data/
├── dynamic_labels.json      ← Confirmed patterns (49 domains)
├── local_rules.json         ← Learned rules (5000+ patterns)
├── pattern_review.md        ← Suggestions from --analyze-patterns
└── checkpoint.json          ← Resume progress

logs/
├── digest.log               ← Full run logs
└── previous_runs/

scripts/
├── run_and_learn.sh         ← All-in-one workflow
├── post_run_learner.py      ← Post-run suggestions
├── analyze_logs.py          ← Log analysis
└── monitor_efficiency.py    ← Progress tracking
```

---

## Cost Estimation

**Per 500 emails:**
- With 80% local hits (20% LLM): 100 × $0.0002 = **$0.02**
- With 50% local hits (50% LLM): 250 × $0.0002 = **$0.05**
- With 20% local hits (80% LLM): 400 × $0.0002 = **$0.08**

**Monthly** (assuming 2 runs/day):
- Optimized: 60 LLM calls × $0.0002 × 60 = ~**$0.72**
- Unoptimized: 400 LLM calls × $0.0002 × 60 = ~**$4.80**

**Savings: ~$4/month per user** 💰

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Local hits not increasing | Run `--analyze-patterns`, confirm patterns with `--confirm-label` |
| LLM calls still high | Increase pattern analysis limit: `--limit 1000` |
| No patterns found | Needs more data, run with `--limit 1000` |
| Want to reset | `rm data/local_rules.json && python agent.py --reset-checkpoint` |

---

## Full Command Cheat Sheet

```bash
# Run & Learn (recommended)
./run_and_learn.sh

# Core operations
python agent.py                           # Run digest
python agent.py --limit 500               # Process 500 emails
python agent.py --analyze-patterns        # Find patterns

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
python agent.py --dry-run                 # Don't save to Sheets

# Resume & Reset
python agent.py --resume                  # Continue from checkpoint
python agent.py --reset-checkpoint        # Start fresh

# Help
python agent.py --help
```

---

## Next Steps

1. **Run your first full cycle:**
   ```bash
   ./run_and_learn.sh
   ```

2. **After each run, confirm 2-3 high-confidence patterns:**
   ```bash
   python agent.py --confirm-label <domain> <category>
   ```

3. **Check progress weekly:**
   ```bash
   python monitor_efficiency.py
   ```

4. **Target: 75%+ local hit rate in 2 weeks** 🎯

---

*For detailed docs, see: [LEARNING_LOOP.md](LEARNING_LOOP.md)*
