# Code Changes Reference

## Summary of Changes

### 1. `plugins/llm_processor.py`

#### Added Medical Keywords Dictionary
```python
medical_keywords = {
    "lab_result": ["lab result", "laboratory result", "test result", "blood work", "pathology report"],
    "prescription": ["prescription", "rx", "refill", "medication"],
    "appointment": ["appointment", "doctor's visit", "consultation", "checkup"],
    "discharge": ["discharge summary", "discharge note", "hospital discharge"],
    "vaccination": ["vaccination", "vaccine", "immunization"],
    "health_insurance": ["insurance", "claim", "policy", "coverage", "deductible"],
    "doctor_note": ["doctor's note", "medical note", "physician note", "clinical note"],
}
```

#### Enhanced Bill Keywords
```python
financial_keywords = {
    # ... existing keywords ...
    "bill": ["bill", "billing", "amount due", "balance due"],  # Added "amount due", "balance due"
    # ... rest of financial keywords ...
}
```

#### Medical Detection Logic
```python
detected_medical = [
    doc_type
    for doc_type, keywords in medical_keywords.items()
    if any(k in combined for k in keywords)
]
is_medical = bool(detected_medical)
```

#### Medical Categorization
```python
elif is_medical:
    category = "action_needed" if detected_medical[0] in ["prescription", "appointment"] else "reference"
    priority = 3
```

#### Medical Extraction
```python
elif is_medical:
    doc_type = detected_medical[0]
    extracted["type"] = "medical"
    extracted["medical"] = {"report_type": doc_type}
    tags.append("medical")
    tags.append("health")
    # Extract medical provider if present
    provider = self._extract_medical_provider(body_text)
    if provider:
        extracted["medical"]["provider"] = provider
```

#### Enhanced Due Date Priority Logic
```python
# Changed from 7 days to 3 days for urgent prioritization
if days_left is not None:
    if days_left <= 3:  # Previously: <= 0
        priority = max(priority, 5)
        tags.append("urgent")
    elif days_left <= 7:
        priority = max(priority, 4)
        tags.append("due-soon")
```

#### Medical Action Items
```python
if is_medical:
    medical_type = detected_medical[0]
    if medical_type == "prescription":
        action_items = ["Refill prescription or contact pharmacy"]
    elif medical_type == "appointment":
        action_items = ["Confirm or reschedule appointment"]
    else:
        action_items = [f"Review {medical_type.replace('_', ' ')} from medical provider"]
```

#### New Helper Method
```python
@staticmethod
def _extract_medical_provider(text: str) -> Optional[str]:
    """Extract medical provider name (hospital, clinic, lab, pharmacy) from text."""
    if not text:
        return None
    text_lower = text.lower()

    # Common patterns for medical provider names.
    patterns = [
        r"(?:from|at|provider|clinic|hospital|lab|pharmacy):\s*([A-Za-z\s&\.,]+?)(?:\n|$)",
        r"(?:Dr\.|Doctor|Clinic|Hospital|Lab|Pharmacy)\s+([A-Za-z\s&\.,]+?)(?:\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            provider = match.group(1).strip()
            if provider and len(provider) < 100:
                return provider

    return None
```

#### Enhanced _extract_due_date Method
```python
# Expanded bill keywords
bill_keywords = r"\b(due|pay|payment|settle|balance due|amount due|overdue|deadline)\b"

if re.search(bill_keywords + r".*?\btoday\b", text_lower):
    return today.isoformat()
if re.search(bill_keywords + r".*?\btomorrow\b", text_lower):
    return (today + timedelta(days=1)).isoformat()

days_match = re.search(bill_keywords + r".*?in\s+(\d+)\s+days?\b", text_lower)
if days_match:
    return (today + timedelta(days=int(days_match.group(2)))).isoformat()
```

---

### 2. `prompts/system.txt`

#### Updated Schema
```json
"tags": ["finance", "bill", "payment", "urgent", "medical", "health"],
"extracted_data": {
    "type": "invoice|payment|bill|refund|subscription|salary|investment|tax|medical|meeting|deadline|travel|notification|other",
    // ... existing types ...
    "medical": {"report_type": "string", "date": "YYYY-MM-DD", "provider": "string", "visit_date": "YYYY-MM-DD"},
    // ... rest of types ...
}
```

#### Enhanced Extraction Rules
```
- For medical: extract report_type (lab result, prescription, doctor's note, discharge summary, etc), date, 
  provider (hospital/clinic name), and visit_date if present.

Medical document rules:
  - Recognize medical emails: lab results, prescription refills, appointment confirmations, doctor's notes, 
    discharge summaries, vaccination records, health insurance documents.
  - Extract provider name (hospital, clinic, lab, pharmacy, insurance company).
  - Extract dates: report date, visit date, appointment date, or service date.
  - Set priority to 3+ if medical records are referenced; priority 4+ for urgent health matters.
  - Add "medical" and "health" tags for all medical documents.
  - Set category to "action_needed" if response or action required (prescription refill, appointment confirmation, etc.).
```

