# Reading Guide 15 — Know Your Customer (KYC) and Due Diligence in Practice

## What is KYC and why does it exist?

KYC — Know Your Customer — is the process financial institutions use to verify
the identity of their clients and assess the risk they pose.

The fundamental problem: if you don't know who your customer is, you can't
assess whether their transactions are suspicious. A $50,000 wire from a
hedge fund is normal; the same wire from a recently-opened personal account
with no stated income is alarming.

KYC provides the **baseline** against which transactions are evaluated.
Without it, anomaly detection has no reference point.

---

## The Four Core KYC Components

### 1. Customer Identification Program (CIP)

When a customer opens an account, the institution must collect and verify:

- **Legal name** — as it appears on government-issued ID
- **Date of birth** — for individuals
- **Address** — physical address (not PO Box)
- **Identification number** — SSN for US persons; passport/national ID for foreign

Verification methods:
- Documentary: Driver's license, passport, state ID
- Non-documentary: Credit bureaus, public records, knowledge-based authentication

**In our system**: `holder_name`, `account_type`, and `account_id` are simplifications.
Production KYC would add SSN, DOB, address, employment, and income fields.

### 2. Customer Due Diligence (CDD)

Beyond identification, CDD requires understanding:

- What is the customer's **occupation or business**?
- What is the **expected transaction volume and pattern**?
- What is the **source of funds**?
- Does the customer have any **PEP status** or adverse media?

This creates the "expected behavior" profile. When actual behavior deviates
significantly from expected behavior, it triggers enhanced review.

### 3. Beneficial Ownership (BO)

For legal entities (LLCs, corporations, partnerships), identify all natural
persons who:
- Own 25%+ of equity interest, OR
- Exercise significant control over the entity

The Corporate Transparency Act (2024 enforcement) makes this mandatory.
Banks must verify BO information against FinCEN's beneficial ownership database.

### 4. Ongoing Monitoring

KYC isn't one-time — it's continuous. The institution must:
- Periodically re-verify customer information (especially for high-risk customers)
- Monitor transactions against the expected behavior profile
- Update risk classification as the customer relationship evolves

**This is what our detection pipeline implements** — ongoing transaction monitoring
against rules and ML models to detect behavioral deviations.

---

## Risk-Based Approach to CDD

Not all customers need the same level of scrutiny. A risk-based approach
allocates compliance resources efficiently.

### Risk Factors That Increase Customer Risk

**Geographic factors:**
- Customer in or transacting with FATF grey/black list countries
- High-risk jurisdictions (secrecy havens: BVI, Cayman Islands, Delaware for certain uses)
- Mismatch between stated address and transaction geography

**Behavioral factors:**
- Complex, unusual transaction patterns with no clear business purpose
- Large cash transactions inconsistent with business type
- Reluctance to provide KYC information
- Transactions just below reporting thresholds (structuring indicator)

**Customer type factors:**
- Politically Exposed Persons (PEPs) and their families
- High-value customers (HNWIs) with opaque wealth sources
- Non-resident aliens (NRAs) with foreign business structures
- Money service businesses (MSBs) that are themselves AML-regulated entities

### Customer Risk Tiers

| Tier | Description | Review Frequency | Monitoring Level |
|------|-------------|------------------|-----------------|
| Low | Retail customers, stable employment, expected patterns | 3 years | Standard rules |
| Medium | Self-employed, foreign income, frequent large transactions | 18 months | Enhanced rules |
| High | PEPs, offshore entities, adverse media hits | 6 months | Full EDD + manual review |
| Prohibited | OFAC-sanctioned, confirmed criminal activity | N/A | Account closure |

---

## Enhanced Due Diligence (EDD) — when to dig deeper

EDD applies automatically to:
1. **PEPs and their immediate family** — risk of bribery proceeds
2. **Customers in high-risk countries** — risk of sanctions evasion, terrorism finance
3. **Correspondent banking relationships** — where one bank processes for another
4. **Private banking clients** — ultra-high-net-worth with privacy expectations
5. **Customers flagged by initial transaction monitoring** — behavioral triggers

EDD involves:
- Senior management approval to open/maintain the relationship
- Additional identity verification (secondary ID, third-party data)
- Understanding the source of wealth (not just source of funds)
- More frequent transaction monitoring and periodic review
- Documenting the business rationale for unusual transactions

---

## The Role of Customer Context in Alert Scoring

This is where KYC and transaction monitoring intersect.

**Same transaction, different risk scores:**

| Customer profile | Transaction | Risk implication |
|-----------------|-------------|-----------------|
| Import/export business | $200k wire to Hong Kong | Normal — expected behavior |
| Retired individual | $200k wire to Hong Kong | High risk — unexplained |
| New account (2 weeks old) | $50k cash deposit | Very high risk — structuring risk |
| Casino | $50k cash deposit | Lower risk — cash business |

**Our system's limitation**: We generate synthetic accounts with minimal profile
data (`account_type: PERSONAL/BUSINESS`). Production systems have rich profile
data that adjusts alert thresholds per customer.

A more complete system would:
1. Load customer risk tier from KYC database
2. Adjust rule thresholds based on risk tier (stricter for high-risk customers)
3. Apply EDD monitoring for flagged customers automatically
4. Surface KYC profile data in the analyst review screen (our AccountDetailPage)

---

## Red Flags in KYC That Predict AML Risk

**At account opening:**
- Customer provides inconsistent information across different documents
- Customer is reluctant to provide information beyond what's required
- Customer wants to conduct large transactions immediately at account opening
- Business customer can't explain what their business does
- Third party pays the initial deposit

**During the relationship:**
- Customer suddenly changes transaction behavior dramatically
- Customer frequently cancels transactions after inquiring about reporting requirements
- Multiple customers with same address, phone, or IP address
- Customer mentions structuring as an explicit strategy

**Transaction-level red flags:**
- Multiple cash deposits totaling just under $10,000
- Wires immediately followed by counter-wires of the same amount
- Round numbers: $10,000, $25,000, $50,000 (avoid natural amounts)
- Transactions to/from shell company email domains

---

## How KYC Data Would Enhance This System

If we had full KYC data, we could add these detection rules:

1. **Profile deviation rule**: Flag when a customer's actual transaction volume
   exceeds their stated expected volume by more than 2×

2. **Income mismatch rule**: Flag when cumulative deposits exceed stated annual
   income (minus taxes) within a 12-month window

3. **PEP proximity rule**: Elevate risk score for any account transacting with
   a PEP (even indirectly through 1 hop)

4. **Business purpose rule**: For BUSINESS accounts, flag when transaction
   types don't match the stated business purpose (e.g., a bakery receiving
   large wire transfers from shell companies)

5. **Relationship network rule**: Flag customers who share a phone number,
   email domain, or address with other suspicious accounts

---

## Summary

KYC is the foundation that makes transaction monitoring meaningful. Without
customer context, every large transaction looks suspicious; with it, you can
calibrate alerts to flag genuinely anomalous behavior rather than generating
noise that overwhelms compliance teams.

The goal of the AML Detection System is to surface the accounts that
*most warrant* analyst attention — KYC data is what separates a high-conviction
alert from a generic high-value transaction flag.

---

*Next: Read 16 — How Real Transaction Monitoring Systems Work*
