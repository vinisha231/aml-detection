# FinCEN SAR Guidance — Study Notes for AML Developers

> FinCEN = Financial Crimes Enforcement Network (US Treasury bureau)
> SAR = Suspicious Activity Report (mandatory filing when you suspect laundering)

---

## What is a SAR?

A SAR is a confidential report that banks MUST file with FinCEN when they detect
transactions that appear suspicious. Banks are legally required to do this under
the Bank Secrecy Act (BSA) of 1970.

Key facts:
- Filing threshold: $5,000 or more if a known suspect; $25,000 for unknown suspects
- Filing deadline: 30 days after detection (60 days if no suspect identified)
- Banks CANNOT tell the customer they filed a SAR (this is called "tipping off")
- SAR data feeds into law enforcement investigations globally

---

## The SAR narrative — what analysts actually write

The most important part of a SAR is the narrative. It must answer:

1. **WHO** — describe each subject (name, DOB, account numbers)
2. **WHAT** — what specific transactions were suspicious
3. **WHEN** — exact dates and times
4. **WHERE** — branch, city, state
5. **WHY** — explain the analytical reasoning (not just "it looked weird")
6. **HOW** — how the suspicious activity was conducted

**Bad narrative (gets kicked back):**
> "Customer made multiple deposits. Activity appeared unusual."

**Good narrative (gets accepted and used):**
> "Subject JOHN DOE (DOB: 01/15/1980, Account #12345) made 9 cash deposits between
> 03/01/2024 and 03/14/2024, totaling $86,425. Individual deposits ranged from $9,100
> to $9,900, all below the $10,000 Currency Transaction Report (CTR) threshold.
> Deposits occurred at 4 different branches, suggesting intentional avoidance of
> reporting requirements (structuring, 31 U.S.C. § 5324)."

---

## The $10,000 threshold — why it matters

The Bank Secrecy Act requires banks to file a **Currency Transaction Report (CTR)**
for any cash transaction over $10,000 in a single day.

**Structuring** (also called "smurfing") is when criminals break up large deposits into
amounts just under $10,000 to avoid triggering this report. This is itself a federal crime.

Red flags for structuring:
- Multiple deposits of $9,000–$9,999 within 1–14 days
- Same amounts repeated at different branches
- Customer seems nervous or asks "is there a limit?"
- Account history shows no prior large cash activity

**Our system detects this in:** `backend/detection/rules/structuring_rule.py`

---

## The five stages of money laundering

Understanding these stages helps you understand why each typology exists:

```
Dirty money
    ↓
1. PLACEMENT — getting cash into the financial system
   (Example: depositing cash through structuring)
    ↓
2. LAYERING — making the money hard to trace
   (Example: moving through shell companies, wire transfers, crypto)
    ↓
3. INTEGRATION — money appears legitimate
   (Example: buying real estate, luxury goods, then selling for "clean" money)
    ↓
Clean-looking money (still proceeds of crime)
```

Most bank-level detection focuses on **Placement** and early **Layering**.

---

## Key regulatory thresholds to memorize

| Threshold | Rule | What triggers it |
|-----------|------|-----------------|
| $10,000   | CTR (31 CFR 1010.311) | Single cash transaction ≥ $10k |
| $5,000    | SAR threshold (known suspect) | Suspicious tx ≥ $5k |
| $25,000   | SAR threshold (unknown suspect) | Suspicious tx ≥ $25k |
| $3,000    | Funds Transfer Rule | Wire transfer record-keeping |

---

## Common SAR filing categories

FinCEN uses standardized activity types. The ones most relevant to our system:

- **Structuring** — intentional avoidance of reporting thresholds
- **BSA/Structuring/Money Laundering** — combined filing
- **Fraud** — various types of account fraud
- **Identity theft** — account takeover
- **Terrorist Financing** — funds linked to designated organizations
- **Unusual Use of Currency** — large/unexpected cash activity

---

## What this means for our code

When we build the evidence string in `scoring.py`, we're essentially writing the
machine-readable equivalent of a SAR narrative:
- The WHAT: which rule triggered
- The WHY: what the specific transactions looked like
- The HOW CONFIDENT: a 0–100 confidence score

The "Disposition" screen in our dashboard (escalate SAR vs. dismiss) mirrors the
analyst workflow at real banks: review → document reasoning → file or clear.

---

## Sources (read these originals)

- FinCEN SAR Activity Review: https://www.fincen.gov/resources/advisories
- BSA Examination Manual: https://www.ffiec.gov/bsa_aml_infobase/
- FATF Guidance on AML: https://www.fatf-gafi.org/en/publications/Fatfrecommendations/
- FinCEN SAR Stats: https://www.fincen.gov/reports/sar-stats
