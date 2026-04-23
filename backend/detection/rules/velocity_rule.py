"""
backend/detection/rules/velocity_rule.py
─────────────────────────────────────────────────────────────────────────────
The VELOCITY ANOMALY detection rule.

What we're looking for:
  An account's transaction rate in the last 7 days is significantly higher
  than its baseline rate over the previous 30 days.

We use Z-score to measure "how unusual" the current rate is:
  Z = (current_rate - baseline_mean) / baseline_std_dev

Z-score interpretation:
  - Z < 2:  Normal variation (not flagged)
  - Z 2–3:  Somewhat unusual (score ~30–50)
  - Z 3–5:  Very unusual (score ~50–75)
  - Z > 5:  Extremely unusual (score ~75–95)

Why Z-score instead of a simple ratio?
  A ratio (current / baseline) doesn't account for baseline variance.
  An account that normally sends 10 tx/week going to 20 tx/week (ratio 2x)
  is much LESS suspicious than an account that averages 1 tx/month going
  to 50 tx/day (ratio 1500x). Z-score captures this distinction.

Special case: dormant accounts (baseline ≈ 0)
  If baseline is near zero, we can't compute a meaningful Z-score.
  Instead, we use a simpler threshold: if burst count > 20, flag it.
─────────────────────────────────────────────────────────────────────────────
"""

import math
from datetime import datetime, timedelta
from typing import List, Optional

from .structuring_rule import RuleSignal  # reuse the same dataclass

# ─── Constants ────────────────────────────────────────────────────────────────

RECENT_WINDOW_DAYS   = 7   # "current" period — how active is the account NOW
BASELINE_WINDOW_DAYS = 30  # "historical" period — what's the normal rate?
# Note: baseline window starts BEFORE the recent window (no overlap)

# Minimum Z-score to flag
Z_SCORE_THRESHOLD = 2.0

# For dormant accounts: minimum burst count to flag
DORMANT_BURST_THRESHOLD = 20

SIGNAL_WEIGHT = 1.5  # velocity is a good signal but generates more false positives


def check_velocity(
    account_id: str,
    transactions: List[dict],
    as_of_date: Optional[datetime] = None
) -> List[RuleSignal]:
    """
    Check if an account shows unusual transaction velocity.

    Compare recent 7-day transaction count against previous 30-day baseline.
    Flag accounts where recent rate is statistically abnormal.

    Args:
        account_id:   Account to check
        transactions: All transactions involving this account
        as_of_date:   Reference date (defaults to latest transaction date)

    Returns:
        List of 0 or 1 RuleSignal objects.
    """

    # ── Step 1: Establish timeline ────────────────────────────────────────────
    if not transactions:
        return []

    if as_of_date is None:
        as_of_date = max(tx["transaction_date"] for tx in transactions)

    # Define the three time periods:
    # [baseline_start ... baseline_end] [gap] [recent_start ... as_of_date]
    recent_start   = as_of_date - timedelta(days=RECENT_WINDOW_DAYS)
    baseline_end   = recent_start  # baseline ends where recent period starts
    baseline_start = baseline_end - timedelta(days=BASELINE_WINDOW_DAYS)

    # ── Step 2: Count transactions in each period ─────────────────────────────
    # We count transactions WHERE this account is the SENDER
    # (outgoing transactions are more suspicious for velocity patterns)
    sent_recent = [
        tx for tx in transactions
        if (
            tx["sender_account_id"] == account_id
            and recent_start <= tx["transaction_date"] <= as_of_date
        )
    ]

    sent_baseline = [
        tx for tx in transactions
        if (
            tx["sender_account_id"] == account_id
            and baseline_start <= tx["transaction_date"] < baseline_end
        )
    ]

    recent_count   = len(sent_recent)
    baseline_count = len(sent_baseline)

    # ── Step 3: Calculate baseline rate (transactions per day) ───────────────
    # This is the "normal" activity rate for this account
    baseline_rate = baseline_count / BASELINE_WINDOW_DAYS  # tx per day

    # ── Step 4: Calculate recent rate ────────────────────────────────────────
    recent_rate = recent_count / RECENT_WINDOW_DAYS  # tx per day

    # ── Step 5: Handle dormant accounts ──────────────────────────────────────
    # If baseline rate is near zero (dormant account), standard Z-score fails.
    # Use a simpler threshold-based detection instead.
    if baseline_rate < 0.1:  # less than 1 transaction per 10 days = dormant
        if recent_count >= DORMANT_BURST_THRESHOLD:
            # Dormant account suddenly very active — high confidence flag
            score = min(95.0, 60.0 + (recent_count - DORMANT_BURST_THRESHOLD) * 1.0)
            evidence = (
                f"Account was dormant (avg {baseline_rate:.2f} tx/day over {BASELINE_WINDOW_DAYS} days). "
                f"Burst: {recent_count} transactions in last {RECENT_WINDOW_DAYS} days "
                f"({recent_rate:.1f} tx/day)"
            )
            return [RuleSignal(
                account_id=account_id,
                signal_type="velocity_rule",
                score=round(score, 1),
                weight=SIGNAL_WEIGHT,
                evidence=evidence,
                confidence=0.85,
            )]
        else:
            # Dormant with small burst — not suspicious enough
            return []

    # ── Step 6: Calculate Z-score for active accounts ─────────────────────────
    # For a Poisson process (random transaction arrivals), the standard
    # deviation of the rate ≈ sqrt(baseline_rate / BASELINE_WINDOW_DAYS)
    # This is a simplification but works well in practice.

    # Standard deviation of the expected daily rate
    baseline_std = math.sqrt(baseline_rate / BASELINE_WINDOW_DAYS)

    if baseline_std == 0:
        # Can't compute Z-score with zero std dev
        return []

    z_score = (recent_rate - baseline_rate) / baseline_std

    if z_score < Z_SCORE_THRESHOLD:
        # Not statistically unusual
        return []

    # ── Step 7: Calculate score from Z-score ─────────────────────────────────
    # Z=2:  score ≈ 30
    # Z=5:  score ≈ 75
    # Z=10: score ≈ 95
    score = min(95.0, 20.0 + z_score * 7.5)

    confidence = min(0.95, 0.50 + z_score * 0.045)

    # ── Step 8: Evidence string ────────────────────────────────────────────────
    evidence = (
        f"{recent_count} transactions in last {RECENT_WINDOW_DAYS} days "
        f"vs baseline {baseline_count} in prior {BASELINE_WINDOW_DAYS} days "
        f"(Z-score: {z_score:.1f}x above normal; "
        f"recent: {recent_rate:.1f} tx/day, baseline: {baseline_rate:.2f} tx/day)"
    )

    return [RuleSignal(
        account_id=account_id,
        signal_type="velocity_rule",
        score=round(score, 1),
        weight=SIGNAL_WEIGHT,
        evidence=evidence,
        confidence=round(confidence, 2),
    )]