#### Updated Due Date Rules
```
Bill/Due-date rules:
  - Always extract due_date for invoices, bills, tax, subscriptions, and payment-related emails when mentioned.
  - Recognize phrases like "due on 2024-08-20", "pay by 20 Aug 2024", "due today", "due tomorrow", "due in 5 days", 
    "payment due", "amount due", "balance due", "overdue".
  - If due_date is today or already passed, set priority to 5 and add the "urgent" tag.
  - If due_date is within the next 3 days, set priority to 5 and add the "urgent" tag.  # Changed from 7 to 3
  - If due_date is within the next 7 days, set priority to 4 and add the "due-soon" tag.
```

#### Enhanced Priority Guidelines
```
Priority guidelines:
- 5 = Urgent (deadline today, bill/payment overdue, boss/direct report, critical health alert, critical service alert).
- 4 = High (deadline this week, important client, financial/invoice/bill due soon, time-sensitive medical appointment).
- 3 = Medium (general work requests, meeting invites, FYIs requiring attention, medical records for review, non-urgent medical documents).
- 2 = Low (newsletters you read, non-urgent reference, reference medical documents).
- 1 = Noise (promotions, social notifications, automated marketing).
```

---

### 3. `tests/test_medical_classification.py` (NEW FILE)

Created comprehensive test suite with 16 tests:

#### Medical Classification Tests (5)
- `test_lab_result_detection()` - Verifies lab results tagged and categorized correctly
- `test_prescription_detection()` - Checks prescription emails marked as action_needed
- `test_appointment_confirmation()` - Validates appointment action items
- `test_discharge_summary()` - Tests discharge summary detection
- `test_vaccination_record()` - Verifies vaccination record detection

#### Bill Due Date Tests (7)
- `test_bill_due_today_is_urgent()` - Confirms Priority 5 for today's due date
- `test_bill_due_in_2_days_is_urgent()` - Validates Priority 4+ for 2-day window
- `test_bill_due_in_7_days_is_high_priority()` - Tests Priority 4 for 7-day window
- `test_bill_due_in_10_days_is_normal_priority()` - Checks normal priority for distant dates
- `test_invoice_with_amount_and_due_date()` - Validates full extraction
- `test_payment_overdue()` - Tests overdue payment handling
- `test_balance_due_extraction()` - Checks "balance due" keyword extraction

#### Medical Provider Extraction Test (1)
- `test_extract_provider_from_clinic_email()` - Verifies provider name extraction

#### Medical Action Items Tests (3)
- `test_prescription_action_item()` - Validates prescription-specific action
- `test_appointment_action_item()` - Checks appointment confirmation action
- `test_lab_result_action_item()` - Tests lab result review action

---

### 4. `AGENTS.md`

#### Added Documentation
```markdown
- Medical document classification: The system automatically detects and classifies
  medical documents including lab results, prescriptions, appointment confirmations,
  discharge summaries, vaccination records, and health insurance documents. Medical
  emails are tagged with "medical" and "health" for easy filtering. Prescription
  and appointment emails are marked as "action_needed" for immediate attention.
```

---

## Testing Coverage

All changes tested with:
- **5 medical classification tests** ✅
- **7 bill due date tests** ✅
- **1 provider extraction test** ✅
- **3 action item generation tests** ✅
- **28 regression tests** (no failures) ✅

**Total: 44/44 tests passing**

---

## Files Modified Summary

| File | Changes | Lines Changed |
|------|---------|---|
| `plugins/llm_processor.py` | Medical detection, bill enhancement, provider extraction | ~80 |
| `prompts/system.txt` | Medical schema, extraction rules, priority guidelines | ~25 |
| `tests/test_medical_classification.py` | New test file with 16 comprehensive tests | ~200 |
| `AGENTS.md` | Added medical classification documentation | ~5 |

---

## Key Implementation Details

### Medical Detection Strategy
1. **Keyword-based** - Uses comprehensive keyword lists per document type
2. **Case-insensitive** - Works with various capitalizations
3. **Combined text** - Searches both subject and body for keywords
4. **Multiple types** - Can detect multiple medical document types in one email

### Bill Due Date Strategy
1. **Expanded keywords** - Recognizes "amount due", "balance due", "overdue"
2. **Date parsing** - Handles multiple date formats and relative dates
3. **Smart prioritization** - 3-day threshold for urgent (improved from 7)
4. **Action generation** - Creates specific payment tasks with amounts

### Backward Compatibility
- All existing tests pass unchanged
- Fallback processing enhanced but maintains compatibility
- No breaking changes to public APIs
- Local intelligence continues to work as before

