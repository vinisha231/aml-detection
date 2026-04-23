# 08 — The False Positive Problem in AML Detection

## Why False Positives Are the Central Challenge

Every AML system faces an uncomfortable trade-off:

- **Too sensitive** → You flag 10,000 accounts. Your analysts can only review 200 per day. They become exhausted, start dismissing without proper review, and real suspicious activity slips through.
- **Too conservative** → You only flag 50 accounts. You catch the obvious cases but miss sophisticated layering and smurfing.

Real industry statistics make this concrete:

| Metric | Typical Value |
|--------|---------------|
| False positive rate at major banks | **90–99%** |
| Annual SARs filed per analyst | 200–400 |
| Cost of reviewing one alert | $30–$80 |
| Fines for AML failures | $100M–$9B |

The industry spends ~$215 billion annually on AML compliance. **The majority is wasted reviewing false positives.**

---

## Why False Positives Are So Common

### 1. Rules are blunt instruments
A rule like "flag any account with 8+ cash deposits under $10k" catches structured accounts AND legitimate small business owners who just prefer cash.

### 2. Financial activity has high variance
A customer who usually spends $500/month might spend $5,000 in December buying holiday gifts. A velocity rule will fire.

### 3. Base rates make precision hard
Even if your rule has 95% precision (only 5% of flagged accounts are innocent), if only 1% of all accounts are truly suspicious:

```
True positives  = 1,000 suspicious × 0.95 = 950
False positives = 99,000 benign × 0.05   = 4,950

Precision@all = 950 / (950 + 4,950) = 16% !
```

This is the **base rate fallacy** — even good rules produce mostly false positives when suspicious accounts are rare.

---

## How This System Addresses False Positives

### Strategy 1: Weighted Ensemble Scoring

Instead of binary rule triggers, we combine many signals with weights. An account needs MULTIPLE independent signals to score high enough to appear in the analyst's queue.

This is similar to how a doctor diagnoses illness: one symptom (fever) is not conclusive. Fever + cough + oxygen desaturation + chest X-ray changes together point strongly to pneumonia.

**Pile-up bonus:** 3+ independent signals adds bonus points, because coincidences are unlikely. If structuring, velocity, AND cycle detection all fire, the account is almost certainly suspicious.

### Strategy 2: Confidence Calibration

Each signal has a `confidence` value (0–1) that reflects:
- How many times the pattern occurred (5 deposits vs. 15)
- How far the metric is from the threshold
- Historical precision of this rule type

A structuring signal with `confidence=0.9` carries more weight than one with `confidence=0.4`.

### Strategy 3: Analyst Feedback Loop

The `disposition` table tracks every dismiss/escalate decision.
The analytics endpoint computes **False Positive Rate per rule**:

```
FPR(rule_X) = dismissed_accounts_with_rule_X / total_dispositioned_accounts_with_rule_X
```

If `round_number` has FPR = 85%, we know it's a weak signal and should lower its weight. If `graph_cycle` has FPR = 12%, it's highly reliable and should get a higher weight.

This closed feedback loop is what separates mature AML programs from naive rule engines.

### Strategy 4: Risk-Based Prioritisation

Rather than treating all flagged accounts equally, we sort by score and work from the top. Even if the queue has 500 accounts, the top 20 are reviewed exhaustively and are likely real. The bottom 200 may never be reviewed in a busy week, which is acceptable if they're mostly false positives.

---

## Key Metrics to Track

### Precision@K
Of the top K accounts by score, what fraction are truly suspicious?

```python
def precision_at_k(scored_accounts, k):
    top_k = sorted(scored_accounts, key=lambda a: a.risk_score, reverse=True)[:k]
    true_positives = sum(1 for a in top_k if a.is_suspicious)
    return true_positives / k
```

Target: Precision@100 > 60% means 60 of your top 100 accounts are real.

### Recall@K
Of all truly suspicious accounts, how many appear in the top K?

```python
def recall_at_k(scored_accounts, all_suspicious_ids, k):
    top_k_ids = {a.account_id for a in sorted(...)[:k]}
    caught = len(top_k_ids & all_suspicious_ids)
    return caught / len(all_suspicious_ids)
```

### AUC-ROC
Area Under the ROC Curve — measures how well the score separates suspicious from benign. 
- AUC = 0.5: random guessing (no better than a coin flip)  
- AUC = 1.0: perfect separation
- Target: AUC > 0.85 for a production AML system

### False Positive Rate per Rule
Tracked in `backend/database/queries.py::get_false_positive_rate_by_rule()`  
Used to tune signal weights in `scoring_config.py`.

---

## The Human in the Loop

No fully automated AML system is legally acceptable. Regulators require human review of flagged accounts before SAR filing.

The analyst's disposition decision (escalate/dismiss) is itself part of the system:
- Escalated accounts are reviewed again by a senior analyst
- SARs are drafted, reviewed by legal, and filed with FinCEN
- Dismissed accounts are documented with reasons for audit trail

Our `Disposition` table and the disposition API endpoints (`POST /dispositions/{id}`) implement this workflow.

---

## Recommended Reading

- FinCEN Advisory FIN-2014-A005: Structuring and Smurfing  
- FATF Guidance on AML/CFT Risk Management: July 2022  
- "Fighting Financial Crime in the Digital Age" — McKinsey Global Institute  
- Basel Committee: Sound Management of Risks Related to ML/TF (2016)
