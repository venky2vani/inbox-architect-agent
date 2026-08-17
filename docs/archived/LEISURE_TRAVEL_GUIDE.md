# Extended Email Classification Guide

## Overview

Your inbox agent now automatically classifies emails into **8 major categories**, making it easy to filter and organize messages in Gmail. Beyond medical and bills, you can now automatically detect and tag:

- **Travel** (flights, hotels, car rentals)
- **Leisure/Events** (concerts, movies, sports, restaurants)
- **Shopping** (orders, shipments, deliveries, returns)
- **Work** (projects, collaboration, assignments)
- **Personal** (family, friends, social, hobbies)

---

## Travel Classification

### What Gets Detected

The system automatically identifies travel-related emails:

| Type | Keywords | Detection | Priority |
|------|----------|-----------|----------|
| **Flight** | flight, airline, booking, itinerary, boarding pass | Flight confirmations and bookings | 3 |
| **Hotel** | hotel, resort, check-in, accommodation | Hotel reservations and confirmations | 3 |
| **Car Rental** | car rental, vehicle, pickup, drive | Car rental bookings | 3 |
| **Trip/Vacation** | trip, vacation, itinerary, tour | Travel itineraries and advisories | 2 |

### Examples

**Flight Booking:**
```
From: bookings@lufthansa.com
Subject: Flight Confirmation - New York to Berlin

Extraction:
├─ Type: travel
├─ Travel Type: flight
├─ Destination: Berlin
├─ Tags: ["travel"]
└─ Action: Review travel booking and confirm flight
```

**Hotel Reservation:**
```
From: reservations@marriott.com
Subject: Hotel Reservation Confirmed

Extraction:
├─ Type: travel
├─ Travel Type: hotel
├─ Tags: ["travel"]
└─ Action: Review hotel booking and confirm reservation
```

### Gmail Labels for Travel

Create these filters in Gmail:
```
Label: Travel
Filter: From travel sites (bookings@, reservations@, flights@)
        + Subject contains (confirmation, booking, ticket, reservation)
```

---

## Leisure & Event Classification

### What Gets Detected

The system identifies entertainment and social events:

| Category | Keywords | Example | Priority |
|----------|----------|---------|----------|
| **Concert/Show** | concert, live performance, artist, show | Concert tickets | 2 |
| **Movie** | movie, cinema, film, screening, ticket | Movie tickets | 2 |
| **Sports** | sports, game, match, tournament, team | Game/match tickets | 2 |
| **Restaurant** | restaurant, dining, reservation, table | Restaurant bookings | 2 |
| **Event** | event, registration, RSVP, attending | Conference tickets | 3 |

### Examples

**Concert Ticket:**
```
From: tickets@ticketmaster.com
Subject: Your Concert Tickets - Arctic Monkeys

Extraction:
├─ Type: event
├─ Category: concert
├─ Event Name: Arctic Monkeys
├─ Tags: ["leisure"]
└─ Action: Confirm attendance for concert event
```

**Movie Screening:**
```
From: tickets@fandango.com
Subject: Movie Tickets Confirmation

Extraction:
├─ Type: event
├─ Category: movie
├─ Tags: ["leisure"]
└─ Action: Confirm attendance for movie event
```

**Restaurant Reservation:**
```
From: reservations@opentable.com
Subject: Reservation Confirmed

Extraction:
├─ Type: event
├─ Category: restaurant
├─ Tags: ["leisure"]
└─ Action: Confirm attendance for restaurant event
```

### Gmail Labels for Leisure

```
Label: Events & Leisure
Filter: From ticketing/reservation sites
        + Subject contains (ticket, reservation, booking, event)
```

---

## Shopping & Order Classification

### What Gets Detected

All e-commerce and order-related emails:

| Type | Keywords | Detection | Priority |
|------|----------|-----------|----------|
| **Order Confirmation** | order confirmation, purchased, thank you, order # | New orders | 2 |
| **Shipment** | shipped, tracking number, on the way, package | Tracking updates | 2 |
| **Delivery** | delivered, out for delivery, will arrive | Delivery notifications | 3 |
| **Return/Refund** | return processed, exchange, replacement, refund | Return confirmations | 3 |

### Examples

