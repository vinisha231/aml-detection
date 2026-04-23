# Reading Guide 16 — How Real Transaction Monitoring Systems Work

## The production reality vs. our system

Our AML Detector is an educational simulation that demonstrates the core concepts
of a transaction monitoring system (TMS). Real production TMS platforms — Actimize,
Mantas, SAS AML, Temenos Financial Crime Mitigation — have additional complexity
that's worth understanding if you're building toward production.

This guide bridges the gap.

---

## Architecture of a Production TMS

### 1. Data Ingestion Layer

Real-time TMS platforms process millions of transactions per day. The ingestion
layer handles:

**Event streaming**: Kafka or similar message queues receive transaction events
as they happen. Each event is a JSON or Avro payload with 50–200 fields.

**Normalization**: Different core banking systems produce different formats.
The TMS normalizes everything into a canonical transaction schema before processing.

**Deduplication**: Network retries can produce duplicate transaction events.
The TMS must idempotently handle duplicates (using `transaction_id` as the key).

**Enrichment**: Before processing, the transaction is enriched with:
- Customer risk profile (from KYC system)
- Counterparty risk score (from prior analysis)
- Geographic risk (country risk rating)
- Real-time OFAC sanctions screening result

**Our system**: We skip real-time ingestion. The generator creates a static dataset
that the detection pipeline processes in batch. That's fine for learning — but
production needs streaming capability.

### 2. Rule Engine Layer

Rules execute against enriched transactions. Production systems have:

**Rule library**: 200–400 individual rules organized by typology, jurisdiction,
and customer segment. Each rule has:
- Threshold parameters (configurable without code changes)
- A "score" (contribution to the alert score if triggered)
- A "suppress" condition (scenarios where the rule should not fire)
- Business justification (required for audit)

**Parallel execution**: Rules run in parallel across a compute cluster. A single
transaction might touch 50 rules simultaneously.

**Windowed aggregation**: Rules like "sum of deposits in last 30 days" need
pre-computed aggregates. Production systems maintain sliding-window accumulators
in Redis or specialized time-series databases.

**Our system**: We run rules sequentially (or with Python threading) on a full
transaction history. This is much simpler but not scalable to production volumes.

### 3. Scoring & Alert Generation Layer

After rules fire, scores are aggregated into alerts:

**Alert thresholds**: Only transactions/accounts above a certain combined score
generate alerts. Below-threshold events are logged but not surfaced to analysts.

**Alert deduplication**: If an account triggered an alert 3 days ago and the
same rules fire again, the TMS should update the existing alert, not create a new one.

**Alert routing**: Different alert types route to different analyst queues.
High-value structuring might go to a specialized SAR team; unusual geographic
patterns might go to the sanctions team.

**Priority scoring**: Alerts are ranked by urgency (severity × age) within each
queue so analysts work the most important cases first.

**Our system**: We generate a single queue ordered by risk score. Production
would have multiple queues, alert deduplication, and SLA-based prioritization.

### 4. Case Management Layer

This is the analyst-facing UI — our AccountDetailPage is a simplified version.

Production case management includes:
- **Case creation**: Multiple related alerts get bundled into a single case
- **Evidence gathering**: Analyst can pull account history, counterparty data,
  news/adverse media, OFAC screening results, and prior SARs
- **Collaboration**: Multiple analysts can work on a case with threaded comments
- **Decision tracking**: Full audit trail of who did what and when
- **SAR filing integration**: Direct connection to FinCEN's BSA e-filing system

**SAR narrative generation**: Our `scoring_explainer.py` generates simple
explanations. Production systems help analysts write full SAR narratives
in the format FinCEN requires (who, what, when, where, why, how).

### 5. Feedback Loop Layer

This is what makes a TMS improve over time:

**Alert disposition tracking**: When an analyst dismisses or escalates an alert,
that decision is recorded with the analyst's reasoning.

**Model feedback**: Dismissed alerts (false positives) feed back into rule tuning.
If a rule fires on 90% false positives, its weight is reduced or its threshold raised.

**Typology library updates**: When new laundering typologies emerge (e.g., new
crypto-mixing techniques), the typology library is updated and pushed to all rules.

**Our system**: We have disposition tracking (dismiss/escalate) but no automated
feedback loop. A production system would retrain models and adjust rule weights
based on analyst decisions.

