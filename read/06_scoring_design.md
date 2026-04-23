# Scoring System Design — Deep Dive

> This document explains the design choices behind the scoring engine.
> Read this when you want to understand WHY the scoring works the way it does.

---

## The core problem: how do you turn "several suspicious signals" into one number?

Option 1: **Maximum** — take the highest signal score.
  - Problem: ignores all other signals. An account with 5 signals at 60 each
    scores the same as an account with 1 signal at 60.

Option 2: **Average** — take the mean of all signal scores.
  - Problem: many weak signals pull down strong ones. An account with
    10 signals at 40 each averages to 40, same as a genuinely medium-risk account.

Option 3: **Weighted average** — each signal has a weight reflecting its importance.
  - Our choice. Gives higher-quality signals more influence.

Option 4: **Bayesian** — treat each signal as updating a prior probability.
  - More theoretically correct but complex to calibrate.
  - Worth exploring in production systems.

---

## Why weighted average?

Real AML systems use a variant of weighted scoring because:

1. **Explainability** — analysts can see exactly why the score is what it is.
   "Structuring (weight 2.0, score 72) + Velocity (weight 1.5, score 65) = final 69"

2. **Tunability** — compliance teams can adjust weights based on false positive rates.
   If the velocity rule has 80% FPR, reduce its weight from 1.5 to 0.5.

3. **Intuitive** — higher-confidence signals count more. A rule with 0.95 confidence
   contributes more than the same score with 0.50 confidence.

---

## The pile-up bonus

Having 3+ signals is qualitatively different from having 1-2.

Example: An account flags structuring (score 65) AND velocity (score 60) AND
graph_cycle (score 70). Any one of these alone might be a false positive.
All three together is extremely suspicious — money launderers often trigger
multiple patterns simultaneously.

The pile-up bonus adds 3 points per signal beyond the second:
  - 3 signals: +3 points
  - 4 signals: +6 points
  - 5 signals: +9 points
  - 6+ signals: capped at +10 points

This creates a "convergence effect" where multiple weak signals together
produce a stronger alert than the individual signals would suggest.

---

## Weight design rationale

| Signal | Weight | Reasoning |
|--------|--------|-----------|
| structuring_rule | 2.0 | Very specific, low false positive rate, federal crime |
| graph_cycle | 2.0 | Round-tripping is always suspicious, high signal quality |
| graph_community | 1.8 | Shell clusters are very suspicious, low false positives |
| funnel_rule | 1.8 | Fan-in pattern is distinctive and hard to explain legitimately |
| velocity_rule | 1.5 | Good signal but higher false positive rate (seasonal accounts) |
| graph_chain | 1.6 | Layering intermediaries, moderate confidence |
| graph_pagerank | 1.5 | Useful but PageRank can fire on legitimate high-volume accounts |
| dormant_rule | 1.5 | Good signal but can be seasonal or lifestyle change |
| round_number_rule | 0.5 | High false positive rate, only useful as a supporting signal |

---

## Confidence scaling

Each signal's contribution is scaled by its confidence:

```
effective_score = signal.score × signal.confidence
weighted_contribution = effective_score × signal.weight
```

A structuring signal at score=80, confidence=0.95 contributes:
  80 × 0.95 × 2.0 = 152 to the numerator

A round_number signal at score=50, confidence=0.45 contributes:
  50 × 0.45 × 0.5 = 11.25 — much less impact

This means uncertain signals don't drag down the final score too much.

---

## Score calibration

Ideally, a score of X should mean "X% of accounts at this score are genuinely suspicious."
This is called "calibration" and requires real data to achieve properly.

For our synthetic data:
- We know ground truth, so we can check calibration
- Run evaluate.py and look at: for all accounts scoring 70-80, what fraction are dirty?
- If that fraction ≠ 0.75, the scoring is miscalibrated

Full calibration (Platt scaling or isotonic regression) is a good Week 4 extension.

---

## What happens when the pipeline runs twice?

The pipeline is idempotent:
1. Old signals for each account are DELETED before new ones are saved
2. account.risk_score and account.evidence are OVERWRITTEN, not appended

This means you can safely re-run `make detect` and get consistent results.
It's important for production systems — daily scoring should update, not accumulate.
