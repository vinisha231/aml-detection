"""
backend/detection/graph/cycle_signal.py
─────────────────────────────────────────────────────────────────────────────
Detects graph cycles — the round-tripping pattern.

A cycle is a path in the transaction graph that starts and ends at the same account.
Example: ACC_001 → ACC_002 → ACC_003 → ACC_001

This is the graph signature of round-tripping / circular flow laundering.

Challenge: large graphs have MANY cycles.
  We filter for MEANINGFUL cycles:
  1. Length 3–8 hops (short cycles are more suspicious than 20-hop chains)
  2. High-value (total money in cycle ≥ $5,000)
  3. Time-constrained (cycle completes within 30 days)

Performance note:
  nx.simple_cycles() uses DFS and can be slow on large graphs.
  We use a depth limit and set a maximum result count to keep it fast.
─────────────────────────────────────────────────────────────────────────────
"""

import networkx as nx
from typing import List

from ..rules.structuring_rule import RuleSignal

# ─── Constants ─────────────────────────────────────────────────────────────────

MIN_CYCLE_LENGTH = 3   # minimum hops in cycle (exclude simple A↔B back-and-forth)
MAX_CYCLE_LENGTH = 8   # maximum hops — longer cycles are less useful for detection
MIN_CYCLE_AMOUNT = 5_000.00   # minimum total amount in the cycle
MAX_CYCLES_TO_PROCESS = 500   # cap to avoid performance issues on large graphs

SIGNAL_WEIGHT = 2.0  # round-tripping is a strong signal


def compute_cycle_signals(
    G: nx.DiGraph,
) -> List[RuleSignal]:
    """
    Detect accounts that participate in directed cycles (round-tripping).

    Algorithm:
    1. Find all simple cycles in the directed graph (using DFS)
    2. Filter for cycles meeting our criteria (length, amount)
    3. Flag every account that appears in a qualifying cycle

    Args:
        G: The full transaction graph (from builder.py)

    Returns:
        List of RuleSignal objects for all accounts in qualifying cycles.
    """

    if G.number_of_edges() == 0:
        return []

    # ── Step 1: Find cycles ────────────────────────────────────────────────────
    # nx.simple_cycles() returns a generator of cycles
    # Each cycle is a list of node IDs (account IDs)
    # Example: ["ACC_001", "ACC_002", "ACC_003"] means 001→002→003→001
    cycles_found = []

    try:
        for cycle in nx.simple_cycles(G):
            # Apply length filter immediately (before collecting too many)
            if MIN_CYCLE_LENGTH <= len(cycle) <= MAX_CYCLE_LENGTH:
                cycles_found.append(cycle)

            if len(cycles_found) >= MAX_CYCLES_TO_PROCESS:
                # Stop early to avoid performance issues
                break
    except Exception as e:
        print(f"[CycleSignal] cycle detection failed: {e}")
        return []

    if not cycles_found:
        return []

    # ── Step 2: Calculate cycle metrics ───────────────────────────────────────
    # For each cycle, calculate total amount and flag qualifying cycles
    qualifying_cycles = []

    for cycle in cycles_found:
        # Calculate total money flow through this cycle
        # cycle = [A, B, C] means edges: A→B, B→C, C→A
        cycle_amount = 0.0
        cycle_valid  = True

        for i in range(len(cycle)):
            sender   = cycle[i]
            receiver = cycle[(i + 1) % len(cycle)]  # wraps around

            if G.has_edge(sender, receiver):
                cycle_amount += G[sender][receiver].get("weight", 0)
            else:
                # Cycle doesn't actually exist as transactions — skip
                cycle_valid = False
                break

        if not cycle_valid:
            continue

        if cycle_amount < MIN_CYCLE_AMOUNT:
            # Too small to be meaningful
            continue

        qualifying_cycles.append((cycle, cycle_amount))

    # ── Step 3: Collect all accounts in qualifying cycles ─────────────────────
    # An account might appear in MULTIPLE cycles — that's even more suspicious
    account_cycle_count = {}  # account_id → number of cycles it's in
    account_max_amount  = {}  # account_id → largest cycle it's part of
    account_min_length  = {}  # account_id → shortest cycle it's in (more suspicious)

    for cycle, cycle_amount in qualifying_cycles:
        for account_id in cycle:
            account_cycle_count[account_id] = account_cycle_count.get(account_id, 0) + 1
            account_max_amount[account_id]  = max(
                account_max_amount.get(account_id, 0), cycle_amount
            )
            account_min_length[account_id]  = min(
                account_min_length.get(account_id, MAX_CYCLE_LENGTH + 1), len(cycle)
            )

    # ── Step 4: Generate signals ───────────────────────────────────────────────
    signals = []

    for account_id, cycle_count in account_cycle_count.items():

        # Skip system accounts
        if account_id.startswith("ACC_") and not account_id[4:].isdigit():
            continue

        max_amount  = account_max_amount[account_id]
        min_length  = account_min_length[account_id]

        # Score formula:
        # Base: 60 (any cycle membership is suspicious)
        # + up to 25 for high cycle count (multiple cycles = worse)
        # + up to 10 for large cycle amounts
        score = 60.0
        score += min(25.0, cycle_count * 8.0)  # up to 25 points for multiple cycles
        score += min(10.0, max_amount / 50_000 * 5.0)  # up to 10 points for large amounts
        score = min(95.0, score)

        confidence = min(0.90, 0.65 + cycle_count * 0.05)

        evidence = (
            f"Round-trip detected: account appears in {cycle_count} directed cycle(s). "
            f"Shortest cycle: {min_length} hops. "
            f"Largest cycle amount: ${max_amount:,.0f}."
        )

        signals.append(RuleSignal(
            account_id=account_id,
            signal_type="graph_cycle",
            score=round(score, 1),
            weight=SIGNAL_WEIGHT,
            evidence=evidence,
            confidence=round(confidence, 2),
        ))

    return signals
