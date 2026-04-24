"""
backend/utils/amount_utils.py
─────────────────────────────────────────────────────────────────────────────
Utility functions for financial amount analysis.

Why centralise amount utilities?
  Multiple detection rules perform similar calculations on transaction amounts:
  - "Is this amount suspiciously round?"
  - "Does this amount cluster just below a reporting threshold?"
  - "What is the typical amount for this account?"

  Centralising avoids duplication and ensures consistent behavior when these
  calculations are refined based on new typology intelligence.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import math
from statistics import mean, stdev


# ─── CTR threshold analysis ───────────────────────────────────────────────────

# US Currency Transaction Report threshold (must file for cash ≥$10,000)
CTR_THRESHOLD = 10_000.0

# How far below the CTR threshold we consider "structuring zone"
# $9,500–$9,999 = clearly in structuring zone
STRUCTURING_ZONE_FLOOR = 9_500.0


def is_in_structuring_zone(amount: float) -> bool:
    """
    Check if an amount falls in the classic structuring zone ($9,500–$9,999).

    Amounts in this range are below the CTR threshold but large enough that
    the primary purpose of choosing this amount may be to avoid reporting.

    Args:
        amount: Transaction amount in USD.

    Returns:
        True if the amount is in the structuring zone.
    """
    return STRUCTURING_ZONE_FLOOR <= amount < CTR_THRESHOLD


def is_just_below_threshold(
    amount:    float,
    threshold: float = CTR_THRESHOLD,
    margin:    float = 500.0,
) -> bool:
    """
    Check if an amount is just below a reporting threshold.

    This generalizes structuring detection to arbitrary thresholds:
    - CTR threshold ($10,000 for cash)
    - SAR threshold ($5,000 for suspicious activity)
    - Smurfing CTR threshold ($10,000)

    Args:
        amount:    Transaction amount to check.
        threshold: The reporting threshold to check against.
        margin:    How close to the threshold counts as "just below".

    Returns:
        True if the amount is within `margin` below `threshold`.
    """
    return (threshold - margin) <= amount < threshold


# ─── Round number detection ───────────────────────────────────────────────────

def roundness_score(amount: float) -> float:
    """
    Compute a "roundness score" for a transaction amount (0.0–1.0).

    Round numbers (exactly $10,000, $25,000, $50,000) have no natural explanation
    in legitimate transactions. Salary payments, vendor invoices, and purchases
    almost never result in perfectly round dollar amounts.

    Money launderers often use round numbers because they're simple to track
    and easy to split into equal portions.

    Algorithm:
      We check multiple levels of roundness:
      - Divisible by $10,000: very round (1.0)
      - Divisible by $1,000:  round (0.7)
      - Divisible by $500:    somewhat round (0.5)
      - Divisible by $100:    slightly round (0.3)
      - Other: not round (0.0)

    Args:
        amount: Transaction amount in USD.

    Returns:
        Float 0.0 (not round) to 1.0 (maximally round).
    """
    if amount <= 0:
        return 0.0

    # Check from most round to least round
    if amount % 10_000 == 0:
        return 1.0
    if amount % 1_000 == 0:
        return 0.7
    if amount % 500 == 0:
        return 0.5
    if amount % 100 == 0:
        return 0.3

    return 0.0


# ─── Statistical amount analysis ─────────────────────────────────────────────

def amount_z_score(amount: float, amounts: list[float]) -> float | None:
    """
    Compute the Z-score of a transaction amount relative to a list of amounts.

    Z-score tells you how many standard deviations above the mean this amount is.
    Z > 2.5 is statistically rare (top 0.6%). Z > 3 is very rare (top 0.13%).

    Args:
        amount:  The transaction amount to evaluate.
        amounts: A list of reference amounts to compare against.

    Returns:
        The Z-score, or None if there aren't enough amounts to compute it.
    """
    # Need at least 2 amounts to compute a standard deviation
    if len(amounts) < 2:
        return None

    mu  = mean(amounts)
    std = stdev(amounts)

    # If std is 0, all amounts are identical — any different amount is extreme
    if std == 0:
        return float('inf') if amount != mu else 0.0

    return (amount - mu) / std


def total_volume(amounts: list[float]) -> float:
    """
    Sum of all amounts in a list.

    Args:
        amounts: List of transaction amounts.

    Returns:
        Total volume. 0.0 if the list is empty.
    """
    return sum(amounts)


def largest_transaction(amounts: list[float]) -> float:
    """
    The maximum transaction amount.

    Args:
        amounts: List of transaction amounts.

    Returns:
        The largest amount, or 0.0 if the list is empty.
    """
    return max(amounts) if amounts else 0.0
