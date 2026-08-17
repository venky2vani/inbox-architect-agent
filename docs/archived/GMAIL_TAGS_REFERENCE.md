# Gmail Tags & Labels Reference

Complete guide to all available email tags and how to use them in Gmail filters.

---

## Quick Tag List

### Financial Tags
| Tag | Meaning | Gmail Filter | Use Case |
|-----|---------|--------------|----------|
| `finance` | Financial document | `has:label:finance` | All financial items |
| `bill` | Bill/invoice | `subject:bill` | Bills to pay |
| `payment` | Payment-related | `subject:payment` | Payment confirmations |
| `invoice` | Invoice | `subject:invoice` | Vendor invoices |
| `subscription` | Subscription | `subject:subscription` | Recurring charges |
| `salary` | Salary/payroll | `subject:salary` | Pay stubs |
| `investment` | Investment | `subject:investment` | Investment updates |
| `tax` | Tax-related | `subject:tax` | Tax documents |
| `due-soon` | Due within 7 days | Priority 4 | Bills due this week |
| `urgent` | Urgent action needed | Priority 5 | Bills due ≤3 days |

### Medical & Health Tags
| Tag | Meaning | Gmail Filter | Use Case |
|-----|---------|--------------|----------|
| `medical` | Medical document | `has:label:medical` | All medical items |
| `health` | Health-related | `has:label:health` | Health communications |

### Travel & Leisure Tags
| Tag | Meaning | Gmail Filter | Use Case |
|-----|---------|--------------|----------|
| `travel` | Travel document | `has:label:travel` | All travel bookings |
| `leisure` | Entertainment/event | `has:label:leisure` | Events & entertainment |

### Shopping Tags
| Tag | Meaning | Gmail Filter | Use Case |
|-----|---------|--------------|----------|
| `shopping` | Order/purchase | `has:label:shopping` | All shopping items |

### Work Tags
| Tag | Meaning | Gmail Filter | Use Case |
|-----|---------|--------------|----------|
| `work` | Work-related | `has:label:work` | All work items |

### Personal Tags
| Tag | Meaning | Gmail Filter | Use Case |
|-----|---------|--------------|----------|
| `personal` | Personal communication | `has:label:personal` | Personal emails |

### Universal Tags
| Tag | Meaning | Gmail Filter | Use Case |
|-----|---------|--------------|----------|
| `urgent` | Needs immediate action | Priority 5 | High priority items |

---

## Gmail Label Setup

### Create Labels

In Gmail, go to **Settings → Labels → Create new label**:

```
Financial
├── Bills
├── Invoices
├── Subscriptions
└── Taxes

Medical
├── Lab Results
├── Prescriptions
└── Appointments

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
├── Projects
├── Collaboration
└── Assignments

Personal
├── Family
├── Friends
└── Social
```

---

## Gmail Filters

### Financial Filters

#### Bills & Invoices
```
Matches:
  has:attachment OR (subject:bill OR subject:invoice OR subject:payment due)
Apply label: Financial/Bills
Archive: false
```

#### Urgent Bills (Due ≤3 days)
```
Matches:
  (subject:bill OR subject:payment due OR subject:due today OR subject:due tomorrow)
Apply label: Financial/Bills
Mark as important: true
Never send to spam: true
```

#### Subscriptions
```
Matches:
  subject:subscription OR subject:renewal OR subject:renew
Apply label: Financial/Subscriptions
```

#### Tax Documents
```
Matches:
  subject:tax OR subject:1099 OR subject:W2 OR subject:GST
Apply label: Financial/Taxes
```

### Medical Filters

#### Medical Documents
```
Matches:
  from:(doctor@ OR clinic@ OR hospital@ OR lab@ OR pharmacy@)
  OR (subject:lab OR subject:prescription OR subject:appointment OR subject:medical)
Apply label: Medical
Mark as important: true (if urgent)
```

#### Prescriptions
```
Matches:
  subject:prescription OR subject:rx OR subject:refill
  OR from:pharmacy
Apply label: Medical/Prescriptions
Mark as important: true
```

#### Lab Results
```
Matches:
  subject:lab OR subject:results OR subject:pathology
  OR from:(lab@ OR diagnostics@)
Apply label: Medical/Lab Results
```

