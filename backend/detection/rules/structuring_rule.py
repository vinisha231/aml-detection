"""
backend/detection/rules/structuring_rule.py
─────────────────────────────────────────────────────────────────────────────
The STRUCTURING detection rule.

What we're looking for:
  ≥5 cash deposits in a 14-day window where each deposit is between
  $8,500 and $10,000 (just under the CTR reporting threshold).

Why this range?
  - $10,000: the CTR threshold (above this triggers mandatory reporting)
  - $8,500: lower bound (below this, deposits are too small to be structuring)
  - Real structurers usually stay in $9,000–$9,900 range

Why 5+ deposits?
  One deposit in this range could be coincidence.
  Five or more in 14 days is statistically very unlikely without intent.

Scoring:
  - 5 deposits: score 40 (possible structuring)
  - 10 deposits: score 70 (likely structuring)
  - 15+ deposits: score 95 (almost certain structuring)
  - Each deposit adds proportionally to the score
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass


# ─── Signal dataclass ─────────────────────────────────────────────────────────
# We use a dataclass instead of a plain dict for type safety.
# Python will automatically create __init__, __repr__, etc.

@dataclass
class RuleSignal:
    """
    Represents one detection signal from one rule for one account.

    This is the standard output format for ALL rule functions.
    The scoring engine reads these and combines them into a final score.
    """
    account_id:  str    # which account triggered this rule
    signal_type: str    # rule name (e.g., "structuring_rule")
    score:       float  # 0-100 score for THIS signal
    weight:      float  # how much this signal counts in final score (default 1.0)
    evidence:    str    # human-readable explanation for the analyst
    confidence:  float  # 0.0 to 1.0 — how certain we are


# ─── Detection constants ──────────────────────────────────────────────────────

CTR_THRESHOLD          = 10_000.00   # federal reporting threshold
STRUCTURING_LOWER      = 8_500.00    # below this, not structuring
STRUCTURING_UPPER      = CTR_THRESHOLD - 0.01  # just under threshold

LOOKBACK_WINDOW_DAYS   = 14         # look at the last 14 days
MIN_DEPOSITS_TO_FLAG   = 5          # minimum deposits to trigger the rule

SIGNAL_WEIGHT          = 2.0        # structuring is a high-confidence rule, weight it higher


def check_structuring(
    account_id: str,
    transactions: List[dict],
    as_of_date: Optional[datetime] = None
) -> List[RuleSignal]:
    """
    Check if an account shows structuring behavior.

    Structuring = multiple cash deposits just under $10k threshold in 14 days.

    Args:
        account_id:   Account ID to check
        transactions: List of ALL transactions for this account
                      (both sent and received)
        as_of_date:   The "current" date for the lookback window.
                      If None, uses the latest transaction date.

    Returns:
        List of RuleSignal objects. Empty list if nothing suspicious found.
        Usually returns 0 or 1 signal (structuring either fires or it doesn't).

    Example output when structuring detected:
        [RuleSignal(
            account_id="ACC_000001",
            signal_type="structuring_rule",
            score=72.5,
            weight=2.0,
            evidence="9 cash deposits avg $9,640 in 14 days (total $86,760)",
            confidence=0.87
        )]
    """

    # ── Step 1: Filter to cash deposits only ─────────────────────────────────
    # Structuring specifically involves cash deposits (not wire transfers, etc.)
    cash_deposits = [
        tx for tx in transactions
        if (
            tx["transaction_type"] == "cash_deposit"
            and tx["receiver_account_id"] == account_id  # must be received, not sent
        )
    ]

    if len(cash_deposits) == 0:
        # No cash deposits at all — structuring impossible
        return []

    # ── Step 2: Determine the lookback window ─────────────────────────────────
    if as_of_date is None:
        # Use the date of the most recent transaction
        as_of_date = max(tx["transaction_date"] for tx in transactions)

    window_start = as_of_date - timedelta(days=LOOKBACK_WINDOW_DAYS)

    # ── Step 3: Find deposits in the lookback window ──────────────────────────
    recent_deposits = [
        tx for tx in cash_deposits
        if window_start <= tx["transaction_date"] <= as_of_date
    ]

    if len(recent_deposits) < MIN_DEPOSITS_TO_FLAG:
        # Too few deposits in the window
        return []

    # ── Step 4: Filter to the structuring amount range ────────────────────────
    structuring_deposits = [
        tx for tx in recent_deposits
        if STRUCTURING_LOWER <= tx["amount"] <= STRUCTURING_UPPER
    ]

    if len(structuring_deposits) < MIN_DEPOSITS_TO_FLAG:
        # Not enough deposits in the suspicious range
        return []

    # ── Step 5: Calculate the score ───────────────────────────────────────────
    # Score scales from 40 (5 deposits) to 95 (15+ deposits)
    # Formula: 40 + (count - 5) * 5.5, capped at 95
    count = len(structuring_deposits)
    base_score = 40.0
    score = min(95.0, base_score + (count - MIN_DEPOSITS_TO_FLAG) * 5.5)

    # ── Step 6: Calculate confidence ─────────────────────────────────────────
    # Confidence is based on how consistently the deposits are in the range
    # All in range = high confidence; some edge cases = lower confidence
    amounts = [tx["amount"] for tx in structuring_deposits]
    avg_amount = sum(amounts) / len(amounts)
    total_amount = sum(amounts)

    # Confidence: higher if amounts cluster tightly near threshold
    # Check: what fraction of deposits are $9,000–$9,999 (the "sweet spot")?
    sweet_spot_count = sum(1 for a in amounts if 9_000 <= a <= 9_999)
    confidence = min(0.98, 0.60 + (sweet_spot_count / count) * 0.38)

    # ── Step 7: Build the evidence string ────────────────────────────────────
    # This is what the analyst reads. Be specific and clear.
    evidence = (
        f"{count} cash deposits avg ${avg_amount:,.0f} "
        f"in {LOOKBACK_WINDOW_DAYS} days "
        f"(total ${total_amount:,.0f}; all under ${CTR_THRESHOLD:,.0f} CTR threshold)"
    )

    # ── Return the signal ────────────────────────────────────────────────────
    return [RuleSignal(
        account_id=account_id,
        signal_type="structuring_rule",
        score=round(score, 1),
        weight=SIGNAL_WEIGHT,
        evidence=evidence,
        confidence=round(confidence, 2),
    )]
