# Classification & Tags Guide

This guide describes the email categories, smart tags, dynamic labels, and extraction schemas used by the agent.

## Core Categories

Every email is assigned one of four categories:

| Category | Meaning | Default Priority |
|----------|---------|------------------|
| `action_needed` | Requires your response/action | 3-5 |
| `waiting_for` | You're waiting on someone else | 3 |
| `reference` | Information for your records | 2-3 |
| `noise` | Automated/promotional content | 1 |

### Category Details

#### action_needed (Priority 3-5)
Emails requiring immediate user action.

- Bill/invoice with due date within 7 days
- Payment confirmation required
- Account verification needed
- Deadline approaching
- Medical appointment confirmed
- Prescription ready for pickup
- Action item in meeting notes

Keywords: `payment`, `invoice`, `due`, `urgent`, `confirm`, `verify`, `action required`.

#### waiting_for (Priority 2-3)
Emails where you're awaiting a response or action from others.

- "I'm waiting for" phrases
- "Pending approval" status
- "Awaiting your response"
- Project status checks
- Approval workflows

Keywords: `waiting`, `pending`, `approval`, `awaiting`, `response needed`.

#### reference (Priority: 2)
Informational content for later reading.

- Meeting minutes, reports, documentation
- Weekly summaries or newsletters
- Educational content
- Archived articles or documentation
- News updates
- Lab results and medical records

Keywords: `summary`, `report`, `minutes`, `documentation`, `update`, `announcement`.

#### noise (Priority: 1)
Auto-archived promotional/low-value content.

- Promotional emails
- Marketing campaigns
- Generic newsletters
- Notifications without substance
- Spam-like content

Keywords: `discount`, `offer`, `sale`, `limited time`, `click here`, `unsubscribe`.

## Smart Categories (Dynamic Labels)

The agent recognizes additional domain/keyword-based categories. These are used as secondary tags and may influence category/priority decisions.

### banking_investment (Priority: 3)
Financial institution alerts and statements.

**Domains:** HDFC Bank, ICICI, Axis, SBI, Kotak, IndusInd, RBL, Federal, IDBI, Wise, TransferWise, PayPal, Revolut, Stripe, Razorpay, PhonePe, Google Pay, CRED, Chase, BoA, Wells Fargo.

**Detection:** Account statements and alerts, transaction confirmations, balance updates, OTP and security alerts, credit/debit notifications.

### subscription (Priority: 2)
Recurring service charges and memberships.

**Streaming:** Netflix, Prime Video, Disney+, Hulu, Paramount+, Peacock, Apple TV+, Spotify, YouTube Premium, Twitch.
**Regional:** AHA OTT, SonyLIV, Hotstar, JioCinema, Zee5, Voot, MXPlayer.
**Other:** Adobe Creative Cloud, Microsoft 365, GitHub Pro, Dropbox, AWS, Google Cloud.

**Tagging:**
- `renews_soon` — Renewal within 30 days
- `renews_week` — Renewal within 7 days
- `expensive` — Cost >$20/month (boosted priority)

### shopping (Priority: 2-3)
E-commerce orders and deliveries.

**Domains:** Amazon, Flipkart, BigBasket, Myntra, Ajio, Meesho.

**Detection:** Order confirmations, shipment tracking updates, delivery notifications, return authorizations, order cancellations.

**Extracted Data:** Order number, tracking number, delivery date, item list.

### food_delivery (Priority: 2)
Restaurant orders and food service.

**Domains:** Zomato, Swiggy, GrubHub, Doordash, Uber Eats, Deliveroo, FoodPanda.

**Detection:** Order confirmations, delivery tracking, restaurant updates, loyalty program alerts.

## Extended Document Types

### Medical & Health

| Type | Keywords | Category | Priority | Action |
|------|----------|----------|----------|--------|
| **Lab Results** | lab result, test result, blood work, pathology | reference | 3 | Review results |
| **Prescription** | prescription, rx, refill, medication | action_needed | 3 | Refill or pickup |
| **Appointment** | appointment, consultation, checkup | action_needed | 3 | Confirm/reschedule |
| **Discharge** | discharge summary, discharge note | reference | 3 | Review summary |
| **Vaccination** | vaccination, vaccine, immunization | reference | 3 | Review record |
| **Insurance** | insurance, claim, policy, coverage | reference | 2 | Process claim |
| **Doctor's Note** | doctor's note, medical note, clinical note | reference | 3 | Review note |

**Tags:** `medical`, `health` (prescriptions/appointments also get `action_needed` handling).

### Travel & Leisure

| Type | Keywords | Category | Priority | Extracted |
|------|----------|----------|----------|-----------|
| **Flight** | flight, airline, boarding pass | action_needed/reference | 3 | Confirmation number, dates, passengers |
| **Hotel** | hotel, reservation, accommodation | reference | 2 | Confirmation number, dates, guests |
| **Car Rental** | car rental, vehicle rental | reference | 2 | Confirmation number, dates |
| **Event** | concert, movie, sports, ticket, RSVP, restaurant | reference/action_needed | 2-3 | Event name, date, time, venue |