#### Appointments
```
Matches:
  subject:appointment OR subject:confirmation OR subject:reminder
  AND from:(doctor@ OR clinic@ OR health@)
Apply label: Medical/Appointments
```

### Travel Filters

#### Flight Confirmations
```
Matches:
  from:(airlines@ OR flights@ OR bookings@)
  OR subject:flight OR subject:boarding pass
Apply label: Travel/Flights
```

#### Hotel Bookings
```
Matches:
  from:(hotel@ OR reservations@)
  OR subject:hotel OR subject:accommodation
Apply label: Travel/Hotels
```

#### Car Rentals
```
Matches:
  subject:car rental OR subject:vehicle rental
  OR from:(rental@ OR hertz OR enterprise)
Apply label: Travel/Car Rental
```

### Leisure Filters

#### Event Tickets
```
Matches:
  from:(ticketmaster OR eventbrite OR fandango)
  OR subject:ticket OR subject:event
Apply label: Leisure/Events
```

#### Concert Tickets
```
Matches:
  subject:concert OR subject:show
  OR from:ticketmaster
Apply label: Leisure/Concerts
```

#### Movie Tickets
```
Matches:
  subject:movie OR subject:cinema
  OR from:(fandango OR cinema)
Apply label: Leisure/Movies
```

#### Restaurant Reservations
```
Matches:
  subject:restaurant OR subject:dining reservation
  OR from:(opentable OR resy)
Apply label: Leisure/Restaurants
```

### Shopping Filters

#### Order Confirmations
```
Matches:
  subject:order confirmation OR subject:"thank you for your order"
  OR from:(amazon OR ebay OR shop)
Apply label: Shopping/Orders
```

#### Shipment Tracking
```
Matches:
  subject:shipped OR subject:tracking OR subject:on the way
  OR from:(fedex OR ups OR dhl OR amazon)
Apply label: Shopping/Shipments
```

#### Delivery Notifications
```
Matches:
  subject:delivered OR subject:out for delivery
  OR subject:"will arrive"
Apply label: Shopping/Deliveries
Mark as important: true
```

#### Returns & Refunds
```
Matches:
  subject:return OR subject:refund
  OR subject:exchange
Apply label: Shopping/Returns
```

### Work Filters

#### Projects & Tasks
```
Matches:
  (from:company.com OR from:teammate@company.com)
  AND (subject:project OR subject:sprint OR subject:deadline)
Apply label: Work/Projects
```

#### Code Reviews
```
Matches:
  (from:github OR from:gitlab OR from:bitbucket)
  OR subject:review OR subject:"pull request"
Apply label: Work/Collaboration
Mark as important: true
```

#### Assignments
```
Matches:
  subject:"assigned to you" OR subject:"assigned to me"
  OR subject:"action item"
Apply label: Work/Assignments
Mark as important: true
```

### Personal Filters

#### Family
```
Matches:
  subject:family OR from:(family member email addresses)
Apply label: Personal/Family
```

#### Friends
```
Matches:
  subject:friend OR from:(friend email addresses)
Apply label: Personal/Friends
```

#### Social Groups
```
Matches:
  from:(meetup OR group@ OR community@)
Apply label: Personal/Social
```

---

## Priority-Based Filters

### Urgent Items (Priority 5)
```
Matches:
  subject:urgent OR subject:asap OR subject:ASAP
  OR subject:deadline today OR subject:overdue
Apply label: Urgent
Star: true
Mark as important: true
```

### High Priority (Priority 4)
```
Matches:
  subject:high priority OR subject:important
Apply label: Important
Star: true
```

### Due Soon (Priority 4)
```
Matches:
  subject:"due soon" OR subject:"due this week"
  OR subject:"due by" (within 7 days)
Apply label: Due Soon
```

---

## Advanced Filters

### Combine Multiple Conditions

#### Urgent Financial Items
```
Matches:
  (subject:bill OR subject:invoice OR subject:payment)
  AND (subject:urgent OR subject:overdue OR subject:due today)
Apply label: Urgent Bills
Star: true
Mark as important: true
```

#### Medical with Prescriptions
```
Matches:
  (from:pharmacy OR subject:prescription)
  AND (subject:ready OR subject:pickup)
Apply label: Medical/Urgent
Mark as important: true
```

#### Work Collaboration
```
Matches:
  (from:company.com OR from:github)
  AND (subject:review OR subject:feedback OR subject:"pull request")
Apply label: Work/Review
Mark as important: true
```

