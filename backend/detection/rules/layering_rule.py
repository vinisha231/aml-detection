"""
backend/detection/rules/layering_rule.py
─────────────────────────────────────────────────────────────────────────────
Detection rule for Layering — moving money through multiple hops to obscure
its origin.

What is layering?
  After placing dirty money into the banking system, launderers move it
  through a series of accounts to create a confusing trail of transactions.
  Each hop may involve:
    - Wire transfers between banks
    - Conversion to foreign currency
    - Payment to a shell company
    - Withdrawal and re-deposit elsewhere

  The goal: by the time investigators trace the money, it has passed through
  so many accounts that the original source is hard to prove.

How we detect it (rule-based):
  Layering creates a chain graph: A → B → B → C → D → ... → Z
  This rule looks for accounts that:
    1. Receive a large payment from a SINGLE sender
    2. Pass most of that amount onward within 72 hours
    3. The passthrough ratio is 80–115% (small fee taken or added)

  If an account consistently acts as a "pass-through" node, it's suspicious.

Note: The graph chain signal (chain_signal.py) detects this pattern using
      betweenness centrality on the full transaction graph. This rule is a
      simpler, rule-based complement.
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import timedelta
from collections import defaultdict

from backend.detection.rules.base_rule import RuleSignal, get_latest_date


# ─── Constants ───────────────────────────────────────────────────────────────

# How far back to look for layering patterns (in days)
LOOKBACK_DAYS = 30

# An account must receive at least this much to be worth passing through
MIN_INFLOW_AMOUNT = 10_000.0

# How soon after receiving money must the account send it onward?
# Launderers move quickly to avoid detection — hours to a few days
MAX_HOP_HOURS = 72

# How much of the inflow must be passed on? (80%–115% range)
# Below 80%: the account is a recipient, not a pass-through
# Above 115%: the account is adding its own funds (unlikely for laundering)
MIN_PASSTHROUGH_RATIO = 0.80
MAX_PASSTHROUGH_RATIO = 1.15

# Minimum number of pass-through events to flag
MIN_HOP_COUNT = 2

# Weight of this signal in the scoring engine
SIGNAL_WEIGHT = 1.7

# Base score before bonuses
BASE_SCORE = 45.0


def check_layering(account_id: str, transactions: list) -> RuleSignal | None:
    """
    Detect if an account is acting as a pass-through node in a layering chain.

    Algorithm:
      For each large inflow, check if a matching outflow follows within 72 hours.
      A "matching" outflow has amount between 80% and 115% of the inflow.
      If this happens MIN_HOP_COUNT+ times, flag the account.

    Args:
        account_id:   The account being analysed.
        transactions: All transactions for this account (mixed senders/receivers).

    Returns:
        A RuleSignal if the pattern is detected, None otherwise.
    """
    if not transactions:
        return None

    # Determine the analysis window
    latest_date = get_latest_date(transactions)
    cutoff_date = latest_date - timedelta(days=LOOKBACK_DAYS)

    # Separate inflows and outflows within the lookback window
    # Inflow  = account received money (account_id is the receiver)
    # Outflow = account sent money    (account_id is the sender)
    inflows:  list[dict] = []
    outflows: list[dict] = []

    for tx in transactions:
        if tx['transaction_date'] < cutoff_date:
            continue
        if tx.get('transaction_type') not in ('WIRE', 'ACH', 'INTERNAL'):
            # Structuring uses cash — layering uses electronic transfers
            continue
        amount = tx['amount']
        if amount < MIN_INFLOW_AMOUNT:
            continue  # too small to be layering

        if tx['receiver_account_id'] == account_id:
            inflows.append(tx)
        elif tx['sender_account_id'] == account_id:
            outflows.append(tx)

    if not inflows or not outflows:
        return None

    # Sort both lists by date for efficient pairing
    inflows.sort(key=lambda t: t['transaction_date'])
    outflows.sort(key=lambda t: t['transaction_date'])

    # Count how many inflows have a matching outflow within 72 hours
    hop_count = 0
    total_amount_passed = 0.0

    for inflow in inflows:
        inflow_amount = inflow['amount']
        inflow_time   = inflow['transaction_date']
        window_end    = inflow_time + timedelta(hours=MAX_HOP_HOURS)

        # Find outflows that occur after this inflow and within the time window
        for outflow in outflows:
            outflow_time = outflow['transaction_date']
            if outflow_time <= inflow_time:
                continue  # must happen AFTER the inflow
            if outflow_time > window_end:
                break     # sorted, so no more outflows will match

            # Check if the outflow amount is within the passthrough range
            ratio = outflow['amount'] / inflow_amount
            if MIN_PASSTHROUGH_RATIO <= ratio <= MAX_PASSTHROUGH_RATIO:
                hop_count += 1
                total_amount_passed += outflow['amount']
                break  # each inflow can only match one outflow

    if hop_count < MIN_HOP_COUNT:
        return None  # not enough pass-through events

    # ── Score calculation ─────────────────────────────────────────────────────
    # Base score + bonus for:
    #   - More hops (each extra hop adds 10 points)
    #   - Larger total amount passed through (log scale)

    import math
    hop_bonus    = min(30.0, (hop_count - MIN_HOP_COUNT) * 10)
    amount_bonus = min(20.0, math.log10(max(1, total_amount_passed / 100_000)) * 10)
    score        = min(95.0, BASE_SCORE + hop_bonus + amount_bonus)

    # ── Confidence ────────────────────────────────────────────────────────────
    # Higher hop count = higher confidence this is layering
    confidence = min(0.95, 0.5 + hop_count * 0.12)

    # ── Evidence string ───────────────────────────────────────────────────────
    avg_amount = total_amount_passed / hop_count
    evidence = (
        f"Pass-through pattern detected: {hop_count} inflow→outflow pairs "
        f"within 72 hours, avg ${avg_amount:,.0f} per hop, "
        f"total ${total_amount_passed:,.0f} passed through. "
        f"Passthrough ratio {MIN_PASSTHROUGH_RATIO*100:.0f}–"
        f"{MAX_PASSTHROUGH_RATIO*100:.0f}% suggests wire-layering."
    )

    return RuleSignal(
        account_id  = account_id,
        signal_type = 'layering',
        score       = round(score, 1),
        weight      = SIGNAL_WEIGHT,
        evidence    = evidence,
        confidence  = round(confidence, 2),
    )
