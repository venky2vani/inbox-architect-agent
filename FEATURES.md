# Features & Classification Guide

Comprehensive reference for all email classification categories, features, and smart detection rules.

---

## Classification Categories

### action_needed (Priority: 3-4)
Emails requiring immediate user action.

**Auto-detected when:**
- Bill/invoice with due date within 7 days
- Payment confirmation required
- Account verification needed
- Deadline approaching
- Medical appointment confirmed
- Action item in meeting notes

**Keywords:** payment, invoice, due, urgent, confirm, verify, action required

**Examples:**
- "Payment Due Tomorrow"
- "Action Required: Verify Identity"
- "Your Account Needs Attention"

---

### reference (Priority: 2)
Informational content for later reading.

**Auto-detected when:**
- Meeting minutes, reports, documentation
- Weekly summaries or newsletters
- Educational content
- Archived articles or documentation
- News updates

**Keywords:** summary, report, minutes, documentation, update, announcement

**Examples:**
- "Weekly Report Summary"
- "Meeting Minutes Available"
- "Documentation Update"

---

### waiting_for (Priority: 2-3)
Emails where you're awaiting a response or action from others.

**Auto-detected when:**
- "I'm waiting for" phrases
- "Pending approval" status
- "Awaiting your response"
- Project status checks
- Approval workflows

**Keywords:** waiting, pending, approval, awaiting, response needed

**Examples:**
- "Pending Your Approval"
- "Awaiting Signature"
- "Status: In Review"

---

### noise (Priority: 1)
Auto-archived promotional/low-value content.

**Auto-detected when:**
- Promotional emails
- Marketing campaigns
- Generic newsletters
- Notifications without substance
- Spam-like content

**Keywords:** discount, offer, sale, limited time, click here, unsubscribe

**Examples:**
- "Discover Must-Haves"
- "Complete Your Profile"
- "One Day Left to Choose"

---

## Smart Categories (Dynamic Labels)

### banking_investment (Priority: 3)
Financial institution alerts and statements.

**Domains:** HDFC Bank, ICICI, Axis, SBI, Kotak, IndusInd, RBL, Federal, IDBI, Wise, TransferWise, PayPal, Revolut, Stripe, Razorpay, PhonePe, Google Pay, CRED, Chase, BoA, Wells Fargo

**Detection:**
- Account statements and alerts
- Transaction confirmations
- Balance updates
- OTP and security alerts
- Credit/debit notifications

**Action Items Extracted:**
- Due amounts and dates
- Card details needing update
- Security actions needed
- Investment updates

---

### subscription (Priority: 2)
Recurring service charges and memberships.

**Streaming Services:** Netflix, Prime Video, Disney+, Hulu, Paramount+, Peacock, Apple TV+, Spotify, YouTube Premium, Twitch

**Regional Services:** AHA OTT, SonyLIV, Hotstar, JioCinema, Zee5, Voot, MXPlayer

**Other Services:** Adobe Creative Cloud, Microsoft 365, GitHub Pro, Dropbox, AWS, Google Cloud

**Detection:**
- Subscription renewal confirmations
- Billing notifications
- Service activation/deactivation
- Membership status changes
- High-cost flagging (>$20/month)

**Tagging:**
- `renews_soon` — Renewal within 30 days
- `renews_week` — Renewal within 7 days
- `expensive` — Cost >$20/month (boosted priority)

---

### shopping (Priority: 2-3)
E-commerce orders and deliveries.

**Domains:** Amazon, Flipkart, BigBasket, Myntra, Ajio, Meesho

**Detection:**
- Order confirmations
- Shipment tracking updates
- Delivery notifications
- Return authorizations
- Order cancellations

**Extracted Data:**
- Order number
- Tracking number
- Delivery date
- Item list

---

### food_delivery (Priority: 2)
Restaurant orders and food service.

**Domains:** Zomato, Swiggy, GrubHub, Doordash, Uber Eats, Deliveroo, FoodPanda

**Detection:**
- Order confirmations
- Delivery tracking
- Restaurant updates
- Loyalty program alerts
- Promotional offers

**Extracted Data:**
- Order number
- Restaurant name
- Delivery time
- Total amount

---

## Medical & Health

### medical (Priority: 3-4)
Healthcare-related communications.

**Auto-detected when:**
- Lab results received
- Prescription ready for pickup
- Appointment confirmations
- Discharge summaries
- Vaccination records
- Insurance claim updates

**Detection Examples:**
- **Lab Results:** "Your lab results are ready", "Test results available"
- **Prescriptions:** "Prescription ready", "Refill available"
- **Appointments:** "Appointment confirmed", "Reminder: Your appointment"
- **Insurance:** "Claim approved", "Prior authorization needed"

**Action Items:**
- Lab result review needed
- Prescription pickup
- Appointment attendance
- Insurance form required

---

## Leisure & Travel

### travel_booking (Priority: 3)
Flight, hotel, and transportation reservations.

