# Medical & Bill Classification Quick Reference

## Medical Documents Classification

The system now automatically detects and categorizes medical emails.

### Recognized Medical Document Types

| Type | Keywords | Auto-Category | Priority | Action |
|------|----------|---------------|----------|--------|
| **Lab Results** | lab result, test result, blood work, pathology | reference | 3 | Review results |
| **Prescription** | prescription, rx, refill, medication | action_needed | 3 | Refill or pickup |
| **Appointment** | appointment, consultation, checkup | action_needed | 3 | Confirm/reschedule |
| **Discharge** | discharge summary, discharge note | reference | 3 | Review summary |
| **Vaccination** | vaccination, vaccine, immunization | reference | 3 | Review record |
| **Insurance** | insurance, claim, policy, coverage | reference | 2 | Process claim |
| **Doctor's Note** | doctor's note, medical note, clinical note | reference | 3 | Review note |

### Example: Prescription Email
```
From: pharmacy@cvs.com
Subject: Your Prescription is Ready

Body: Your amoxicillin prescription is ready for pickup at CVS.

↓ Classification:
Category: action_needed
Priority: 3 (Medium)
Tags: ["medical", "health"]
Action Item: Refill prescription or contact pharmacy
```

---

## Bill Due Date Classification

Enhanced detection for financial documents with intelligent priority boosting.

### Priority Levels Based on Due Date

| Days Until Due | Priority | Tag | Action |
|---|---|---|---|
| **Overdue / Today** | 5 | urgent | Pay immediately |
| **1-3 days** | 5 | urgent | Pay ASAP |
| **4-7 days** | 4 | due-soon | Schedule payment |
| **8+ days** | 2-3 | (none) | Schedule later |

### Bill Keywords Detected

- "bill", "invoice", "payment"
- "amount due", "balance due"
- "pay by", "due on"
- "overdue", "settle"

### Example: Urgent Bill
```
From: billing@utility.com
Subject: Bill Payment Due Today

Body: Your electricity bill of $150 is due today 2026-08-16.

↓ Classification:
Category: action_needed
Priority: 5 (URGENT)
Tags: ["finance", "bill", "urgent"]
Amount: $150
Provider: electricity company
Due Date: 2026-08-16
Action Item: Pay bill of $150 by 2026-08-16
```

### Example: Bill Due Soon
```
From: billing@internet.com
Subject: Payment Due Notice

Body: Please settle your internet bill of $65 by August 22, 2026.

↓ Classification:
Category: action_needed
Priority: 4 (High)
Tags: ["finance", "bill", "due-soon"]
Amount: $65
Provider: internet company
Due Date: 2026-08-22
Action Item: Pay bill of $65 by 2026-08-22
```

---

## Tagged Emails

### Medical Tag (`"medical"`)
Applied to all medical documents. Use this to:
- Filter medical emails in spreadsheet
- Archive non-urgent medical records
- Create medical document folder in email client

### Health Tag (`"health"`)
Applied alongside "medical" tag. Use this to:
- Create health-related filters
- Set up email rules for health alerts
- Group health-related items together

### Finance Tag (`"finance"`)
Applied to invoices, bills, payments. Includes:
- Bills
- Invoices
- Payments
- Subscriptions
- Salary/payroll
- Investments
- Tax documents

### Urgent Tag (`"urgent"`)
Applied when immediate action needed:
- Bills overdue or due very soon (≤3 days)
- Prescription refills
- Time-sensitive appointments
- Payment overdue notices

---

## Extraction Examples

### Medical: Lab Results
```json
{
  "type": "medical",
  "medical": {
    "report_type": "lab_result",
    "date": "2026-08-16",
    "provider": "Clinical Diagnostics Lab",
    "visit_date": "2026-08-14"
  }
}
```

### Financial: Bill
```json
{
  "type": "bill",
  "bill": {
    "amount": "$150.00",
    "due_date": "2026-08-20",
    "provider": "Electric Company Inc"
  }
}
```

