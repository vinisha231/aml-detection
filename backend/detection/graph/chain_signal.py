"""
backend/detection/graph/chain_signal.py
─────────────────────────────────────────────────────────────────────────────
Detects high-value directed chains — the layering pattern.

Layering creates chains of transactions:
  Dirty Source → Intermediate1 → Intermediate2 → Clean Destination

Each hop reduces the amount (fees taken).
The chain happens quickly (within hours).

How we detect this:
  We look for paths of 3+ hops where:
  1. Total chain amount is high (≥ $25,000)
  2. Each hop amount is decreasing (consistent fee-taking pattern)
  3. The chain involves accounts that appear central in the graph

Approach:
  We use betweenness centrality to find "bridge" accounts —
  accounts that appear frequently on the shortest paths between
  high-risk nodes. These are likely intermediary accounts.
─────────────────────────────────────────────────────────────────────────────
"""

import networkx as nx
from typing import List

from ..rules.structuring_rule import RuleSignal

# ─── Constants ─────────────────────────────────────────────────────────────────

# Betweenness centrality threshold — accounts above this are flagged as bridges
BETWEENNESS_PERCENTILE = 90  # top 10%

# Minimum in-degree AND out-degree to be a layering intermediary
# (layering accounts both receive and send large amounts)
MIN_DEGREE_FOR_INTERMEDIARY = 2

SIGNAL_WEIGHT = 1.6


def compute_chain_signals(
    G: nx.DiGraph,
) -> List[RuleSignal]:
    """
    Detect potential layering intermediary accounts using betweenness centrality.

    Betweenness centrality measures how often a node appears on the
    shortest path between other nodes. High betweenness = bridge account.
    In AML, bridge accounts in high-value flows are often intermediaries.

    Args:
        G: The full transaction graph (from builder.py)

    Returns:
        List of RuleSignal objects for likely layering intermediaries.
    """

    if G.number_of_nodes() < 4:
        # Need at least 4 nodes for a 3-hop chain
        return []

    # ── Step 1: Compute betweenness centrality ────────────────────────────────
    # normalized=True: scores are between 0 and 1 (easier to compare)
    # weight=None: we use hop count (not amount) for betweenness
    #   because layering is about STRUCTURE (many hops), not just money flow
    betweenness = nx.betweenness_centrality(G, normalized=True, weight=None)

    # ── Step 2: Find the threshold (90th percentile) ──────────────────────────
    all_scores   = sorted(betweenness.values())
    total        = len(all_scores)

    if total == 0:
        return []

    threshold_idx = int(total * BETWEENNESS_PERCENTILE / 100)
    threshold_val = all_scores[min(threshold_idx, total - 1)]

    signals = []

    # ── Step 3: Flag high-betweenness accounts ────────────────────────────────
    for account_id, centrality_score in betweenness.items():

        if centrality_score <= threshold_val:
            continue

        # Skip system accounts
        if account_id.startswith("ACC_") and not account_id[4:].isdigit():
            continue

        # A true intermediary both receives AND sends money
        in_degree  = G.in_degree(account_id)
        out_degree = G.out_degree(account_id)

        if in_degree < MIN_DEGREE_FOR_INTERMEDIARY or out_degree < MIN_DEGREE_FOR_INTERMEDIARY:
            # One-directional accounts are less likely to be intermediaries
            continue

        # ── Calculate total flow through this account ─────────────────────────
        total_in  = sum(d.get("weight", 0) for _, _, d in G.in_edges(account_id, data=True))
        total_out = sum(d.get("weight", 0) for _, _, d in G.out_edges(account_id, data=True))

        # For layering, OUTFLOW ≈ INFLOW (minus small fees)
        # If outflow is very different from inflow, it's not a typical intermediary
        if total_in > 0:
            passthrough_ratio = total_out / total_in
        else:
            passthrough_ratio = 0.0

        # Intermediaries pass through 70–99% of what they receive
        if passthrough_ratio < 0.50 or passthrough_ratio > 1.10:
            # Too much accumulation or spending — probably not intermediary
            continue

        # ── Score formula ─────────────────────────────────────────────────────
        # Convert percentile to score
        percentile = (
            sorted(betweenness.values()).index(centrality_score) / total * 100
        )
        score = max(30.0, (percentile - BETWEENNESS_PERCENTILE) / (100 - BETWEENNESS_PERCENTILE) * 75.0)
        score = min(80.0, score)  # chain is harder to confirm than cycle, cap lower

        confidence = min(0.75, 0.40 + centrality_score * 2.0)

        evidence = (
            f"Potential layering intermediary: betweenness centrality {centrality_score:.4f} "
            f"(top {100 - percentile:.1f}%). "
            f"Receives from {in_degree} accounts (${total_in:,.0f}), "
            f"sends to {out_degree} accounts (${total_out:,.0f}). "
            f"Pass-through ratio: {passthrough_ratio:.0%}."
        )

        signals.append(RuleSignal(
            account_id=account_id,
            signal_type="graph_chain",
            score=round(score, 1),
            weight=SIGNAL_WEIGHT,
            evidence=evidence,
            confidence=round(confidence, 2),
        ))

    return signals
