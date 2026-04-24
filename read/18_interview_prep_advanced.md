# Reading Guide 18 — Advanced Interview Prep: AML Systems Design

## Overview

This guide covers the questions you're most likely to face in technical interviews
for roles involving financial crime detection, compliance engineering, or fintech
data engineering. It builds on Guide 07 (basic interview prep) with systems-design
and ML-focused questions.

---

## Systems Design Questions

### "Design a real-time AML transaction monitoring system"

A strong answer covers all four layers:

**1. Ingestion Layer**
- Apache Kafka for event streaming (millions of transactions/day)
- Each transaction is a JSON event: `{tx_id, sender, receiver, amount, timestamp, type}`
- Kafka partitioned by account_id for ordered processing per account
- Avro schemas with a Schema Registry for backward compatibility

**2. Enrichment Layer**
- Stream processing with Apache Flink or Spark Streaming
- Joins against: customer risk profile, OFAC sanctions list, counterparty history
- Output: enriched transaction with risk context attached

**3. Detection Layer**
- Rule engine: reads enriched events, fires rules, publishes alerts
- ML scoring: XGBoost model reads 50-feature vectors, outputs probability
- Both run in parallel; scores are fused in the ensemble

**4. Alert Management**
- Alerts written to PostgreSQL, indexed by risk score and status
- React dashboard reads from API (FastAPI or Django REST)
- Alert disposition writes back to DB + audit log

**Scalability**: Answer how you'd handle 10× traffic:
- Kafka auto-scales with more partitions
- Rule engine pods scale horizontally (stateless, rules read from config store)
- DB scales with read replicas for the analyst dashboard

---

### "How would you reduce the false positive rate from 30% to 5%?"

This is an operational problem, not just a model problem. Strong answer:

1. **Analyze the FP distribution**: Which rules fire most often on FPs?
   Build a rule-level FP report (we have this in `/analytics/false-positive-rates`).

2. **Raise thresholds on low-precision rules**: If "high_value_rule" fires on 85% FPs,
   its threshold is too low. Raise it from $50k to $100k.

3. **Add context from KYC**: A $100k wire is normal for an import business.
   Condition the rule on customer type (BUSINESS vs. PERSONAL).

4. **Peer grouping**: Compare to similar accounts. A $50k wire from an HNWI is normal;
   from a minimum-wage earner it's suspicious.

5. **ML feedback loop**: Train a binary classifier on analyst dispositions (escalated=1,
   dismissed=0). The model learns which rule combinations actually predict escalation.

6. **Suppression rules**: Explicit whitelist conditions that suppress alerts.
   "Recurring same-amount monthly transfers to same account" = likely direct debit.

---

### "How would you handle 1 billion transactions per month?"

Scale calculation:
- 1B tx/month = 33M/day = 1.4M/hour = 23,000/minute = ~380/second

At 380 tx/sec, a single Python process can't keep up (Python GIL, ~10k/sec for simple logic).

**Solution**:
1. **Kafka**: All transactions go to Kafka (handles millions/sec)
2. **Flink cluster**: 20 workers, each handling 19 tx/sec of enrichment
3. **Rule engine in Go or Rust**: 10× faster than Python for CPU-bound rule evaluation
4. **Pre-computed aggregates**: Don't query the DB for "sum of last 30 days" on every tx.
   Maintain rolling accumulators in Redis (INCRBY for amounts, INCR for counts).
5. **Graph signals**: Run nightly batch (not real-time). NetworkX is too slow for streaming.
6. **PostgreSQL → Cassandra**: For write-heavy alert storage at this scale.

---

## ML-Specific Questions

### "Why not just use a neural network for everything?"

Good reasons to prefer rule-based + ensemble:

1. **Explainability**: Regulations require explanations for adverse decisions.
   "The neural network said so" is not acceptable. Rules produce human-readable evidence.

2. **Labeled data scarcity**: Confirmed money laundering cases are rare and often
   discovered years after the fact. You can't train a good neural network with 100 labels.

3. **Distribution shift**: Criminal behavior evolves faster than training data.
   A rule can be updated immediately when a new typology is identified.
   A neural network needs months of new labeled examples.

4. **Auditability**: Rules are auditable by compliance officers and regulators.
   Black-box models require additional XAI (SHAP, LIME) to explain.

**When to use ML**: Use ML for ranking (which of 10,000 alerts to review first),
not for binary classification (is this suspicious?). The rule engine determines
what's suspicious; ML determines urgency.

---

### "How do you evaluate a model when ground truth is delayed or unavailable?"

This is the AML oracle problem: you only discover true positives when law
enforcement prosecutes months or years later. In the meantime:

1. **Proxy labels**: Use analyst escalation decisions as weak labels.
   Analysts are right ~90% of the time; their decisions are available immediately.

2. **Retrospective evaluation**: When a case is prosecuted, look back and check
   if the system flagged the accounts during the suspicious period.

3. **Synthetic evaluation**: Generate synthetic data with known ground truth
   (exactly what this project does). This gives you clean AUC-ROC without
   waiting for real cases.

4. **Typology coverage testing**: For each known typology, create test cases and
   verify the system flags them (regression testing for detection rules).

5. **External benchmarks**: FINCEN-provided typology examples, academic AML datasets
   (Elliptic Bitcoin dataset, SAML dataset).

---

### "Explain how PageRank is applied to financial crime"

Standard PageRank was designed for web pages. The AML analogy:

| Web concept | AML equivalent |
|-------------|---------------|
| Web page | Bank account |
| Hyperlink | Money transfer (directed) |
| Link importance | Transfer amount (weighted edges) |
| Important page | High-value exit account |
| Spam pages | Low-value mule accounts |

In web search, a page is important if important pages link to it.
In AML, an account is important if accounts with high transaction volume send to it.

Key difference: in web graph, PageRank finds authoritative sources.
In AML graph, PageRank finds the final destination of laundered funds.

---

## Behavioral Questions for AML Roles

### "Tell me about a time you found a false positive / false negative tradeoff"

Frame it with the stakes:
- False positive = analyst time wasted, customer friction (account freezes)
- False negative = laundered funds reach criminals, regulatory penalty for institution

Best answer: "I reduced FPR on the high_value rule by adding a transaction type filter
(cash-only). This dropped FPR from 40% to 12% with no loss in TPR because wire transfers
have different thresholds in the structuring rules already."

### "How would you explain AML detection to a non-technical stakeholder?"

"We look for financial behavior that matches known patterns of money laundering.
It's like a spam filter for financial transactions — we use rules learned from
thousands of documented cases to score how suspicious each account looks.
The scores help our compliance team focus their limited time on the accounts
most likely to need a closer look."

---

## Salary Negotiation Context

For AML/compliance tech roles (2024 market):
- Junior (<2 years): $90k–$120k + bonus
- Mid-level (2–5 years): $130k–$170k + bonus
- Senior (5+ years): $170k–$220k + equity
- Staff/Principal: $220k–$300k+ with significant equity

Compliance technology is specialized and well-compensated because:
1. Regulatory stakes are high (seven-figure fines for failures)
2. Domain knowledge takes time to develop
3. Small talent pool relative to demand