### Financial: Invoice
```json
{
  "type": "invoice",
  "invoice": {
    "amount": "$1,500.00",
    "due_date": "2026-09-15",
    "vendor": "Acme Consulting"
  }
}
```

---

## How It Works

### 1. Detection Phase
- Email subject and body are scanned for keywords
- Medical keywords: "lab", "prescription", "appointment", "vaccination", etc.
- Bill keywords: "invoice", "bill", "payment due", "balance due", etc.

### 2. Extraction Phase
- Amount extracted: Regex patterns match `$X.XX`, `€X,XXX`, etc.
- Due date extracted: Recognizes dates in multiple formats
  - Relative: "due today", "due in 5 days"
  - Absolute: "2026-08-20", "Aug 20, 2026", "20/08/2026"
- Provider extracted: Medical providers, bill issuers

### 3. Categorization Phase
- **Action Needed:** Requires your response
  - Prescriptions needing refill
  - Appointments to confirm
  - Bills needing payment
- **Reference:** Information for your records
  - Lab results
  - Medical records
  - Paid invoice confirmations

### 4. Priority Assignment
- Medical: Default priority 3, escalated for urgent health matters
- Bills: Escalated based on days until due date
  - ≤3 days: Priority 5 (urgent)
  - ≤7 days: Priority 4 (high)
  - >7 days: Priority 2-3 (normal)

### 5. Action Item Generation
**Medical Documents:**
- Prescription: "Refill prescription or contact pharmacy"
- Appointment: "Confirm or reschedule appointment"
- Lab result: "Review [type] from medical provider"

**Financial Documents:**
- With amount & due date: "Pay [provider] bill of [amount] by [date]"
- With due date only: "Settle [provider] by [date]"
- With amount only: "Review [type] of [amount]"

---

## Tips & Best Practices

✅ **DO:**
- Review medical documents promptly (within 24 hours)
- Act on prescriptions and appointments immediately
- Pay bills 2-3 days before due date to ensure processing time
- Use tags to create email filters for recurring medical/bill items

❌ **DON'T:**
- Delay on prescriptions (medication delays can be serious)
- Ignore overdue payment notices
- Archive action_needed medical/financial emails without action
- Assume dates are extracted correctly (always verify in original email)

---

## Filtering Examples

### In Google Sheets
```
Filter for all urgent medical items:
  tags contains "medical" AND priority = 5

Filter for bills due this week:
  extracted_data type = "bill" AND tags contains "due-soon"

Filter for action-needed prescriptions:
  category = "action_needed" AND medical report_type contains "prescription"
```

### In Email Client (Gmail Rules)
```
Medical documents:
  From: (lab@, clinic@, pharmacy@, hospital@, health@, doctor@)
  Label: "Medical"

Bills and Invoices:
  Subject: (invoice, bill, payment due, amount due)
  Label: "Financial"
```

---

## Troubleshooting

### Medical document not detected?
- Check if sender domain suggests medical source
- Verify keywords in subject/body match our detection patterns
- Check if it's tagged as "other" type instead of "medical"

### Bill due date not extracted?
- Verify date format is standard (YYYY-MM-DD, DD/MM/YYYY, or named month)
- Check if "due" or "pay by" keywords are present
- Look for currency amount in email

### Priority seems wrong?
- Bills: Double-check due date calculation
- Medical: Verify if it's urgent health matter (will get priority boost)
- Check if tagged with "urgent" or "due-soon"

---

## Integration with Other Features

### Local Intelligence Learning
- Over time, the system learns from your LLM classifications
- Medical patterns and bill keywords become faster to recognize
- Provider names are cached for faster future detection

### Checkpoint System
- Medical and financial emails are tracked
- Won't be re-processed on subsequent runs
- Can be reset if needed

### Google Workspace Export
- All extracted data stored in Sheets
- Medical provider names and dates indexed
- Bill amounts and due dates easily searchable

