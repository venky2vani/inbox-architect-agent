# Dynamic Labels — Quick Start (2 minutes)

## What It Does

Automatically discovers NEW email categories when 50+ emails appear from a domain that doesn't fit your existing 8 categories.

---

## Try It Now

```bash
# Analyze your emails for new patterns
python agent.py --analyze-patterns --limit 200
```

**Output:**
```
🎯 Found 3 potential new categories:

1. CRYPTO_EXCHANGES
   Emails: 85
   Confidence: 92%

2. GAMING
   Emails: 62
   Confidence: 81%

3. JOB_PLATFORMS
   Emails: 73
   Confidence: 85%

✓ Review file saved to: data/pattern_review.md
```

---

## Review & Approve (1 minute)

1. **Read** `data/pattern_review.md`
2. **Decide** if each category makes sense
3. **Edit** `data/dynamic_labels.json` to approve

```json
// Add to confirmed_labels array:
{
  "domain": "coinbase.com",
  "label": "crypto_exchanges",
  "confirmed_at": "2026-08-16T10:30:00"
}
```

---

## Deploy (Automatic)

New labels are automatically used in:
- ✅ Gmail filters
- ✅ Google Sheets columns
- ✅ Email classification
- ✅ Priority tagging

---

## Typical Discoveries

| Pattern | Emails | Example Domains |
|---------|--------|-----------------|
| Crypto | 50-200+ | coinbase, kraken, binance |
| Gaming | 30-100+ | steam, epic, playstation |
| Job Boards | 50-150+ | linkedin, indeed, glassdoor |
| Sports Betting | 40-80+ | draftkings, fanduel, betmgm |
| Developer Tools | 60-200+ | github, gitlab, docker |

---

## Monthly Workflow

```
Week 1: python agent.py --analyze-patterns --limit 300
        ↓
Week 2: Review data/pattern_review.md
        ↓
Week 3: Edit data/dynamic_labels.json to approve
        ↓
Week 4: New categories deployed automatically ✅
```

---

## File Reference

| File | Purpose |
|------|---------|
| `data/pattern_review.md` | Human-readable suggestions |
| `data/dynamic_labels.json` | Configuration & approvals |
| `plugins/dynamic_classifier.py` | Discovery engine |

---

## Commands

```bash
# Analyze 200 emails
python agent.py --analyze-patterns --limit 200

# Analyze 500 emails (more thorough)
python agent.py --analyze-patterns --limit 500

# Show all confirmed labels
cat data/dynamic_labels.json | grep confirmed_labels
```

---

## Examples

### Scenario 1: Crypto Investor
```
System finds: 85 emails from coinbase.com
Suggests: crypto_exchanges (92% confidence)
You: Approve ✓
Result: New Gmail label, Google Sheets column, auto-tagging
```

### Scenario 2: Gamer
```
System finds: 62 emails from steam.com
Suggests: gaming (81% confidence)
You: Approve ✓
Result: All Steam emails tagged and categorized
```

### Scenario 3: Not Relevant
```
System finds: 40 emails from random-newsletter.com
Suggests: category_newsletter (65% confidence)
You: Reject (edit data/dynamic_labels.json)
Result: Pattern ignored, emails stay in "noise"
```

---

## Key Points

✅ **Automatic** — No manual configuration needed  
✅ **Smart** — Confidence scoring avoids false positives  
✅ **Controlled** — You approve before deploying  
✅ **Flexible** — Add/remove anytime  
✅ **Fast** — Analyzes 200 emails in ~2 seconds  

---

## Next Steps

1. Run: `python agent.py --analyze-patterns --limit 200`
2. Review: `data/pattern_review.md`
3. Approve: Edit `data/dynamic_labels.json`
4. Done! New labels used automatically

**Questions?** See `DYNAMIC_LABELS_GUIDE.md`

**Ready?** 🚀 `python agent.py --analyze-patterns --limit 200`
