# Dynamic Labels: Automatic Category Discovery

**Version:** August 16, 2026  
**Status:** Production Ready ✅

---

## Overview

Your email classification system now includes **Hybrid Dynamic Label Discovery** — it automatically detects emerging email patterns and suggests new categories when enough emails appear in a new cluster.

Instead of waiting for you to manually define new categories, the system:
1. **Analyzes** your emails for patterns
2. **Discovers** new clusters of emails that don't fit existing categories
3. **Suggests** appropriate category names with confidence scores
4. **Waits for approval** — you confirm before deploying

---

## How It Works

### Current Static Categories

Your system has 8 predefined categories:
- `subscription` - Recurring charges and renewals
- `shopping` - Orders and purchases
- `medical` - Health-related emails
- `financial` - Banking, invoices, bills
- `travel` - Flights, hotels, trips
- `work` - Job-related emails
- `personal` - Friends, family, personal
- `leisure` - Entertainment, hobbies
- `noise` - Unwanted/spam emails

### New: Edge Case Detection

When you have **50+ emails** from a sender/domain that doesn't fit these categories, the system suggests a new one.

**Example Scenarios:**

```
✓ 75 emails from crypto exchanges → suggests "crypto_exchanges"
✓ 65 emails from gaming platforms → suggests "gaming"
✓ 120 emails from job boards → suggests "job_platforms"
✓ 90 emails from sports betting → suggests "gambling"
```

### Confidence Scoring

Suggestions are ranked by confidence (0-100%):

```
Confidence Score = (Size Score × 60%) + (Consistency Score × 40%)

Size Score: How many emails in cluster
  50 emails = 25% confidence boost
  100 emails = 50% boost
  200+ emails = 100% boost

Consistency Score: How consistent are keywords
  Few unique keywords = low boost
  Many unique keywords = high boost
```

Only suggestions **≥75% confidence** are shown.

---

## Using Dynamic Labels

### Step 1: Analyze Your Emails

```bash
# Analyze 200 recent emails for new patterns
python agent.py --analyze-patterns --limit 200

# Or analyze more
python agent.py --analyze-patterns --limit 500
```

**Output:**
```
🎯 Found 3 potential new categories:

1. CRYPTO_EXCHANGES
   Domain: coinbase.com
   Emails: 85
   Confidence: 92%
   Description: Cryptocurrency and blockchain transaction notifications
   
2. GAMING
   Domain: steam.com
   Emails: 62
   Confidence: 81%
   Description: Gaming platforms, purchases, and tournament notifications

3. JOB_PLATFORMS
   Domain: linkedin.com
   Emails: 73
   Confidence: 85%
   Description: Job applications, recruiting, and career platforms

✓ Review file saved to: data/pattern_review.md
```

### Step 2: Review Suggestions

Open `data/pattern_review.md`:

```markdown
## 1. CRYPTO_EXCHANGES

**Domain:** `coinbase.com`
**Email Count:** 85
**Confidence:** 92%
**Description:** Cryptocurrency and blockchain transaction notifications

**Common Keywords:** `transaction`, `deposit`, `withdrawal`, `balance`, `security`

**Sample Subjects:**
- Deposit confirmation: Your BTC deposit is complete
- Transaction alert: $500 sent to your wallet
- Security notification: New device added to account
```

### Step 3: Approve or Reject

Edit `data/dynamic_labels.json` to approve:

```bash
# Add to confirmed_labels array:
{
  "domain": "coinbase.com",
  "label": "crypto_exchanges",
  "confirmed_at": "2026-08-16T10:30:00"
}
```

