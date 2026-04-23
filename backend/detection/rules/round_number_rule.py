"""
backend/detection/rules/round_number_rule.py
─────────────────────────────────────────────────────────────────────────────
The ROUND NUMBER TRANSACTION detection rule.

What we're looking for:
  An unusually high proportion of transactions at "round" dollar amounts:
  $5,000, $10,000, $25,000, $50,000, $100,000.

Why is this suspicious?
  Real business transactions almost never end in exactly $10,000.00.
  An invoice for services might be $10,247.50, a payroll run $15,623.80, etc.
  Round numbers suggest:
  - Fake invoicing (shell companies invoice for "services" at made-up round amounts)
  - Structured withdrawals (pre-planned amounts)
  - Test transactions (criminals often test accounts with round amounts first)

Important: This rule has a HIGH false positive rate by itself.
  Many legitimate transactions ARE round numbers (rent, loan payments).
  This rule is designed to BOOST the score when combined with other signals,
  not to flag accounts on its own.
  That's why its weight is low (0.5).
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta
from typing import List, Optional

from .structuring_rule import RuleSignal

# ─── Constants ────────────────────────────────────────────────────────────────

LOOKBACK_DAYS = 30

# Minimum number of transactions to analyze (avoid flagging accounts with 1-2 txs)
MIN_TX_TO_ANALYZE = 10

# What fraction of transactions must be "round" to trigger this rule
ROUND_FRACTION_THRESHOLD = 0.60  # 60% or more are round numbers

# A transaction is "suspicious round" if it's a multiple of $1,000 AND ≥ $5,000
ROUND_THRESHOLD    = 5_000.00
ROUND_GRANULARITY  = 1_000.00   # must be a multiple of $1,000

SIGNAL_WEIGHT = 0.5  # LOW weight — this rule generates many false positives


def is_round_number(amount: float) -> bool:
    """
    Check if a transaction amount is a suspicious round number.

    Suspicious = $5,000+ AND exactly divisible by $1,000.

    Args:
        amount: Transaction amount in USD

    Returns:
        True if the amount is a suspicious round number

    Examples:
        is_round_number(10000.00) → True   ($10k exactly)
        is_round_number(9500.00)  → False  (not a multiple of $1,000)
        is_round_number(3000.00)  → False  (below $5,000 threshold)
        is_round_number(50000.00) → True   ($50k exactly)
    """
    if amount < ROUND_THRESHOLD:
        # Small amounts being round is not suspicious (rent, subscriptions)
        return False

    # Check if amount is exactly divisible by ROUND_GRANULARITY
    # We use a small epsilon for floating-point precision
    remainder = amount % ROUND_GRANULARITY
    return remainder < 0.01 or remainder > (ROUND_GRANULARITY - 0.01)


def check_round_numbers(
    account_id: str,
    transactions: List[dict],
    as_of_date: Optional[datetime] = None
) -> List[RuleSignal]:
    """
    Check if an account has an unusually high proportion of round-number transactions.

    This is a SUPPORTING rule — best used in combination with other signals.
    On its own, it has too many false positives to be actionable.

    Args:
        account_id:   Account to check
        transactions: All transactions involving this account
        as_of_date:   Reference date for lookback window

    Returns:
        List of 0 or 1 RuleSignal objects.
    """

    if not transactions:
        return []

    if as_of_date is None:
        as_of_date = max(tx["transaction_date"] for tx in transactions)

    window_start = as_of_date - timedelta(days=LOOKBACK_DAYS)

    # ── Filter to recent transactions where this account was involved ──────────
    recent_tx = [
        tx for tx in transactions
        if (
            window_start <= tx["transaction_date"] <= as_of_date
            and (
                tx["sender_account_id"] == account_id or
                tx["receiver_account_id"] == account_id
            )
        )
    ]

    if len(recent_tx) < MIN_TX_TO_ANALYZE:
        # Too few transactions to make a meaningful judgment
        return []

    # ── Count round number transactions ───────────────────────────────────────
    round_tx = [tx for tx in recent_tx if is_round_number(tx["amount"])]
    total_tx  = len(recent_tx)
    round_fraction = len(round_tx) / total_tx

    if round_fraction < ROUND_FRACTION_THRESHOLD:
        # Not suspicious — most transactions are normal amounts
        return []

    # ── Calculate score ────────────────────────────────────────────────────────
    # Score scales from 20 (60% round) to 60 (100% round)
    # This is intentionally LOW — this rule is a supporting signal only
    score = 20.0 + (round_fraction - ROUND_FRACTION_THRESHOLD) * 100.0
    score = min(60.0, score)

    confidence = 0.45  # inherently lower confidence for this rule

    # ── Evidence ────────────────────────────────────────────────────────────────
    round_amounts = sorted(set(tx["amount"] for tx in round_tx))[:5]  # show top 5
    amounts_str = ", ".join(f"${a:,.0f}" for a in round_amounts)

    evidence = (
        f"{len(round_tx)}/{total_tx} transactions ({round_fraction:.0%}) "
        f"are exact round numbers ≥ ${ROUND_THRESHOLD:,.0f} "
        f"(e.g., {amounts_str})"
    )

    return [RuleSignal(
        account_id=account_id,
        signal_type="round_number_rule",
        score=round(score, 1),
        weight=SIGNAL_WEIGHT,
        evidence=evidence,
        confidence=confidence,
    )]
