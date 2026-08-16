# Extended Email Classification - Quick Start

## What's New ✨

Your inbox agent now automatically classifies emails into **8 major categories**:

| Category | Examples | Label | Priority |
|----------|----------|-------|----------|
| **Medical** | Lab results, prescriptions, appointments | medical | 3-4 |
| **Bills** | Invoices, payments, subscriptions | finance/bill | 2-5 |
| **Travel** | Flights, hotels, car rentals | travel | 2-3 |
| **Leisure** | Concerts, movies, sports, restaurants | leisure | 2 |
| **Shopping** | Orders, shipments, deliveries | shopping | 2-3 |
| **Work** | Projects, collaboration, assignments | work | 4 |
| **Personal** | Family, friends, social | personal | 2-3 |
| **Noise** | Promotions, newsletters | noise | 1 |

---

## Try It Out (1 minute)

```bash
# Test classification on 5 emails (no changes)
python agent.py --dry-run --limit 5

# Run all tests
python -m pytest tests/ -v

# See results
# ✅ 65/65 tests passing
#   - 28 existing tests
#   - 16 medical/bill tests
#   - 21 new classification tests
```

---

## Set Up Gmail Labels (5 minutes)

Go to **Gmail Settings → Labels → Create new label:**

```
✅ Create these labels:
  Financial
  ├── Bills
  ├── Invoices
  └── Subscriptions

  Medical
  ├── Prescriptions
  ├── Appointments
  └── Lab Results

  Travel
  ├── Flights
  ├── Hotels
  └── Bookings

  Leisure
  ├── Events
  ├── Tickets
  └── Restaurants

  Shopping
  ├── Orders
  ├── Shipments
  └── Returns

  Work
  └── Projects

  Personal
  └── Social
```

---

## Create Gmail Filters (5 minutes)

**Gmail Settings → Filters and Blocked Addresses → Create a new filter:**

### Bills
```
Matches: subject:(bill OR invoice OR payment due)
Apply label: Financial/Bills
```

### Travel
```
Matches: from:(airline OR hotel OR booking) 
         OR subject:(flight OR hotel OR reservation)
Apply label: Travel
```

### Shopping
```
Matches: from:(amazon OR ebay) 
         OR subject:(order confirmation OR shipped)
Apply label: Shopping
```

### Work
```
Matches: from:company.com 
         AND subject:(project OR review OR assigned)
Apply label: Work
```

### Medical
```
Matches: from:(doctor OR clinic OR pharmacy OR lab)
         OR subject:(prescription OR appointment)
Apply label: Medical
```

---

## Enable LLM (Optional, 2 minutes)

For better classification accuracy:

```bash
export ANTHROPIC_API_KEY=sk-your-key-here
export LLM_PROVIDER=anthropic
python agent.py
```

*Note: Works great without LLM too! The system uses fallback keyword matching.*

---

## See Results in Google Sheets

Once configured, all emails are automatically extracted to your Google Sheet with:

- **Type:** medical, travel, event, order, work, personal, bill, etc.
- **Tags:** finance, medical, travel, leisure, shopping, work, personal, urgent
- **Priority:** 1-5 (5=urgent)
- **Extracted Data:** amounts, dates, destinations, providers, etc.

---

## Common Email Classifications

### Travel
```
✈️ Flight confirmation from airline.com
→ Type: travel | Tag: travel | Priority: 3

🏨 Hotel reservation from marriott.com
→ Type: travel | Tag: travel | Priority: 3
```

### Leisure
```
🎭 Concert ticket from ticketmaster.com
→ Type: event | Tag: leisure | Priority: 2

🍽️ Restaurant reservation from opentable.com
→ Type: event | Tag: leisure | Priority: 2
```

### Shopping
```
📦 Order confirmation from amazon.com
→ Type: order | Tag: shopping | Priority: 2

📬 Package delivered notification
→ Type: order | Tag: shopping | Priority: 3
```

### Work
```
📋 Project update from team lead
→ Type: work | Tag: work | Priority: 4

👁️ Code review request from GitHub
→ Type: work | Tag: work | Priority: 4
```

### Personal
```
👨‍👩‍👧‍👦 Message from mom@gmail.com
→ Type: personal | Tag: personal | Priority: 2

🎉 Friend hangout invitation
→ Type: personal | Tag: personal | Priority: 2
```