**Order Confirmation:**
```
From: orders@amazon.com
Subject: Order Confirmation - Your Purchase

Extraction:
├─ Type: order
├─ Order Number: AMZ12345678
├─ Amount: $299.99
├─ Tags: ["shopping"]
└─ Action: Review order details and confirm
```

**Shipment Tracking:**
```
From: shipments@fedex.com
Subject: Your Package Has Shipped

Extraction:
├─ Type: order
├─ Tags: ["shopping"]
├─ Tracking: TRK987654
└─ Action: Review shipment status and track package
```

**Delivery Notification:**
```
From: notifications@ups.com
Subject: Out for Delivery Today

Extraction:
├─ Type: order
├─ Category: delivery
├─ Tags: ["shopping", "urgent"]
├─ Priority: 3
└─ Action: Review delivery status and track package
```

**Return Confirmation:**
```
From: support@amazon.com
Subject: Return Processed

Extraction:
├─ Type: order
├─ Category: return
├─ Refund Amount: $79.99
├─ Tags: ["shopping"]
└─ Action: Review return status and track refund
```

### Priority Rules for Shopping

- Normal orders → Priority 2 (reference)
- Shipment tracking → Priority 2 (reference)
- Delivery issues/urgent → Priority 3-4 (action_needed)
- Returns → Priority 3 (action_needed)

### Gmail Labels for Shopping

```
Label: Shopping & Orders
Filter: From e-commerce (amazon.com, ebay.com, shop@, orders@)
        + Subject contains (order, shipped, delivery, tracking)
```

---

## Work Classification

### What Gets Detected

Work-related emails with clear actions:

| Type | Keywords | Category | Priority |
|------|----------|----------|----------|
| **Project** | project, sprint, deadline, deliverable, task | action_needed | 4 |
| **Collaboration** | review, feedback, pull request, code review, share | action_needed | 4 |
| **Meeting** | meeting, sync, standup, all-hands | action_needed | 3 |
| **Assignment** | assigned, task, action item | action_needed | 4 |

### Examples

**Project Update:**
```
From: project.lead@company.com
Subject: Q4 Project Roadmap

Extraction:
├─ Type: work
├─ Work Type: project
├─ Project Name: Q4 Roadmap
├─ Tags: ["work"]
├─ Priority: 4
└─ Action: Review work task and respond as needed
```

**Code Review Request:**
```
From: dev.lead@company.com
Subject: Code Review Needed - Auth Module

Extraction:
├─ Type: work
├─ Work Type: collaboration
├─ Tags: ["work"]
├─ Priority: 4
└─ Action: Review work task and respond as needed
```

**Task Assignment:**
```
From: manager@company.com
Subject: Task Assigned - User Dashboard

Extraction:
├─ Type: work
├─ Work Type: assignment
├─ Tags: ["work"]
├─ Priority: 4
└─ Action: Review work task and respond as needed
```

### Priority Rules for Work

- Urgent projects/collaboration → Priority 4-5
- Normal work tasks → Priority 4
- FYI/information → Priority 2-3

### Gmail Labels for Work

```
Label: Work & Projects
Filter: From company domain
        + Subject contains (project, review, feedback, assigned, sprint)
```

---

## Personal Classification

### What Gets Detected

Personal communications:

| Type | Keywords | Detection | Priority |
|------|----------|-----------|----------|
| **Family** | family, mom, dad, brother, sister, parent | Family updates | 2 |
| **Friends** | friend, buddy, catch up, hangout, pal | Friend messages | 2 |
| **Social** | party, gathering, meetup, event, group | Social invitations | 2 |
| **Hobbies** | hobby, interest, club, community, group | Hobby group communications | 2 |

### Examples

**Family Email:**
```
From: mom@gmail.com
Subject: Family Dinner This Weekend

Extraction:
├─ Type: personal
├─ Personal Type: family
├─ Tags: ["personal"]
├─ Priority: 2
└─ Action: Review personal message and respond
```

**Friend Hangout:**
```
From: john@gmail.com
Subject: Let's Catch Up

Extraction:
├─ Type: personal
├─ Personal Type: friend
├─ Tags: ["personal"]
├─ Priority: 2
└─ Action: Review personal message and respond
```