**Tags:** `travel`, `leisure`.

### Shopping & Orders

| Type | Keywords | Category | Priority | Extracted |
|------|----------|----------|----------|-----------|
| **Order Confirmation** | order confirmation, purchased | reference | 2 | Order number, amount, vendor |
| **Shipment** | shipped, tracking number | reference | 2 | Tracking number |
| **Delivery** | delivered, out for delivery | action_needed | 3 | Delivery date |
| **Return/Refund** | return processed, refund | action_needed | 3 | Refund amount |

**Tags:** `shopping`.

### Work & Personal

| Type | Keywords | Category | Priority |
|------|----------|----------|----------|
| **Work Project** | project, sprint, deadline, deliverable | action_needed | 4 |
| **Collaboration** | review, feedback, pull request | action_needed | 4 |
| **Meeting** | meeting, sync, standup | action_needed | 3 |
| **Personal** | family, friend, social, hobby | reference | 2 |

**Tags:** `work`, `personal`.

## Priority Boosting

| Priority | Meaning | Triggers |
|----------|---------|----------|
| 5 (Urgent) | Immediate action required | Bill overdue/due today, bill due ≤3 days, critical health alerts, urgent deadlines |
| 4 (High) | Time-sensitive | Bills due ≤7 days, important work, imminent travel |
| 3 (Medium) | Regular action needed | Prescriptions, appointments, shopping issues, work requests |
| 2 (Low) | Reference materials | Newsletters, confirmations, records |
| 1 (Noise) | Auto-archive | Promotions, marketing |

## Tag Reference

### Financial
`finance`, `bill`, `payment`, `invoice`, `subscription`, `salary`, `investment`, `tax`, `due-soon`, `expensive`, `renews_soon`, `renews_week`.

### Medical/Health
`medical`, `health`, `urgent` (when time-sensitive).

### Travel & Leisure
`travel`, `leisure`.

### Shopping
`shopping`, `urgent` (when delivery delayed).

### Work/Personal
`work`, `personal`, `urgent` (when deadline near).

### General
`urgent`, `due-soon`.

## Extraction Schemas

Example structures the LLM returns for extracted data:

### Medical
```json
{
  "type": "medical",
  "medical": {
    "report_type": "lab_result|prescription|appointment|discharge|vaccination|health_insurance|doctor_note",
    "date": "YYYY-MM-DD",
    "provider": "hospital/clinic/lab name",
    "visit_date": "YYYY-MM-DD"
  }
}
```

### Bill
```json
{
  "type": "bill",
  "bill": {
    "amount": "$150.00",
    "due_date": "YYYY-MM-DD",
    "provider": "Electric Company Inc"
  }
}
```

### Invoice
```json
{
  "type": "invoice",
  "invoice": {
    "amount": "$1,500.00",
    "due_date": "YYYY-MM-DD",
    "vendor": "Acme Consulting"
  }
}
```

### Travel
```json
{
  "type": "travel",
  "travel": {
    "type": "flight|hotel|car|trip",
    "destination": "string",
    "departure": "YYYY-MM-DD"
  }
}
```

### Event
```json
{
  "type": "event",
  "event": {
    "category": "concert|movie|sports|conference|social|restaurant|other",
    "name": "string",
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "location": "string"
  }
}
```

### Order
```json
{
  "type": "order",
  "order": {
    "amount": "string",
    "vendor": "string",
    "order_number": "string",
    "delivery_date": "YYYY-MM-DD"
  }
}
```

## Gmail Filter Examples

These examples can be applied manually in Gmail to mirror the agent's categories.

### Urgent Bills
```
Matches:
  (subject:bill OR subject:payment due OR subject:due today OR subject:due tomorrow)
Apply label: Financial/Bills
Mark as important: true
```

### Medical Documents
```
Matches:
  from:(doctor@ OR clinic@ OR hospital@ OR lab@ OR pharmacy@)
  OR (subject:lab OR subject:prescription OR subject:appointment OR subject:medical)
Apply label: Medical
```

### Travel Confirmations
```
Matches:
  from:(airlines@ OR flights@ OR bookings@)
  OR subject:flight OR subject:boarding pass
Apply label: Travel/Flights
```

### Work Collaboration
```
Matches:
  (from:company.com OR from:github)
  AND (subject:review OR subject:feedback OR subject:"pull request")
Apply label: Work/Review
Mark as important: true
```

## Configuration

Edit `config.yaml` to customize categories and thresholds:

```yaml
processor:
  categories:
    - action_needed
    - waiting_for
    - reference
    - noise

  local_intelligence:
    confidence_threshold: 0.75
    min_hits: 3
```

See [architecture.md](architecture.md) for details on dynamic labels and local intelligence.
