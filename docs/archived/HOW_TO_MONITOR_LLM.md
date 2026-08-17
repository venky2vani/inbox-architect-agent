# How to Monitor LLM Usage & Classification Pipeline

## Quick Start

### 1. Run with Log File (Recommended)

```bash
python agent.py --log-file logs/digest.log

# Then analyze:
python analyze_logs.py logs/digest.log
```

### 2. Run with Console Logging (Real-time)

```bash
python agent.py --log-level INFO 2>&1 | tee logs/digest.log
```

### 3. Filter Just LLM Calls

```bash
python agent.py --log-level INFO 2>&1 | grep "🔴"
```

---

## Understanding the Log Symbols

### Classification Pipeline (in order):

```
✓ SENDER OVERRIDE      → Hard rule matched (blocked LLM)
✓ DYNAMIC LABEL        → Confirmed pattern matched (blocked LLM)
✓ LOCAL INTEL          → Learned rule matched (blocked LLM)
🔴 LLM REQUIRED        → No shortcuts worked, must use AI
🔴 [LLM CALL]          → Actually calling the LLM API
🔴 [LLM RESULT]        → LLM response received
🔴 [LLM ERROR]         → LLM returned invalid response
⚠️  FALLBACK           → No LLM available, using basic rules
→ Checking...          → Debug info (shows decision process)
```

---

## Example Output

### A Run with Mixed Classification:

```
✓ SENDER OVERRIDE | Your Payme | from: boss@company.com
✓ DYNAMIC LABEL | Netflix Subscription | category: streaming
✓ LOCAL INTEL | Your Package Arrived | category: shopping (confidence: 0.85)
🔴 LLM REQUIRED | Unusual Activity Alert | Reason: No sender override, no dynamic label, no local rule match
🔴 [LLM CALL] Sending to OPENAI: Unusual Activity Alert
🔴 [LLM RESULT] Category: action_needed | Priority: 4 | 1.23s | Unusual Activity...
✓ LOCAL INTEL | Your Order Shipped | category: shopping (confidence: 0.92)
🔴 LLM REQUIRED | Quarterly Report from Finance | Reason: No sender override, no dynamic label, no local rule match
🔴 [LLM CALL] Sending to OPENAI: Quarterly Report from Finance
🔴 [LLM RESULT] Category: reference | Priority: 2 | 0.98s | Quarterly Report...
```

---

## Analysis Scripts

### Full Summary
```bash
python analyze_logs.py logs/digest.log
```

**Output:**
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

### Just LLM Calls
```bash
grep "🔴 \[LLM" logs/digest.log | head -20
```

### Just Local Intelligence Hits
```bash
grep "✓ LOCAL INTEL" logs/digest.log | head -20
```

### Count by Category
```bash
grep "Category:" logs/digest.log | grep -o "Category: [a-z_]*" | sort | uniq -c
```

---

## Interpreting the Numbers

### Good Efficiency (Goal: >60% skip LLM)
```
Local hits: 280/500 = 56%  ✓ Good
Local hits: 350/500 = 70%  ✓ Excellent
Local hits: 100/500 = 20%  ✗ Poor (keep training)
```

### Why Emails Go to LLM

1. **New sender** — Never seen before, no rules
2. **Unique content** — Doesn't match any learned patterns
3. **Ambiguous keywords** — Multiple possible categories
4. **First-time category** — Building initial rules

---

## Configuration Tuning

### To skip more emails (aggressive)
```yaml
# config.yaml
processor:
  local_intelligence:
    confidence_threshold: 0.70  # Lower = more aggressive
    min_hits: 2                 # Lower = trust rules sooner
```

### To call LLM more (conservative)
```yaml
# config.yaml
processor:
  local_intelligence:
    confidence_threshold: 0.95  # Higher = only very confident
    min_hits: 10                # Higher = require more training
```

---

## Troubleshooting

### Q: Why is one email going to LLM when similar ones don't?
**A:** Check the sender domain or keywords:
```bash
grep "Your Order" logs/digest.log
# See if one was "LOCAL INTEL" and another was "LLM REQUIRED"
```

### Q: Is the learning system working?
**A:** Check the trend over 3-4 runs:
```bash
tail -1 logs/digest.log  # Last line should have summary
# Watch if "Local intelligence hits" increases each run
```

### Q: How much does LLM cost?
**A:** Each LLM call ≈ $0.0001-0.0005 (with gpt-4o-mini)
```
165 LLM calls × $0.0002 = $0.033 per batch
```

---

## Performance Goals

| Metric | Target | Your Current |
|--------|--------|--------------|
| Local Intel Hits | >60% | Check logs |
| Avg LLM Time | <2s | Check logs |
| False Positives | <5% | Monitor misses in local_rules.json |

