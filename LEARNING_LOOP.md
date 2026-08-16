# 🤖 Automated Learning Loop - Post-Run Analysis

## The Complete Learning Workflow

Every time you run the agent, it learns what can be automated next time.

```
┌─────────────────────────────────────────────────────────────┐
│  Run Daily Digest                                           │
│  (500 emails: 50% LLM, 50% learned rules)                  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Analyze What LLM Did                                       │
│  "45 shopping emails, 30 banking, 25 unknown patterns"     │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Check Learning Efficiency                                  │
│  Local hits: 250/500 (50%) - up from 240 (48%) last run   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Suggest New Automation Rules                               │
│  "Emails from payroll@company.com are always 'work'"       │
│  "Alerts from bank.co.in are always 'banking_investment'"  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  User Confirms New Rules                                    │
│  $ python agent.py --confirm-label payroll.company.com work │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Next Run = Fewer LLM Calls (More Automation)              │
│  Local hits: 280/500 (56%) - up from 250                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start: Run with Full Learning Loop

### Option 1: All-in-One (Recommended)

```bash
./run_and_learn.sh
```

This runs in sequence:
1. ✅ Daily digest (processes 500 emails)
2. 📊 Classification pipeline analysis
3. 📈 Learning efficiency report
4. 🤖 Pattern suggestions with user prompt

### Option 2: Step-by-Step (Manual Control)

```bash
# Step 1: Run the digest
python agent.py --log-level INFO --log-file logs/digest.log

# Step 2: See what got classified
python analyze_logs.py logs/digest.log

# Step 3: Check learning progress
python monitor_efficiency.py

# Step 4: Get automation suggestions
python post_run_learner.py logs/digest.log
```

---

## Understanding the Post-Run Analysis

### Example Output

```
🔍 POST-RUN LEARNING ANALYSIS
======================================================================

📊 LLM Usage Summary:
   Total LLM calls: 165
   Total time:      180.54s
   Avg per email:   1.09s
   Est. cost:       $0.033

📂 Classifications by Category:

   ACTION_NEEDED         45 emails ( 27.3%)
   Average priority: 4.2
   Sample subjects:
      • Payment Due Tomorrow
      • Action Required: Verify Identity
      • Your Account Needs Attention

   REFERENCE             52 emails ( 31.5%)
   Average priority: 2.1
   Sample subjects:
      • Weekly Report Summary
      • Meeting Minutes Available
      • Documentation Update

   SHOPPING              40 emails ( 24.2%)
   Average priority: 2.8
   Sample subjects:
      • Your Order Has Shipped
      • Delivery Scheduled
      • Return Authorized

   SUBSCRIPTION          28 emails ( 17.0%)
   Average priority: 2.0
   Sample subjects:
      • Subscription Renewal Confirmed
      • Your Premium Membership

======================================================================
💡 SUGGESTIONS FOR AUTOMATION
======================================================================

The emails above were classified by LLM. To automate future similar emails:

1️⃣  ANALYZE PATTERNS
    Run pattern analysis to find sender domains:

    $ python agent.py --analyze-patterns --limit 500

    This will discover patterns like:
    • emails from "noreply@specific-company.com" → always "action_needed"
    • emails from "alerts@bank.com" → always "banking_investment"
    • subject keywords → categories

2️⃣  REVIEW SUGGESTIONS
    Check the generated file:
    $ cat data/pattern_review.md

    Shows confidence scores for each pattern.

3️⃣  CONFIRM NEW LABELS
    For patterns you trust (>80% confidence):

    $ python agent.py --confirm-label payroll.company.com work
    $ python agent.py --confirm-label alerts.bank.com banking_investment

    This adds them to data/dynamic_labels.json

4️⃣  IMPROVE LOCAL RULES
    The local intelligence system learns from each LLM classification.
    Each run should increase local hits and decrease LLM calls.

    Monitor with:
    $ python monitor_efficiency.py

⏭️  NEXT STEPS

   High-volume categories to focus on:
   • action_needed (45 emails) → Good candidates for automation
   • reference (52 emails) → Look for patterns
   • shopping (40 emails) → Already mostly automated

🤖 Would you like to analyze patterns now? (y/n):
```

---

## Workflow Examples

### Example 1: First Run (Building Initial Rules)

```bash
$ ./run_and_learn.sh
# Output shows:
#   Local hits: 100/500 (20%) - initial state
#   LLM calls: 400/500 (80%) - lots to learn

# Post-run analysis suggests:
#   "emails from alerts@bank.co.in are 90% 'banking_investment'"
#   "emails with 'payment' in subject are 85% 'action_needed'"

$ python agent.py --analyze-patterns --limit 500
# Shows high-confidence patterns

$ python agent.py --confirm-label alerts@bank.co.in banking_investment
$ python agent.py --confirm-label payroll@company.com work
# Adds 2 new rules
```

### Example 2: Second Run (System Learning)

```bash
$ ./run_and_learn.sh
# Output shows:
#   Local hits: 280/500 (56%) - improved from 100!
#   LLM calls: 220/500 (44%) - reduced from 400

# Post-run analysis shows:
#   "Great progress! Local intelligence now covers 56% of emails"
#   "New patterns found in remaining 220 LLM emails..."

$ python agent.py --analyze-patterns --limit 500
# Suggests more patterns to confirm
```

### Example 3: After 10 Runs (Mature System)

```bash
$ ./run_and_learn.sh
# Output shows:
#   Local hits: 420/500 (84%) - excellent!
#   LLM calls: 80/500 (16%) - only edge cases need AI

