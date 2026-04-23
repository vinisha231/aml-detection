"""
backend/detection/rules/funnel_rule.py
─────────────────────────────────────────────────────────────────────────────
The FUNNEL ACCOUNT detection rule.

What we're looking for:
  An account with a very high "fan-in ratio" — many different senders
  sending small amounts, followed by a few large outgoing transfers.

Metrics we check:
  1. in_degree:     number of UNIQUE senders in last 30 days
  2. out_degree:    number of unique receivers in last 30 days
  3. fan_in_ratio:  in_degree / out_degree (high ratio = funnel pattern)
  4. inflow_total:  total money received
  5. outflow_total: total money sent

Scoring thresholds:
  - in_degree ≥ 20 AND fan_in_ratio ≥ 10: base score 50
  - in_degree ≥ 50: score +20
  - outflow concentrated (1-3 receivers): score +15
  - outflow > 80% of inflow: score +10
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta
from typing import List, Optional

from .structuring_rule import RuleSignal

# ─── Constants ────────────────────────────────────────────────────────────────

LOOKBACK_DAYS         = 30    # analyze last 30 days
MIN_UNIQUE_SENDERS    = 15    # minimum unique senders to be suspicious
MIN_FAN_IN_RATIO      = 5.0   # in_degree / out_degree ratio threshold
SIGNAL_WEIGHT         = 1.8


def check_funnel(
    account_id: str,
    transactions: List[dict],
    as_of_date: Optional[datetime] = None
) -> List[RuleSignal]:
    """
    Check if an account shows funnel (fan-in/fan-out) behavior.

    A funnel account receives from MANY senders but sends to FEW receivers.
    It aggregates money from many sources and forwards it as a lump sum.

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

    # ── Filter to the lookback window ─────────────────────────────────────────
    recent_tx = [
        tx for tx in transactions
        if window_start <= tx["transaction_date"] <= as_of_date
    ]

    if not recent_tx:
        return []

    # ── Separate incoming and outgoing ────────────────────────────────────────
    # Incoming: transactions where this account is the RECEIVER
    incoming = [tx for tx in recent_tx if tx["receiver_account_id"] == account_id]

    # Outgoing: transactions where this account is the SENDER
    outgoing = [tx for tx in recent_tx if tx["sender_account_id"] == account_id]

    # ── Count unique counterparties ───────────────────────────────────────────
    # How many DIFFERENT accounts sent money to this account?
    unique_senders = set(tx["sender_account_id"] for tx in incoming)

    # How many DIFFERENT accounts did this account send to?
    unique_receivers = set(tx["receiver_account_id"] for tx in outgoing)

    in_degree  = len(unique_senders)
    out_degree = len(unique_receivers)

    # ── Check minimum thresholds ──────────────────────────────────────────────
    if in_degree < MIN_UNIQUE_SENDERS:
        # Not enough unique senders to be a funnel
        return []

    # ── Calculate fan-in ratio ────────────────────────────────────────────────
    # Prevent division by zero
    if out_degree == 0:
        # Never sent anything out? Could be early-stage funnel.
        fan_in_ratio = float("inf")
    else:
        fan_in_ratio = in_degree / out_degree

    if fan_in_ratio < MIN_FAN_IN_RATIO:
        # Ratio too low — not a funnel
        return []

    # ── Calculate amounts ─────────────────────────────────────────────────────
    inflow_total  = sum(tx["amount"] for tx in incoming)
    outflow_total = sum(tx["amount"] for tx in outgoing)

    # ── Calculate score ────────────────────────────────────────────────────────
    score = 50.0  # base score for passing minimum thresholds

    # Bonus for very high sender count
    if in_degree >= 50:
        score += 20.0
    elif in_degree >= 30:
        score += 10.0

    # Bonus for very concentrated outflow (few receivers = more suspicious)
    if out_degree <= 2:
        score += 15.0
    elif out_degree <= 5:
        score += 8.0

    # Bonus for high outflow fraction (most incoming money is immediately forwarded)
    if inflow_total > 0:
        outflow_fraction = outflow_total / inflow_total
        if outflow_fraction >= 0.80:
            score += 10.0

    score = min(92.0, score)

    # ── Confidence based on the quality of the signal ─────────────────────────
    confidence = min(0.90, 0.50 + (in_degree / 100) * 0.40)

    # ── Evidence string ────────────────────────────────────────────────────────
    outflow_pct = (outflow_total / inflow_total * 100) if inflow_total > 0 else 0
    evidence = (
        f"Fan-in pattern: {in_degree} unique senders → ${inflow_total:,.0f} received, "
        f"then {out_degree} unique receivers ← ${outflow_total:,.0f} sent "
        f"({outflow_pct:.0f}% forwarded; fan-in ratio {fan_in_ratio:.1f}:1)"
    )

    return [RuleSignal(
        account_id=account_id,
        signal_type="funnel_rule",
        score=round(score, 1),
        weight=SIGNAL_WEIGHT,
        evidence=evidence,
        confidence=round(confidence, 2),
    )]
