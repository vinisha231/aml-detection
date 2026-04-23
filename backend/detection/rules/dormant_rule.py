"""
backend/detection/rules/dormant_rule.py
─────────────────────────────────────────────────────────────────────────────
The DORMANT ACCOUNT WAKEUP detection rule.

What we're looking for:
  An account that had very low activity (< 3 transactions per month)
  for at least 60 days, and then suddenly becomes very active.

Why is this suspicious?
  Legitimate customers don't usually ignore their account for months
  and then suddenly make 50+ transactions. This pattern typically indicates:
  - Account takeover (criminal gained access to someone else's account)
  - Compromised account used as a money mule
  - Account purchased from someone who stopped using it

How is this different from the velocity rule?
  The velocity rule uses Z-scores and compares rates.
  The dormant rule specifically looks for a CATEGORICAL transition:
  from "essentially inactive" to "very active."
  These complement each other — velocity catches gradual acceleration,
  dormant catches sudden activation.
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta
from typing import List, Optional

from .structuring_rule import RuleSignal

# ─── Constants ────────────────────────────────────────────────────────────────

# Period during which the account must be dormant
DORMANCY_CHECK_DAYS    = 90   # look back 90 days for dormancy check
DORMANCY_MAX_TX        = 5    # max transactions during dormancy period to qualify

# "Activation" period — how many days counts as the "burst"
BURST_CHECK_DAYS       = 14

# Minimum transactions in the burst period to flag
BURST_MIN_TX           = 15

SIGNAL_WEIGHT          = 1.5


def check_dormant_wakeup(
    account_id: str,
    transactions: List[dict],
    as_of_date: Optional[datetime] = None
) -> List[RuleSignal]:
    """
    Check if an account shows dormant-then-active wakeup pattern.

    Algorithm:
    1. Look at the DORMANCY PERIOD (90 days ago to 14 days ago).
       If this period had ≥ 6 transactions, account is not dormant.
    2. Look at the BURST PERIOD (last 14 days).
       If this period has ≥ 15 transactions, it's a burst.
    3. If dormant AND burst: flag it.

    Args:
        account_id:   Account to check
        transactions: All transactions involving this account
        as_of_date:   Reference date (defaults to latest transaction)

    Returns:
        List of 0 or 1 RuleSignal objects.
    """

    if not transactions:
        return []

    if as_of_date is None:
        as_of_date = max(tx["transaction_date"] for tx in transactions)

    # ── Define time windows ────────────────────────────────────────────────────
    burst_start    = as_of_date - timedelta(days=BURST_CHECK_DAYS)
    dormancy_end   = burst_start
    dormancy_start = dormancy_end - timedelta(days=DORMANCY_CHECK_DAYS)

    # ── Count transactions in each period ─────────────────────────────────────
    # For this rule, we count ALL transactions (sent AND received)
    # because account takeover affects the whole account activity

    dormancy_tx = [
        tx for tx in transactions
        if (
            dormancy_start <= tx["transaction_date"] < dormancy_end
            and (
                tx["sender_account_id"] == account_id or
                tx["receiver_account_id"] == account_id
            )
        )
    ]

    burst_tx = [
        tx for tx in transactions
        if (
            burst_start <= tx["transaction_date"] <= as_of_date
            and (
                tx["sender_account_id"] == account_id or
                tx["receiver_account_id"] == account_id
            )
        )
    ]

    dormancy_count = len(dormancy_tx)
    burst_count    = len(burst_tx)

    # ── Check dormancy threshold ──────────────────────────────────────────────
    if dormancy_count > DORMANCY_MAX_TX:
        # Account was NOT dormant — this is not a wakeup pattern
        return []

    # ── Check burst threshold ─────────────────────────────────────────────────
    if burst_count < BURST_MIN_TX:
        # Not enough activity to count as a burst
        return []

    # ── Calculate score ────────────────────────────────────────────────────────
    # Scale: 15 tx burst → score 55, 50+ tx burst → score 90
    score = min(90.0, 45.0 + burst_count * 0.9)

    # Confidence: higher if dormancy was longer (more unusual the wakeup)
    # Short dormancy (just 90 days) → lower confidence (maybe seasonal account)
    confidence = min(0.88, 0.55 + (DORMANCY_MAX_TX - dormancy_count) * 0.05 + burst_count * 0.005)

    # ── Evidence string ────────────────────────────────────────────────────────
    evidence = (
        f"Account dormant: only {dormancy_count} transactions in prior {DORMANCY_CHECK_DAYS} days. "
        f"Sudden activation: {burst_count} transactions in last {BURST_CHECK_DAYS} days."
    )

    return [RuleSignal(
        account_id=account_id,
        signal_type="dormant_rule",
        score=round(score, 1),
        weight=SIGNAL_WEIGHT,
        evidence=evidence,
        confidence=round(confidence, 2),
    )]
