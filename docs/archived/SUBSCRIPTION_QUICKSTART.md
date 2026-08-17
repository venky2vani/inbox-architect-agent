# Subscription Tracking - Quick Start (2 minutes)

## What You Get

Your system now **automatically finds all subscriptions** and flags expensive ones (>$15/month).

---

## Try It Now

```bash
# See all subscription emails in your inbox
python agent.py --dry-run --limit 50
```

Look for emails with:
- **Type:** `"subscription"`
- **Amount:** Monthly/annual cost
- **Tags:** `"expensive"` (if >$15/month) or `"renews-soon"` (if within 3 days)

---

## What Gets Detected

| Service | Cost | Category |
|---------|------|----------|
| Netflix, Spotify, Disney+ | $9-22/mo | 📺 Streaming |
| Adobe, Microsoft 365, Slack | $12-99+/mo | 💻 Software |
| Dropbox, Google One, iCloud | $9-20/mo | ☁️ Cloud |
| Peloton, Headspace, Gym | $15-40/mo | 💪 Fitness |
| Medium, NYT, Newsletters | $10-20/mo | 📰 News |

---

## Key Info Extracted

```json
{
  "type": "subscription",
  "subscription": {
    "service": "Netflix",              ← Service name
    "amount": "$15.99",                ← Monthly cost
    "renewal_date": "2026-09-16",      ← When it renews
    "category": "streaming"            ← Type of service
  },
  "tags": ["subscription", "streaming"],
  "priority": 2
}
```

---

## Filtering in Google Sheets

**Find all subscriptions:**
```
Filter: type = "subscription"
```

**Find expensive subscriptions (>$15/month):**
```
Filter: type = "subscription" AND tags contains "expensive"
Sort by: amount (highest first)
```

**Find renewals this week:**
```
Filter: type = "subscription" AND tags contains "renews-soon"
Sort by: renewal_date
```

---

## Save Money

### This Week
- [ ] Run: `python agent.py --dry-run --limit 50`
- [ ] Check Google Sheets for "expensive" subscriptions
- [ ] Identify 2-3 unused services

### This Month
- [ ] Unsubscribe from 1 unused service/week
- [ ] Track cancellations in CANCELLED_SUBSCRIPTIONS.md
- [ ] Calculate monthly savings

---

## Action Items Generated

For each subscription, you get:

✅ **Charge notifications:**
> "Review Netflix subscription charge of $15.99. Consider cancelling if unused"

✅ **Renewal alerts:**
> "Review subscription renewal. Check if still needed and cancel if unused"

✅ **Expensive warnings:**
> "Review Adobe subscription charge of $54.99"

---

## Gmail Labels

Create label: **Subscriptions**
- Subscriptions/Expensive (flag with star)
- Subscriptions/Active
- Subscriptions/Renewing Soon
- Subscriptions/Cancelled

Then filter in Gmail:
```
subject:(subscription OR renewal OR billing)
OR from:(billing@)
```

---

## Example Dashboard

Create in Google Sheets:

**Pivot Table:**
```
Services (rows) | Category (columns) | Total Cost (values)

Netflix         | Streaming         | $15.99
Spotify         | Streaming         | $12.99
Adobe           | Software          | $54.99
──────────────────────────────
Total Monthly Spend: ~$85/month
```

---

## Common Actions

### Find all subscriptions
```
In Sheets: Filter → type = "subscription"
```

### Find most expensive
```
In Sheets: Sort by amount (descending)
Top 5 subscriptions shown first
```

### Find expiring soon
```
In Sheets: Filter → tags contains "renews-soon"
```

### Check a service
```
In Sheets: Filter → subscription.service = "Netflix"
See all Netflix-related charges
```

---

## Quick Commands

```bash
# See classifications
python agent.py --dry-run --limit 20

# Run full classification
python agent.py

# See with verbose output
python agent.py --dry-run --limit 10 --verbose

# Run tests
python -m pytest tests/test_subscription_tracking.py -v
```

---

## What Gets Tagged

**Primary:**
- `subscription` - All subscriptions
- `streaming`, `software`, `cloud`, `news`, `fitness` - Category

**Secondary:**
- `expensive` - >$15/month (review & cancel)
- `renews-soon` - Renewing within 3 days (action needed)
- `renews-week` - Renewing within 7 days (review soon)

---

## Money Saved Example

**Before tracking:** Paying for 8 subscriptions, ~$150/month
- Netflix: $15.99
- Spotify: $12.99
- Adobe Creative: $54.99
- Dropbox: $11.99
- Gym (unused): $49.99
- Medium: $12.99
- Headspace: $14.95
- Microsoft 365: $8.99

**After cancelling unused:**
- Cancelled gym (-$49.99)
- Cancelled Medium (-$12.99)
- Cancelled Headspace (-$14.95)

**New monthly cost: $102/month**
**Annual savings: $540+**

---

## Next Steps

1. **Run it:** `python agent.py --dry-run --limit 50`
2. **Review:** Open Google Sheets, filter for subscriptions
3. **Identify:** Find subscriptions you don't use
4. **Cancel:** Unsubscribe from 1-2 this week
5. **Save:** Track cancellations and celebrate savings!

**💰 Let's find money you didn't know you were spending!**
