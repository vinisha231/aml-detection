# Reading Guide 14 — AML Regulations & Compliance Framework

## Why regulations matter for system design

When building an AML detection system, the rules you write aren't arbitrary —
they trace directly back to legal definitions, regulatory guidance, and court-tested
typologies. Understanding the regulatory framework tells you *why* each rule exists
and how to calibrate it correctly.

---

## The Bank Secrecy Act (BSA) — the foundation

Enacted in 1970, the Bank Secrecy Act is the primary US AML law. It requires:

1. **Currency Transaction Reports (CTRs)**: Filed for any cash transaction over $10,000.
   This is why structuring (breaking up transactions to stay below $10k) is itself a crime.

2. **Suspicious Activity Reports (SARs)**: Filed when a financial institution *suspects*
   money laundering, regardless of amount. SARs go to FinCEN and are never disclosed to
   the account holder. Filing a SAR is mandatory; failure to file can result in criminal
   prosecution of the institution.

3. **Record-keeping**: Banks must maintain transaction records for 5 years.
   This is what makes retrospective analysis possible.

---

## FinCEN — Financial Crimes Enforcement Network

FinCEN is a bureau of the US Treasury Department. Its key roles:
- Receives and analyzes BSA reports (CTRs, SARs)
- Issues guidance ("advisories") on emerging typologies
- Maintains the BSA database used by law enforcement

**Key FinCEN advisories to know:**
- Advisory FIN-2014-A007: Cyber-enabled financial crime (BEC, romance scams)
- Advisory FIN-2018-A005: Human trafficking indicators
- Advisory FIN-2021-NTC2: Ransomware indicators
- Advisory FIN-2022-NTC3: Russian sanctions evasion

These advisories literally describe the transaction patterns to look for, making
them excellent training data for rule design.

---

## The Three-Stage AML Model

The classic framework for understanding money laundering:

```
Placement → Integration → Layering
```

**Stage 1 — Placement** (highest risk of detection)
Money enters the financial system. Cash gets deposited, converted to negotiable
instruments, or moved across borders. This is where structuring, smurfing, and
cash-intensive business commingling happen.

Indicators: Large cash deposits, multiple sub-threshold deposits, currency exchange.

**Stage 2 — Layering** (where complexity is introduced)
Multiple transfers through accounts, jurisdictions, and entities to obscure the trail.
Wire transfers, shell companies, trade-based ML, cryptocurrency mixing.

Indicators: Pass-through accounts, round amounts, rapid forwarding, offshore routing.

**Stage 3 — Integration** (hardest to detect)
The money re-enters the legitimate economy, appearing as investment returns,
business income, or real estate. Very hard to detect at the transaction level.

Indicators: Luxury goods purchases, real estate transactions, sudden business revenue.

---

## FATF — Financial Action Task Force

FATF is an intergovernmental body that sets global AML standards. Its 40
Recommendations form the basis of AML law in 200+ jurisdictions.

**FATF Grey List**: Countries with "strategic deficiencies" in AML controls.
Transactions with counterparties in grey-listed countries are high risk.

Current grey list (approximate — check FATF website for current):
Albania, Barbados, Burkina Faso, Cayman Islands, Democratic Republic of Congo,
Haiti, Jamaica, Jordan, Mali, Mozambique, Nigeria, Panama, Philippines, Senegal,
South Africa, Syria, Tanzania, Türkiye, Uganda, UAE, Yemen.

**FATF Black List** (High-Risk Jurisdictions): DPRK (North Korea), Iran, Myanmar.
Enhanced due diligence required; some institutions prohibit transactions entirely.

---

## Customer Due Diligence (CDD) — the Know Your Customer (KYC) framework

AML rules alone aren't enough — you need to know *who* the account holder is
to contextualize their transactions.

**CDD Tiers:**
1. **Standard CDD**: ID verification, understanding the customer's business
2. **Enhanced Due Diligence (EDD)**: For high-risk customers (PEPs, high-risk countries)
3. **Simplified Due Diligence**: For low-risk customers (government accounts, etc.)

**PEPs — Politically Exposed Persons**: Senior government officials, their family
members, and close associates. PEPs receive automatic EDD because they have
elevated risk of bribery and corruption-related laundering.

How this affects detection:
- Transactions involving PEPs should have lower alert thresholds
- Sudden wealth or unexplained income for PEPs is extremely suspicious
- Family member accounts of PEPs get the same treatment

---

## Beneficial Ownership — the shell company problem

A **beneficial owner** is the natural person who ultimately owns or controls a company.
Shell companies can obscure beneficial ownership through chains of holding companies.

The Corporate Transparency Act (2021) now requires US companies to disclose
beneficial ownership to FinCEN. This closes a major gap — before 2024, anyone
could create a US LLC anonymously in Delaware or Wyoming.

Detection implication: Our `shell_company` typology specifically looks for
hub-and-spoke patterns consistent with beneficial ownership obfuscation.

---

## SAR Filing Decision Framework

When should an institution file a SAR? The standard is "knows, suspects, or has
reason to suspect" that a transaction:

1. Involves funds from illegal activity
2. Is designed to evade reporting requirements
3. Has no lawful purpose or is not the type the customer would normally conduct
4. Involves use of the institution to facilitate criminal activity

**Key point**: You don't need proof. Suspicion is enough. This is deliberately
low-threshold because law enforcement has tools to investigate further.

The SAR filing threshold is $5,000 for banks. Below that, filing is discretionary.
For casinos: $3,000. For money service businesses: $2,000.

---

## Sanctions — OFAC

The Office of Foreign Assets Control (OFAC) administers US economic sanctions.
Transactions with sanctioned individuals, entities, or countries are illegal —
full stop. No de minimis threshold.

**SDN List**: Specially Designated Nationals — individuals and entities blocked.
Matching against the SDN list is mandatory and must happen in real time.

Our system doesn't implement OFAC matching (that requires real SDN data),
but in production, OFAC screening would run before any transaction clears.

---

## Enforcement examples — why this matters

**HSBC (2012)**: $1.9B settlement for failing to monitor accounts tied to Mexican
drug cartels. The bank processed $881M for the Sinaloa cartel because its AML
controls were systematically disabled.

**Deutsche Bank (2020)**: $150M fine for failing to flag Jeffrey Epstein's
accounts despite numerous red flags including cash withdrawals structured below
reporting thresholds.

**BitMEX (2022)**: $100M penalty for willfully failing to implement AML controls,
allowing sanctioned countries to use the platform.

**Lesson**: AML isn't bureaucratic compliance — it's a first line of defense against
organized crime, human trafficking, and terrorism financing.

---

## Summary: how regulations map to our detection rules

| Rule | Regulatory basis |
|------|-----------------|
| `structuring_rule` | BSA Section 5324 — Structuring is itself a federal crime |
| `smurfing_rule` | BSA — coordinated structuring by multiple people |
| `velocity_rule` | SAR typology — sudden activity spikes |
| `funnel_rule` | FinCEN advisory on funnel accounts (drug proceeds) |
| `layering_rule` | FATF Recommendation 16 — wire transfer tracking |
| `geographic_rule` | FATF grey/black list countries |
| `shell_company` | Corporate Transparency Act + FATF Recommendation 24 |
| `round_trip_rule` | FinCEN guidance — circular fund flows with no business purpose |

---

*Next: Read 15 — KYC and Customer Due Diligence in Practice*