---

## Key Performance Metrics for TMS

### False Positive Rate (FPR)
FPR = False Positives / (False Positives + True Negatives)

Industry standard: <5% FPR is considered good. Some institutions target <2%.
High FPR burns analyst capacity and leads to "alert fatigue" — analysts start
dismissing alerts without careful review.

### True Positive Rate / Detection Rate
TPR = True Positives / (True Positives + False Negatives)

This is harder to measure because you don't know what you missed. Proxy measures:
- SAR filing rate (SARs filed / total alerts reviewed)
- Law enforcement referral rate
- Asset recovery rate (how often flagged accounts had actual criminal proceeds)

### Alert-to-SAR Conversion Rate
Industry average: 5–15% of alerts result in a SAR filing.
Below 5% suggests too many false positives (wasting analyst time).
Above 30% might suggest thresholds are too high (missing cases).

### Time-to-Alert (TTA)
How quickly does suspicious activity get flagged after it occurs?
Real-time systems: minutes. Batch systems: hours to days.

For layering and round-trip schemes that complete in 24–48 hours,
a batch system running daily might catch them too late.

### Analyst Throughput
Cases reviewed per analyst per day. Industry average: 15–30 cases/day for complex
cases, 50–100/day for simple threshold-based alerts.

AI-assisted systems can increase throughput by pre-populating evidence summaries
and suggesting likely outcomes based on similar historical cases.

---

## The Alert Fatigue Problem

Perhaps the biggest operational challenge in TMS operations.

**The math of alert fatigue:**
- 100,000 transactions per day
- 2% alert rate = 2,000 alerts per day
- 10 analysts at 100 alerts/day = 1,000 alerts reviewed
- Backlog grows by 1,000 alerts per day
- Within a week: 7,000 alert backlog, most of which are now stale

**Solutions that production systems use:**

1. **Risk-based prioritization**: Work the highest-risk alerts first.
   Accept that low-risk alerts may not be reviewed.

2. **Automated dismissal**: Use ML to automatically dismiss alerts that are
   statistically similar to analyst-dismissed alerts from the past 90 days.

3. **Batch suppression**: If an account triggered the same rule 5 times this month,
   suppress the 6th and create a monthly review task instead.

4. **Threshold tuning**: Quarterly review of rule performance. Raise thresholds
   on rules with >90% FPR. Lower thresholds on rules where investigations reveal
   missed cases.

5. **Peer grouping**: Compare account behavior to peers in the same industry/size.
   A $100k wire is suspicious for a sole proprietor but normal for an importer.

---

## Regulatory Expectations for TMS

Regulators don't prescribe specific detection methods, but they do expect:

1. **Coverage**: The TMS must cover all accounts and transaction types.
   "We don't monitor ACH transactions" is not acceptable.

2. **Documentation**: Every rule must have written justification.
   "Because our vendor included it" is not acceptable.

3. **Testing**: Rules must be tested periodically to verify they still fire correctly.
   Annual lookback testing is common (does the system catch known-bad cases?).

4. **Independence**: The team that manages the TMS should be separate from the
   business line being monitored. Conflicts of interest undermine controls.

5. **Escalation paths**: Clear documentation of who reviews alerts, who approves
   SARs, who handles law enforcement requests.

6. **Records retention**: Alert history, analyst decisions, and SAR filings must
   be retained for 5 years (BSA requirement).

---

## How This System Compares

| Feature | Our AML Detector | Production TMS |
|---------|-----------------|---------------|
| Processing mode | Batch (daily) | Real-time streaming |
| Transaction volume | ~50,000 (simulated) | Millions/day |
| Rule count | 15 rules | 200–400 rules |
| Customer profiles | Minimal | Full KYC data |
| OFAC screening | Not implemented | Real-time |
| SAR filing | Not implemented | Integrated with FinCEN |
| Feedback loop | Manual dispositions only | Automated ML retraining |
| Alert deduplication | Not implemented | Full deduplication |
| Multi-queue routing | Single queue | Multiple specialized queues |

Our system demonstrates the core detection and review concepts. Building toward
production would require the infrastructure described in this guide.

---

*Next: Read 17 — Advanced Graph Analysis for Financial Crime Detection*