### Exclude Filters

#### Skip Newsletters in Personal
```
Matches:
  from:(friend@ OR personal@)
  -from:(newsletter@ OR marketing@)
Apply label: Personal/Authentic
```

#### Shopping without Returns
```
Matches:
  subject:order
  -subject:return
  -subject:refund
Apply label: Shopping/Orders Confirmed
```

---

## Tags by Email Type

### Bills & Payments
- `finance` + `bill` + optional `urgent` or `due-soon`
- Example: `finance`, `bill`, `urgent`

### Medical Documents
- `medical` + `health` + optional `urgent`
- Example: `medical`, `health`

### Travel Bookings
- `travel` + type-specific tag
- Example: `travel`

### Events & Entertainment
- `leisure` + event type
- Example: `leisure`

### Shopping Orders
- `shopping` + optional `urgent` (for delivery issues)
- Example: `shopping`

### Work Items
- `work` + optional `urgent`
- Example: `work`

### Personal Communication
- `personal` + optional `urgent`
- Example: `personal`

---

## Searching by Tags in Gmail

### Search Syntax

Find emails with specific tags:
```
has:label:finance           # All financial items
has:label:medical           # All medical items
has:label:work              # All work items
has:label:urgent            # All urgent items
has:label:travel            # All travel items
has:label:shopping          # All shopping items
has:label:personal          # All personal items
has:label:leisure           # All leisure items
```

### Complex Searches

```
# Bills due this week
(has:label:finance) AND (has:label:bill) AND (has:label:due-soon)

# Urgent medical items
(has:label:medical) AND (has:label:urgent)

# Work collaboration
(has:label:work) AND from:github

# Personal messages from family
(has:label:personal) AND from:mom@gmail.com

# Recent shopping orders
(has:label:shopping) AND newer_than:3d

# Travel with confirmation
(has:label:travel) AND subject:confirmation

# All action items needed
is:unread AND (has:label:finance OR has:label:medical OR has:label:work)
```

---

## Tag Organization Strategy

### By Urgency (Recommended)
1. **Urgent** (immediate action)
2. **Important** (this week)
3. **Todo** (later)
4. **Reference** (for reading)
5. **Archive** (done)

### By Category
1. **Finance** → Bills, Invoices, Subscriptions
2. **Medical** → Prescriptions, Lab Results, Appointments
3. **Travel** → Flights, Hotels, Bookings
4. **Leisure** → Events, Tickets, Restaurants
5. **Shopping** → Orders, Shipments, Returns
6. **Work** → Projects, Reviews, Assignments
7. **Personal** → Family, Friends, Social

### By Priority
- **Priority 5 (Urgent):** Bills due today, medical emergencies, work deadlines
- **Priority 4 (High):** Bills due this week, important work, travel confirmations
- **Priority 3 (Medium):** Medical records, regular work, shopping confirmations
- **Priority 2 (Low):** Reference materials, personal updates, notifications
- **Priority 1 (Noise):** Promotions, newsletters, marketing

---

## Best Practices

1. **Create hierarchy:** Main category → Subcategory
2. **Use consistent naming:** All lowercase, hyphens for spacing
3. **Don't over-label:** Stick to 1-2 primary labels per email
4. **Review regularly:** Check label usefulness monthly
5. **Archive aggressively:** Once action taken, archive
6. **Star important items:** For quick visibility
7. **Use priorities:** Let system assign, modify if needed

---

## Integration with Google Sheets

Once emails are classified and extracted to Sheets:

```
Filter: tags contains "urgent" AND type = "bill"
Sort by: due_date (ascending)
Display: all urgent bills due soonest first

Filter: tags contains "medical" 
Sort by: received_at (descending)
Display: latest medical documents first

Filter: tags contains "work"
Sort by: priority (descending)
Display: highest priority work items first
```

---

## Summary

With these tags and filters, your inbox will be:

✅ **Organized** - Emails sorted by type and urgency  
✅ **Actionable** - Clear priorities and required actions  
✅ **Searchable** - Find anything by tag or combination  
✅ **Automated** - Gmail handles organization for you  
✅ **Integrated** - Tags sync to Google Sheets for analysis  

Start with the pre-built filters above, then customize for your specific needs!