### Medical
```
🏥 Lab results from lab.com
→ Type: medical | Tag: medical | Priority: 3

💊 Prescription ready from pharmacy
→ Type: medical | Tag: medical | Priority: 3
```

### Bills
```
💰 Bill due today
→ Type: bill | Tag: finance, bill, urgent | Priority: 5

📄 Invoice from vendor
→ Type: invoice | Tag: finance, invoice | Priority: 2-3
```

---

## Key Features

✅ **Automatic Detection** - Works out-of-the-box with keyword matching  
✅ **No Dependencies** - Pure Python, no new packages needed  
✅ **Works Offline** - Doesn't require internet or API calls (unless LLM enabled)  
✅ **Extraction** - Pulls dates, amounts, providers, destinations, etc.  
✅ **Smart Priorities** - Urgent bills/travel get higher priority  
✅ **Gmail Ready** - Tags sync to Gmail for organization  
✅ **Google Sheets** - All data exported for analysis  
✅ **Learns Over Time** - Local intelligence improves accuracy  

---

## Test Results

```
✅ 65 tests passing (100%)
  - 28 core tests (baseline)
  - 16 medical/bill tests
  - 21 new classification tests

⚡ Zero regressions
🚀 Production ready
```

### New Tests Cover:
- 3 travel classifications
- 4 leisure/event classifications
- 4 shopping/order classifications
- 3 work classifications
- 4 personal classifications
- 3 extraction helpers

---

## Documentation

📖 **Read these for more info:**

1. **LEISURE_TRAVEL_GUIDE.md** - Complete user guide with examples
2. **NEW_CLASSIFICATIONS_SUMMARY.md** - Technical details and implementation
3. **GMAIL_TAGS_REFERENCE.md** - All tags and Gmail filter examples
4. **QUICKSTART.md** - Medical & bills quick reference
5. **CODE_CHANGES_REFERENCE.md** - Exact code modifications

---

## Priority Quick Reference

```
Priority 5 (URGENT 🔴)
├─ Bills due today or overdue
├─ Urgent medical (prescriptions, urgent appointments)
└─ Critical work deadlines

Priority 4 (HIGH 🟠)
├─ Bills due within 7 days
├─ Time-sensitive travel (departure imminent)
├─ Important work items
└─ Medical appointments

Priority 3 (MEDIUM 🟡)
├─ Medical records/reference
├─ Regular bills (due >7 days)
├─ Travel confirmations
└─ Work requests

Priority 2 (LOW 🟢)
├─ Personal communications
├─ Leisure/entertainment info
├─ Shopping confirmations
└─ Reference materials

Priority 1 (NOISE ⚪)
└─ Promotions, newsletters, marketing
```

---

## Next Steps

### Today (5 min)
- [ ] Run `python agent.py --dry-run --limit 5`
- [ ] Review a few classifications
- [ ] Read this file

### This Week (15 min)
- [ ] Create Gmail labels from the list above
- [ ] Set up Gmail filters for key categories
- [ ] Test with full email run: `python agent.py`

### This Month (optional)
- [ ] Enable LLM for better accuracy
- [ ] Review Google Sheets results
- [ ] Adjust keywords for your email patterns
- [ ] Set up calendar/task integration

---

## Troubleshooting

### "Email classified wrong"
- Check keywords match the email content
- Enable LLM for more context
- Adjust keyword lists in `plugins/llm_processor.py`

### "No data in Google Sheets"
- Verify Sheets credentials are configured
- Check log output for errors
- Run with `--verbose` flag

### "Tests failing"
- All 65 should pass: `python -m pytest tests/ -v`
- Check Python version: 3.11+
- Verify venv is activated

---

## Support

**Stuck?** Check these files:

- **New features?** → `LEISURE_TRAVEL_GUIDE.md`
- **Gmail setup?** → `GMAIL_TAGS_REFERENCE.md`
- **Code changes?** → `CODE_CHANGES_REFERENCE.md`
- **Tests?** → `tests/test_leisure_travel_classification.py`

---

## Summary

You now have a **powerful, production-ready email classification system** that:

🎯 **Classifies** 8 email categories automatically  
🏷️ **Tags** emails for Gmail organization  
💾 **Extracts** key data to Google Sheets  
📈 **Learns** over time with local intelligence  
⚡ **Works** without any external dependencies  

**Ready to organize your inbox?**

```bash
python agent.py --dry-run --limit 10
```

🎉 **That's it! You're all set.**
