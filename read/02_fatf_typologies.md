# FATF Typology Report — Study Notes

> FATF = Financial Action Task Force
> An intergovernmental body that sets global standards for AML/CFT.
> They publish free typology reports — real case studies of how criminals launder money.
> URL: https://www.fatf-gafi.org/en/publications/Methodsandtrends/

---

## What is a "typology"?

A typology is a documented, recurring METHOD of money laundering. FATF collects
real cases from 37 member countries and categorizes them into patterns so that
banks worldwide can train their detection systems to spot them.

Think of typologies as "attack patterns" — just like security has CVE databases,
AML has typology reports.

---

## The six typologies we implement — with real-world context

### 1. Structuring (aka Smurfing)

**Real-world example (from FATF):**
Drug traffickers in Colombia would employ dozens of low-level couriers ("smurfs")
to deposit $9,500 each at different bank branches across a city. Each deposit was
under the $10k reporting threshold. Over 3 days, 50 couriers deposited $475,000
total — far exceeding the threshold, but split to avoid it.

**What our generator simulates:**
- 5–15 deposits per account over 3–14 days
- Each deposit: $9,100–$9,950 (just under the $10k CTR threshold)
- Deposits spread across different "branches" (we randomize which branch field)
- Total amount: $45,000–$150,000

**Detection signal strength:** HIGH — this pattern is very distinctive because
legitimate customers rarely make many near-identical large deposits.

**File:** `backend/generator/typologies/structuring.py`

---

### 2. Layering (aka Transaction Chaining)

**Real-world example (from FATF):**
A criminal places $500,000 into a Hong Kong shell company. The shell immediately
wires $490,000 to a UK shell company (taking a 2% "fee"). The UK company wires
$480,200 to a Swiss account (another 2% fee). The Swiss account splits it into
4 wires to different offshore jurisdictions. By the time investigators trace it,
the chain has 7 hops across 4 countries in 6 hours.

**What our generator simulates:**
- 3–6 intermediate accounts
- Each transfer happens within 1–24 hours of the previous
- Each pass deducts 1–5% (to simulate "fees" or exchange)
- Starting amount: $50,000–$500,000

**Detection signal strength:** MEDIUM — requires graph analysis to spot chains.

**File:** `backend/generator/typologies/layering.py`

---

### 3. Funnel Accounts (Fan-In → Fan-Out)

**Real-world example (from FATF):**
Human trafficking operations in Eastern Europe would collect "fees" from dozens
of victims or clients into one central account (fan-in). Once enough accumulated,
a large wire went to an account in the destination country (fan-out). The central
account is the "funnel" — it has an unusually high ratio of incoming transfers
to outgoing transfers.

**What our generator simulates:**
- 20–80 incoming small transfers ($100–$2,000 each)
- All arriving within a 7-day window
- Followed by 1–3 large outgoing wires (capturing 80–95% of total)
- The funnel account itself may have no other activity

**Detection signal strength:** HIGH — fan-in ratio > 10:1 is very unusual for
legitimate accounts.

**File:** `backend/generator/typologies/funnel.py`

---

### 4. Round-Tripping (Circular Flow / Carousel Fraud)

**Real-world example (from FATF):**
A corrupt official receives a bribe of $200,000. Instead of depositing directly,
they wire it through 3 shell companies (each owned by a different nominee director)
and then back into their own account as an "investment return." The money completes
a full circle, and the official claims it as legitimate business income.

**What our generator simulates:**
- Account A sends to Account B
- Account B sends to Account C (or a chain of 2–4 accounts)
- Eventually, money returns to Account A
- Full cycle completes within 3–21 days
- Each hop slightly reduces the amount (2–8% "fees")

**Detection signal strength:** HIGH — NetworkX cycle detection catches this.

**File:** `backend/generator/typologies/round_trip.py`

---

### 5. Shell Company Clusters (Isolation)

**Real-world example (from FATF):**
A Russian oligarch owned 12 shelf companies, all registered by the same law firm
in Cyprus. The companies only ever transacted with each other — circular invoices
for "consulting services." No external customers or suppliers. The entire cluster
was self-contained, making it hard to determine any legitimate business purpose.

**What our generator simulates:**
- Cluster of 3–6 accounts
- Transactions ONLY between cluster members (no external edges)
- Circular or near-circular flow
- Regular, round-number transactions (suggesting fake invoices)
- Very low variety in transaction descriptions

**Detection signal strength:** HIGH — Louvain community detection isolates clusters.

**File:** `backend/generator/typologies/shell_company.py`

---

### 6. Velocity Anomalies (Dormant Account Activation)

**Real-world example (from FATF):**
A fraudster buys a list of 10,000 compromised account credentials. They log into
dormant accounts and initiate multiple small transfers ($200–$500) to "mule"
accounts. An account that had been silent for 2 years suddenly makes 50 transactions
in 24 hours. This is also seen in account takeover fraud.

**What our generator simulates:**
- Account is dormant (0–2 tx/month) for 60+ days
- Suddenly: 30–100 transactions in 24–72 hours
- Transactions often end at same 1–3 destination accounts
- Small, repeated amounts ($150–$800)

**Detection signal strength:** HIGH — z-score vs 30-day baseline is very obvious.

**File:** `backend/generator/typologies/velocity.py`

---

## Parameters from real FATF reports

These are the actual ranges found in FATF typology reports that we used for
our generator's parameter choices:

| Pattern | Typical duration | Typical amount | Key indicator |
|---------|-----------------|----------------|---------------|
| Structuring | 3–14 days | $45k–$150k total | >5 near-threshold deposits |
| Layering | 6 hours–7 days | $50k–$5M | 3+ account hops |
| Funnel | 7–30 days | Varies widely | Fan-in ratio > 10:1 |
| Round-trip | 3–21 days | $10k–$500k | Cycle completes < 30 days |
| Shell cluster | Ongoing | Regular amounts | 0 external connections |
| Velocity | 24–72 hours | $150–$800 each | 30× above baseline |

---

## Why we mix in 10× benign traffic

Real AML detection operates at very low base rates. In a real bank:
- 1 in 1,000 accounts might be suspicious
- 1 in 10,000 transactions might be suspicious

If you train a system only on dirty data, it looks great (100% precision!) but
would flag every transaction at a real bank. The 10:1 benign ratio gives us
a realistic false positive problem to solve.

---

## Sources

- FATF Money Laundering Typologies Report (2020): https://www.fatf-gafi.org
- FATF Guidance on Shell Companies: https://www.fatf-gafi.org/en/publications/
- US Treasury FinCEN Advisories: https://www.fincen.gov/resources/advisories
- Egmont Group Case Studies: https://egmontgroup.org/library/