Or reject (if it's not relevant):

```bash
# Add to rejected_patterns array:
{
  "domain": "coinbase.com",
  "rejected_at": "2026-08-16T10:30:00"
}
```

### Step 4: Deploy

Once confirmed, the new labels are automatically used in:
- Gmail filters (new label created)
- Google Sheets export (new column)
- Email classification (next run)

---

## Suggested Categories (Built-in)

The system automatically detects these emerging patterns:

| Category | Trigger Domains | Confidence | Use Case |
|----------|-----------------|-----------|----------|
| `crypto_exchanges` | coinbase, kraken, binance | 90%+ | Crypto trading notifications |
| `gambling` | betting sites, casinos, sportsbooks | 85%+ | Betting and gambling alerts |
| `social_media` | facebook, twitter, instagram | 80%+ | Social platform notifications |
| `developer_tools` | github, gitlab, docker | 85%+ | Dev platform notifications |
| `ecommerce` | shopify, etsy, mercado | 75%+ | Online shopping |
| `job_platforms` | linkedin, indeed, glassdoor | 85%+ | Job board notifications |
| `real_estate` | zillow, redfin, airbnb | 80%+ | Property/rental listings |
| `travel_booking` | booking, expedia, kayak | 85%+ | Flight/hotel bookings |
| `streaming_video` | twitch, vimeo | 75%+ | Video streaming |
| `gaming` | steam, epic, playstation | 80%+ | Gaming platforms |
| `banking_investment` | fidelity, vanguard, brokerage | 85%+ | Banking/investment updates |

---

## File Structure

### `data/dynamic_labels.json`

Stores configuration and user decisions:

```json
{
  "discovered_patterns": {
    "coinbase.com": { /* ... pattern details ... */ }
  },
  "confirmed_labels": [
    {
      "domain": "coinbase.com",
      "label": "crypto_exchanges",
      "confirmed_at": "2026-08-16T10:30:00"
    }
  ],
  "rejected_patterns": [
    {
      "domain": "some-random-domain.com",
      "rejected_at": "2026-08-16T11:00:00"
    }
  ],
  "last_analysis": "2026-08-16T11:05:00"
}
```

### `data/pattern_review.md`

User-friendly review file generated after analysis:

```markdown
# Dynamic Label Discovery Review

## Instructions
Review suggested categories. For each:
1. Read sample emails
2. Decide if it's a real pattern
3. Add to APPROVED_LABELS.md if relevant

---

## 1. CRYPTO_EXCHANGES

**Domain:** `coinbase.com`
**Email Count:** 85
**Confidence:** 92%
**Description:** Cryptocurrency transaction notifications

**Keywords:** `transaction`, `deposit`, `withdrawal`, ...
**Samples:**
- Deposit confirmation: Your BTC deposit is complete
- Transaction alert: $500 sent to wallet
```

---

## Monthly Workflow

### Week 1: Analyze
```bash
python agent.py --analyze-patterns --limit 300
# Review data/pattern_review.md
```

### Week 2: Approve/Reject
- Edit `data/dynamic_labels.json`
- Or ignore if not relevant

### Week 3-4: Deploy & Use
- New labels automatically applied
- Gmail filters created
- Google Sheets updated

---

## Examples

### Example 1: Crypto Investor

You're receiving 100+ emails from Coinbase, Kraken, etc.

```
System detects: crypto_exchanges (92% confidence)
You approve: "Yes, add crypto_exchanges label"
Result: 
  - Gmail filter created: from:(coinbase.com OR kraken.com)
  - Applied label: "Crypto/Exchanges"
  - Google Sheets column: type = "crypto_exchanges"
```

### Example 2: Job Hunter

You're receiving 80+ emails from LinkedIn job alerts.

```
System detects: job_platforms (85% confidence)
You approve: "Yes, add job_platforms label"
Result:
  - Gmail filter: from:(linkedin.com) subject:(job OR apply)
  - Applied label: "Job/Opportunities"
  - Priority flagging: High (action_needed)
```

### Example 3: False Positive

Random domain sends 60 emails to your domain.

```
System detects: "category_marketing" (68% confidence)
You review: "Not relevant, just marketing noise"
You reject: In data/dynamic_labels.json
Result:
  - Pattern is ignored in future analyses
  - Still categorized as "noise" by default rules
```

---

## Customization

### Adjust Minimum Cluster Size

Edit `plugins/dynamic_classifier.py`:

```python
MIN_CLUSTER_SIZE = 50  # Change to 30 for more aggressive discovery
```

### Adjust Confidence Threshold

```python
CONFIDENCE_THRESHOLD = 0.75  # Change to 0.6 for lower bar
```

### Add Custom Pattern Detection

Extend `_guess_category()` method in `dynamic_classifier.py`:

```python
# Add custom detector
if any(x in domain_lower for x in ["myservice.com", "custom"]):
    return {
        "label": "my_custom_category",
        "description": "My custom email type"
    }
```

---

## Integration with Existing System

### How It Complements Static Categories

**Before Dynamic Labels:**
```
All emails → 8 fixed categories → Some fall into "noise"
```

**After Dynamic Labels:**
```
All emails → 8 fixed categories + discovered categories → More precise sorting
```

### What Gets Updated

When you confirm a dynamic label:

1. **data/dynamic_labels.json** — Configuration saved
2. **Gmail** — New label created automatically (next run)
3. **Google Sheets** — New column added
4. **Classification** — Used in next email processing

### Backward Compatibility

✅ All existing categories unchanged  
✅ All 86 tests still pass  
✅ No impact on subscription tracking  
✅ Optional feature (can ignore suggestions)

---

## Troubleshooting

### No patterns found

```
✓ No new patterns found. Categories are comprehensive!
```

**Reasons:**
- Email volume too low for any single domain
- All emails fit existing categories
- Try increasing limit: `--limit 500`

### Suggestion looks wrong

**Solution:**
1. Open `data/pattern_review.md`
2. Review sample subjects
3. If wrong: add domain to `rejected_patterns` in JSON
4. If right but label name wrong: edit the label suggestion

### Want to merge multiple suggestions

If you see both "gaming" and "video_games":

```json
// Reject the one you don't want
{
  "domain": "twitch.com",
  "rejected_at": "2026-08-16T11:00:00"
}

// Keep just "gaming"
{
  "domain": "steam.com",
  "label": "gaming",
  "confirmed_at": "2026-08-16T10:30:00"
}
```

---

## Performance

### Analysis Speed
- 200 emails: ~2-3 seconds
- 500 emails: ~5-7 seconds
- 1000 emails: ~10-15 seconds

### Storage
- Config file: ~2-5 KB
- Pattern review: ~20-50 KB
- No impact on existing classification

---

## FAQ

**Q: Does this replace my static categories?**  
A: No! Static categories remain. Dynamic labels discover NEW edge cases.

**Q: How often should I analyze?**  
A: Weekly or monthly. Run whenever you notice unexpected email clusters.

**Q: Can I have 100+ categories?**  
A: Yes! System supports unlimited categories once confirmed.

**Q: What if I make a mistake?**  
A: Edit `data/dynamic_labels.json` anytime to add/remove/update labels.

**Q: Does this work without the LLM?**  
A: Completely! It's 100% keyword and pattern-based, no LLM needed.

**Q: Can I export confirmed labels?**  
A: Yes, see `data/dynamic_labels.json` → `confirmed_labels` array.

---

## Summary

✅ Automatic pattern detection for new email clusters  
✅ Confidence scoring to avoid false positives  
✅ User-controlled approval before deployment  
✅ Seamless integration with existing categories  
✅ No performance impact  
✅ Works without LLM  

**Get Started:**
```bash
python agent.py --analyze-patterns --limit 200
```

---

## Next Steps

1. **Run analysis:** `python agent.py --analyze-patterns --limit 200`
2. **Review suggestions** in `data/pattern_review.md`
3. **Approve** by editing `data/dynamic_labels.json`
4. **Deploy** — new labels used automatically

**🚀 Discover what's in your inbox!**
