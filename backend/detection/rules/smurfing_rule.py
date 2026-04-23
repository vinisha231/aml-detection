"""
backend/detection/rules/smurfing_rule.py
─────────────────────────────────────────────────────────────────────────────
Detection rule for smurfing — a specific structuring technique where
multiple individuals ("smurfs") each deposit small amounts below the
$10,000 reporting threshold to avoid triggering CTRs (Currency Transaction
Reports).

Smurfing vs. Structuring:
  Structuring: ONE person makes many sub-threshold deposits to ONE account.
  Smurfing:    MANY people (smurfs) each make ONE deposit to ONE account.

  The distinction matters for investigations: structuring involves a single
  suspect, while smurfing is a coordinated ring.

How we detect it:
  1. Account receives many small cash deposits ($2,000–$9,999)
  2. Each deposit comes from a DIFFERENT sender (many unique counterparties)
  3. All deposits occur within a short window (7–30 days)
  4. The total exceeds what multiple sub-threshold amounts would explain

  Key signal: High unique-sender count for cash deposits
  (structuring uses one source; smurfing uses many)

This rule produces a higher weight signal than basic structuring because
coordinated smurfing implies an organized criminal network, not just
one person managing their own cash.

Regulatory reference:
  FinCEN Advisory FIN-2014-A005: Structuring and Smurfing
  FATF Typologies Report 2022, Section 3.1: Placement Phase
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import timedelta
from collections import Counter

from backend.detection.rules.base_rule import RuleSignal, get_latest_date

# ─── Thresholds ──────────────────────────────────────────────────────────────

# Cash deposits in this range are sub-threshold (just below $10k CTR limit)
SMURF_MIN_AMOUNT = 2_000.0
SMURF_MAX_AMOUNT = 9_950.0

# Minimum number of UNIQUE senders making sub-threshold cash deposits
MIN_UNIQUE_SMURFS = 5

# Minimum number of total smurf deposits
MIN_DEPOSIT_COUNT = 7

# How many days to look back
LOOKBACK_DAYS = 30

# Weight — higher than structuring because organized ring is more serious
SIGNAL_WEIGHT = 2.2

BASE_SCORE = 55.0


def check_smurfing(account_id: str, transactions: list) -> RuleSignal | None:
    """
    Detect if this account is receiving coordinated sub-threshold deposits
    from many different senders (smurfing pattern).

    Args:
        account_id:   The receiving account under investigation.
        transactions: All transactions for this account.

    Returns:
        RuleSignal if smurfing pattern detected, None otherwise.
    """
    if not transactions:
        return None

    latest_date = get_latest_date(transactions)
    cutoff      = latest_date - timedelta(days=LOOKBACK_DAYS)

    # Filter to inbound cash deposits in the sub-threshold range within window
    smurf_deposits = []
    for tx in transactions:
        if tx['transaction_date'] < cutoff:
            continue
        if tx.get('receiver_account_id') != account_id:
            continue  # only looking at deposits INTO this account
        if tx.get('transaction_type') not in ('CASH_DEPOSIT',):
            continue  # smurfing uses cash
        amount = tx['amount']
        if not (SMURF_MIN_AMOUNT <= amount <= SMURF_MAX_AMOUNT):
            continue

        smurf_deposits.append(tx)

    if len(smurf_deposits) < MIN_DEPOSIT_COUNT:
        return None

    # Count unique senders
    sender_counts = Counter(tx['sender_account_id'] for tx in smurf_deposits)
    unique_senders = len(sender_counts)

    if unique_senders < MIN_UNIQUE_SMURFS:
        # Too few unique senders — this is plain structuring, not smurfing
        return None

    # ── Score calculation ─────────────────────────────────────────────────────
    total_amount  = sum(tx['amount'] for tx in smurf_deposits)
    deposit_count = len(smurf_deposits)

    # More smurfs = higher score
    smurf_bonus   = min(25.0, (unique_senders - MIN_UNIQUE_SMURFS) * 3.5)
    # Higher deposit count = higher score
    deposit_bonus = min(10.0, (deposit_count - MIN_DEPOSIT_COUNT) * 1.5)

    score = min(97.0, BASE_SCORE + smurf_bonus + deposit_bonus)

    # Confidence scales with number of unique senders (more smurfs = less chance of coincidence)
    confidence = min(0.95, 0.55 + (unique_senders / 20) * 0.35)

    avg_amount = total_amount / deposit_count
    evidence = (
        f"Smurfing pattern: {deposit_count} sub-threshold cash deposits "
        f"(avg ${avg_amount:,.0f}) from {unique_senders} distinct senders "
        f"over {LOOKBACK_DAYS} days. "
        f"Total: ${total_amount:,.0f}. "
        f"Coordinated cash placement by multiple individuals to avoid CTR reporting."
    )

    return RuleSignal(
        account_id  = account_id,
        signal_type = 'smurfing',
        score       = round(score, 1),
        weight      = SIGNAL_WEIGHT,
        evidence    = evidence,
        confidence  = round(confidence, 2),
    )