# Post-run analysis shows:
#   "Excellent learning! Only 80 emails need LLM"
#   "Suggested patterns for the remaining edge cases"

# These 80 are likely:
#   - New domains never seen before
#   - Genuinely ambiguous emails
#   - Unusual formats
```

---

## Adding New Rules from Post-Run Analysis

### Step 1: Run and Analyze
```bash
./run_and_learn.sh

# When prompted:
# 🤖 Would you like to analyze patterns now? (y/n): y
```

### Step 2: Review Generated Suggestions
```bash
cat data/pattern_review.md

# Output:
# ## 1. BANKING_INVESTMENT
# 
# **Domain:** `alerts@mybank.co.in`
# **Email Count:** 45
# **Confidence:** 87%
# **Keywords:** statement, account, balance, transaction
# **Samples:**
# - Your Monthly E-Statement
# - Account Balance Alert
# - Transaction Confirmation
```

### Step 3: Confirm High-Confidence Patterns
```bash
# If confidence >= 80%, safe to auto-classify
python agent.py --confirm-label alerts@mybank.co.in banking_investment
python agent.py --confirm-label alerts@mybank.co.in banking_investment

# Check what was saved:
cat data/dynamic_labels.json | grep -A2 alerts@mybank.co.in
```

### Step 4: Monitor Improvement
```bash
python monitor_efficiency.py

# Should show increased efficiency on next run
```

---

## Configuration Tuning

### Be More Aggressive (Skip More LLM)
```yaml
# config.yaml
processor:
  local_intelligence:
    confidence_threshold: 0.70   # Lower = more aggressive
    min_hits: 2                  # Lower = trust rules sooner
```

This will:
- Use more learned rules (even if not perfect)
- Reduce LLM calls (saves money)
- May have slightly lower accuracy

### Be More Conservative (Trust LLM More)
```yaml
# config.yaml
processor:
  local_intelligence:
    confidence_threshold: 0.95   # Higher = more conservative
    min_hits: 10                 # Higher = require more proof
```

This will:
- Use only very confident rules
- More LLM calls (costs more)
- Higher accuracy

---

## Monitoring Trends

Track efficiency over multiple runs:

```bash
# Create a tracking file
echo "Run,LocalHits,LLMCalls,Efficiency" > learning_trends.csv

# After each run:
python monitor_efficiency.py | grep "Total hits" >> learning_trends.csv

# Plot the trend:
# (Open in Excel or your favorite tool)
```

Expected trend over 10 runs:
```
Run 1:  20% local hits,  80% LLM  (building initial rules)
Run 2:  35% local hits,  65% LLM  (learning accelerates)
Run 3:  45% local hits,  55% LLM  (rules getting better)
Run 4:  52% local hits,  48% LLM
Run 5:  58% local hits,  42% LLM  (steady improvement)
Run 6:  63% local hits,  37% LLM
Run 7:  68% local hits,  32% LLM
Run 8:  72% local hits,  28% LLM
Run 9:  76% local hits,  24% LLM
Run 10: 79% local hits,  21% LLM  (mature system)
```

---

## Complete Command Reference

```bash
# Run everything with learning loop
./run_and_learn.sh

# Just run digest
python agent.py

# Run and save logs
python agent.py --log-file logs/digest.log

# Analyze logs
python analyze_logs.py logs/digest.log

# Check efficiency
python monitor_efficiency.py

# Post-run learning suggestions
python post_run_learner.py logs/digest.log

# Pattern analysis (generates data/pattern_review.md)
python agent.py --analyze-patterns --limit 500

# Confirm a new rule
python agent.py --confirm-label <domain> <category>

# Reject a pattern
python agent.py --reject-pattern <domain>

# View local rules
cat data/local_rules.json | python -m json.tool

# View dynamic labels
cat data/dynamic_labels.json | python -m json.tool
```

---

## Troubleshooting

### Q: Local hits aren't increasing
**A:** Check:
1. Are new patterns being found? `python agent.py --analyze-patterns`
2. Are you confirming them? `python agent.py --confirm-label`
3. Is local intelligence enabled? Check `config.yaml`

### Q: LLM calls still high
**A:** Try:
1. Increase `limit` to analyze more emails: `python agent.py --analyze-patterns --limit 1000`
2. Lower confidence threshold in `config.yaml`
3. Check `data/local_rules.json` for low-confidence rules (may have many misses)

### Q: Want to reset and start over
**A:**
```bash
# Reset local rules
rm data/local_rules.json

# Reset dynamic labels (keep only core ones)
# Edit data/dynamic_labels.json manually

# Reset checkpoint
python agent.py --reset-checkpoint
```

---

## Summary

The learning loop works like this:

1. **Each run processes emails** using multiple classifiers (overrides → dynamic labels → local rules → LLM)
2. **Post-run analysis shows what LLM did** and why it was needed
3. **You review high-confidence patterns** from the post-run analysis
4. **You confirm patterns to turn into rules** (one-command)
5. **Next run uses new rules**, reducing LLM calls
6. **Efficiency improves over time** with each run

**Best practice:** Run `./run_and_learn.sh` regularly (daily or weekly) and confirm new patterns as they're suggested. After 10 runs, you'll see 80%+ efficiency! 🚀

