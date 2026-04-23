"""
backend/detection/graph/temporal_signal.py
─────────────────────────────────────────────────────────────────────────────
Graph signal that analyses the TIMING of transactions in the network.

Traditional graph analysis looks at the STRUCTURE of connections.
Temporal analysis looks at WHEN those connections occur.

Why timing matters for AML:
  Money laundering often requires moving funds quickly to avoid detection
  and take advantage of settlement windows. This creates distinctive
  temporal patterns:

  1. RAPID FORWARDING: Money arrives and is immediately sent onward.
     Natural legitimate transactions have days/weeks between receiving
     and sending. Laundering often happens in hours.

  2. SYNCHRONIZED FLOWS: Multiple accounts all become active at the same time
     (e.g., 15 accounts that were dormant all start transacting on the same day).
     This suggests coordinated activation of a mule network.

  3. TIME-ZONE ANOMALIES: Transactions occur in the middle of the night
     for the account's apparent location. While not conclusive, it's a
     supporting signal.

Implementation:
  We look at the transaction graph edges and compute the median time between
  receiving a payment (in-edge timestamp) and forwarding it (out-edge timestamp)
  for each account. Very short forwarding windows are suspicious.

  For synchronized flows, we look at accounts that all started transacting
  within the same 24-hour window.
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta
from collections import defaultdict

import networkx as nx
from backend.detection.rules.base_rule import RuleSignal

# ─── Configuration ────────────────────────────────────────────────────────────

# Forwarding within this many hours is suspicious
RAPID_FORWARD_HOURS = 6

# Minimum number of rapid-forwarding events to flag
MIN_RAPID_FORWARD_EVENTS = 2

# Synchronized activation: accounts become active within this window
SYNC_WINDOW_HOURS = 24
MIN_SYNC_ACCOUNTS = 5  # at least this many accounts must activate together

SIGNAL_WEIGHT = 1.4


def compute_temporal_signals(
    G:            nx.DiGraph,
    transactions: list[dict],
) -> list[RuleSignal]:
    """
    Detect temporal anomalies in the transaction network.

    Args:
        G:            The transaction graph (structure only — no timestamps).
        transactions: Raw transaction list with 'transaction_date' fields.

    Returns:
        List of RuleSignals for accounts with suspicious temporal patterns.
    """
    if not transactions or G.number_of_nodes() < 3:
        return []

    signals: list[RuleSignal] = []

    # ── Build per-account transaction timeline ───────────────────────────────
    # For each account, record all inflow and outflow times
    inflow_times:  dict[str, list[datetime]] = defaultdict(list)
    outflow_times: dict[str, list[datetime]] = defaultdict(list)

    for tx in transactions:
        dt = tx.get('transaction_date')
        if dt is None:
            continue
        inflow_times[tx.get('receiver_account_id', '')].append(dt)
        outflow_times[tx.get('sender_account_id', '')].append(dt)

    # ── Check 1: Rapid forwarding ─────────────────────────────────────────────
    for account_id in G.nodes():
        if account_id not in inflow_times or account_id not in outflow_times:
            continue

        inflows  = sorted(inflow_times[account_id])
        outflows = sorted(outflow_times[account_id])

        rapid_count = 0

        for inflow_time in inflows:
            # Check if there's an outflow within RAPID_FORWARD_HOURS of this inflow
            window_end = inflow_time + timedelta(hours=RAPID_FORWARD_HOURS)
            for outflow_time in outflows:
                if inflow_time <= outflow_time <= window_end:
                    rapid_count += 1
                    break  # one rapid forward per inflow

        if rapid_count >= MIN_RAPID_FORWARD_EVENTS:
            score = min(85.0, 40.0 + rapid_count * 8)
            confidence = min(0.85, 0.50 + rapid_count * 0.08)
            evidence = (
                f"Rapid forwarding: {rapid_count} instances where received funds "
                f"were forwarded within {RAPID_FORWARD_HOURS} hours. "
                f"Characteristic of wire layering or mule account operation."
            )
            signals.append(RuleSignal(
                account_id  = account_id,
                signal_type = 'graph_temporal',
                score       = round(score, 1),
                weight      = SIGNAL_WEIGHT,
                evidence    = evidence,
                confidence  = round(confidence, 2),
            ))

    # ── Check 2: Synchronized activation ─────────────────────────────────────
    # Find the first transaction date for each account
    first_tx_by_account: dict[str, datetime] = {}
    for tx in transactions:
        acc = tx.get('sender_account_id', '')
        dt  = tx.get('transaction_date')
        if acc and dt:
            if acc not in first_tx_by_account or dt < first_tx_by_account[acc]:
                first_tx_by_account[acc] = dt

    # Group accounts by their first-transaction day
    activation_buckets: dict[str, list[str]] = defaultdict(list)
    for acc, first_dt in first_tx_by_account.items():
        # Round to nearest day for grouping
        day_key = first_dt.strftime('%Y-%m-%d')
        activation_buckets[day_key].append(acc)

    # Flag accounts in a synchronized group
    for day_key, accounts in activation_buckets.items():
        if len(accounts) >= MIN_SYNC_ACCOUNTS:
            for account_id in accounts:
                # Check if this account is in the graph (relevant to the network)
                if G.has_node(account_id):
                    evidence = (
                        f"Synchronized activation: {len(accounts)} accounts all became "
                        f"active on {day_key}. Consistent with coordinated mule network "
                        f"activation or batch account opening for laundering."
                    )
                    signals.append(RuleSignal(
                        account_id  = account_id,
                        signal_type = 'graph_temporal',
                        score       = min(70.0, 35.0 + len(accounts) * 3),
                        weight      = SIGNAL_WEIGHT,
                        evidence    = evidence,
                        confidence  = 0.55,
                    ))

    return signals