**Auto-detected when:**
- Flight booking confirmations
- Hotel reservation details
- Car rental confirmations
- Tour package bookings
- Travel itinerary updates

**Extraction:**
- Confirmation number
- Travel dates
- Passenger/guest names
- Cancellation policy

### entertainment (Priority: 2)
Tickets and event reservations.

**Auto-detected when:**
- Concert/movie tickets
- Sports event tickets
- Theater reservations
- Event reminders
- Ticket transfer notifications

**Extraction:**
- Event name and date
- Seat/ticket numbers
- Venue and time
- Refund policy

---

## Local Intelligence Learning

The system automatically learns classification patterns from LLM decisions.

### How It Works

1. **Feature Extraction**
   - `sender_domain` — Email domain (e.g., `netflix.com`)
   - `sender_email` — Full sender address
   - `subject_keyword` — Words in subject line
   - `body_keyword` — Words in email body

2. **Confidence Scoring**
   - Tracks hits and misses for each pattern
   - Confidence = Hits / (Hits + Misses)
   - Only applies patterns with >75% confidence

3. **Learning from LLM**
   - Every LLM classification updates rules
   - Similar future emails skip LLM (saves cost)
   - Stale rules automatically pruned after 30 days

### Current Performance

- **6,000+ learned rules** across all feature types
- **65-70% confidence average** for body/subject keywords
- **60-70% confidence** for sender-based rules
- **50%+ local hit rate** — Half of emails skip LLM

---

## Dynamic Label System

Pre-configured sender domains for instant classification (49 domains).

### How to Add New Domains

```bash
# Confirm a new pattern
python agent.py --confirm-label payroll.company.com work

# List confirmed labels
cat data/dynamic_labels.json | python -m json.tool

# Reject a pattern
python agent.py --reject-pattern unwanted.domain.com
```

### High-Confidence Patterns

Based on 100% accuracy (3+ samples):
- `alerts@mycardshdfcbank.co` → reference
- `failed-payments@mail.anthropic.com` → action_needed
- `no-reply-*@mail.anthropic.com` → action_needed

---

## Configuration

### Customize Categories

Edit `config.yaml`:

```yaml
processor:
  categories:
    - action_needed
    - waiting_for
    - reference
    - noise
  
  local_intelligence:
    confidence_threshold: 0.75  # Minimum confidence to auto-classify
    min_hits: 3                 # Minimum samples before trusting a rule
```

### Environment Variables

```bash
# LLM provider (default: anthropic)
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Local intelligence learning
export LOCAL_INTELLIGENCE_ENABLED=true
export LOCAL_INTELLIGENCE_CONFIDENCE_THRESHOLD=0.75

# Parallel processing
export PARALLEL_PROCESSING=true
export PARALLEL_MAX_WORKERS=8
export LLM_RATE_LIMIT_DELAY=0.2
```

---

## Performance Tips

### Skip LLM Calls
- Pre-configure domains with `--confirm-label`
- Let system learn from 3-5 samples per pattern
- Check efficiency with `python monitor_efficiency.py`

### Improve Accuracy
- Increase `confidence_threshold` in config (be more conservative)
- Review rejected patterns: `cat data/dynamic_labels.json`
- Use tags for secondary classification (`medical`, `expensive`, `urgent`)

### Speed Up Processing
- Enable parallel processing: `export PARALLEL_PROCESSING=true`
- Set workers: `export PARALLEL_MAX_WORKERS=8`
- Use rate limiting: `export LLM_RATE_LIMIT_DELAY=0.2`
- Expected: 2-4x faster (500 emails in 5 min vs 15 min)

---

## Troubleshooting

**Q: Emails going to LLM even with dynamic labels?**
- Check domain is in `data/dynamic_labels.json`
- Verify sender domain matches exactly (case-insensitive)
- Confirm label was created: `python agent.py --confirm-label <domain> <category>`

**Q: Local hit rate not improving?**
- Need 3+ samples for each pattern before learning
- Check confidence: `python monitor_efficiency.py`
- Manually add high-confidence domains: `--confirm-label`

**Q: High memory or slow parallel processing?**
- Reduce workers: `export PARALLEL_MAX_WORKERS=4`
- Increase rate limit delay: `export LLM_RATE_LIMIT_DELAY=0.5`
- Check API quota limits

**Q: Classifications seem random?**
- Review last 10 LLM outputs: `tail -50 logs/digest.log | grep "LLM RESULT"`
- Check system prompt: `cat prompts/system.txt`
- Verify config categories are spelled correctly

---

## See Also

- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** — Commands and cheatsheet
- **[LEARNING_LOOP.md](LEARNING_LOOP.md)** — Complete workflow guide
- **[PARALLEL_PROCESSING.md](PARALLEL_PROCESSING.md)** — Performance tuning
- **[README.md](README.md)** — Setup and overview
- **[AGENTS.md](AGENTS.md)** — For AI agents working on this project