**Hobby Group:**
```
From: runners@meetup.com
Subject: Weekly Running Club Meetup

Extraction:
├─ Type: personal
├─ Personal Type: hobby
├─ Tags: ["personal"]
├─ Priority: 2
└─ Action: Review personal message and respond
```

### Gmail Labels for Personal

```
Label: Personal
Filter: Not from company domain
        + Subject contains (personal, family, friend, meet)
        + Exclude work/business keywords
```

---

## All Available Tags

The system now uses these tags for filtering:

### Financial
- `finance`, `bill`, `payment`, `invoice`, `subscription`, `salary`

### Medical/Health
- `medical`, `health`, `urgent` (when time-sensitive)

### Travel & Leisure
- `travel`, `leisure`, `urgent` (when departure imminent)

### Shopping
- `shopping`, `urgent` (when delivery delayed)

### Work
- `work`, `urgent` (when deadline near)

### Personal
- `personal`

### General
- `urgent` (across all categories)
- `due-soon` (for bills/financial)

---

## Category Reference

Email categories determine the default action:

| Category | Meaning | Default Priority |
|----------|---------|------------------|
| `action_needed` | Requires your response/action | 3-5 |
| `waiting_for` | You're waiting on someone else | 3 |
| `reference` | Information for your records | 2-3 |
| `noise` | Automated/promotional content | 1 |

---

## Filtering Examples in Google Sheets

Once extracted to Sheets, you can filter by:

### All Travel
```
extracted_data.tags contains "travel"
```

### All Leisure Events
```
extracted_data.type = "event"
```

### All Shopping Orders
```
extracted_data.type = "order"
```

### All Work Items
```
extracted_data.tags contains "work"
```

### Urgent Items
```
extracted_data.tags contains "urgent"
```

### Personal Communications
```
extracted_data.type = "personal"
```

---

## Configuration

No additional configuration needed! The system works out-of-the-box with:

- **Fallback Heuristics:** Works even without LLM
- **LLM Enhancement:** Improved accuracy when Claude is enabled
- **Local Intelligence:** Learns and improves over time

### To Enable LLM Classification

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your_key_here
python agent.py
```

---

## Test Coverage

✅ **21 New Tests:**
- 3 travel tests (flight, hotel, car)
- 4 leisure tests (concert, movie, sports, restaurant)
- 4 shopping tests (order, shipment, delivery, return)
- 3 work tests (project, collaboration, assignment)
- 4 personal tests (family, friend, social, hobby)
- 3 extraction helper tests

**All 65 tests passing** (44 existing + 21 new) ✅

---

## Quick Reference Chart

### Classification Priority & Tags

```
Travel:     Priority 3    Tags: [travel]
Leisure:    Priority 2    Tags: [leisure]
Shopping:   Priority 2-3  Tags: [shopping]
Work:       Priority 4    Tags: [work]
Personal:   Priority 2    Tags: [personal]
Medical:    Priority 3    Tags: [medical, health]
Bills:      Priority 2-5  Tags: [finance, bill]
```

---

## Troubleshooting

### Email not classified correctly?

1. **Check sender domain** - System uses sender patterns for detection
2. **Check subject and body** - Keywords must be present
3. **Check priority** - All items are captured, just with different priorities
4. **Run dry test** - Test with `python agent.py --dry-run --limit 5`

### Want to exclude a sender?

Add to `LOW_PRIORITY_SENDERS` or `ALWAYS_NOISE_SENDERS`:

```bash
export ALWAYS_NOISE_SENDERS="promotions@,marketing@"
```

### Need more specific rules?

Update keyword lists in `plugins/llm_processor.py`:
- Line 361: `travel_keywords`
- Line 370: `leisure_keywords`
- Line 380: `shopping_keywords`
- Line 389: `work_keywords`
- Line 399: `personal_keywords`

---

## Next Steps

1. **Test with real emails:**
   ```bash
   python agent.py --dry-run --limit 10
   ```

2. **Create Gmail labels** for each category

3. **Set up filters** in Gmail to auto-organize

4. **Enable LLM** for enhanced classification:
   ```bash
   export ANTHROPIC_API_KEY=sk-...
   python agent.py
   ```

5. **Monitor results** in Google Sheets for accuracy

You're all set! 🎉 Your inbox will now be intelligently organized across all major email categories.
