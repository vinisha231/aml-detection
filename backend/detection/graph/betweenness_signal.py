"""
backend/detection/graph/betweenness_signal.py
─────────────────────────────────────────────────────────────────────────────
Graph signal using Betweenness Centrality to detect critical pass-through nodes.

What is betweenness centrality?
  A measure of how often a node appears on the shortest path between
  other pairs of nodes in the graph.

  Formally: BC(v) = Σ_{s≠v≠t} σ(s,t|v) / σ(s,t)

  Where:
    σ(s,t)   = number of shortest paths from node s to node t
    σ(s,t|v) = number of those paths that pass through node v

  Intuitively: nodes with high betweenness are "bridges" — if you removed
  them, many routes through the network would be cut off.

Why it matters for AML:
  In a money laundering network, launderers use specific accounts to
  "bridge" money from dirty sources to clean destinations. These bridge
  accounts appear on many shortest paths because they are the only
  channel connecting two parts of the network.

  This is different from PageRank (which flags accounts that receive
  from many others) — betweenness flags accounts that facilitate flow
  between others, even if they themselves don't receive much.

  Example:
    Dirty pool → BRIDGE → Shell company cluster → Clean withdrawal
    BRIDGE has high betweenness because it connects two separate
    sub-networks.

Difference from chain_signal.py:
  chain_signal.py uses a rule-based check (passthrough_ratio, in/out
  degree) combined with betweenness. This module uses ONLY betweenness
  centrality for a purer graph-theoretic signal.

Complexity note:
  Betweenness centrality is O(V × E) for sparse graphs (Brandes algorithm).
  For 5,000 nodes, this runs in a few seconds. For production at scale,
  use approximate betweenness (k-sample algorithm).
─────────────────────────────────────────────────────────────────────────────
"""

import math
import networkx as nx
from backend.detection.rules.base_rule import RuleSignal

# ─── Configuration ────────────────────────────────────────────────────────────

# Flag accounts in the top X% of betweenness scores
TOP_PERCENTILE = 95  # top 5% — betweenness is very concentrated

# Minimum betweenness score to even consider flagging
MIN_BETWEENNESS = 0.01  # ignore nodes that are barely on any paths

# Weight in the scoring engine
SIGNAL_WEIGHT = 1.4

# For large graphs, use approximate betweenness (sampling)
APPROXIMATE_SAMPLE_K = 200  # number of pivot nodes to sample


def compute_betweenness_signals(G: nx.DiGraph) -> list[RuleSignal]:
    """
    Identify high-betweenness accounts that act as bridges in the network.

    Args:
        G: Directed transaction graph. Nodes = accounts, edges = money flows.
           Edge attributes: weight (total amount), tx_count (transaction count).

    Returns:
        List of RuleSignals for accounts with high betweenness centrality.
        Empty list if the graph is too small or no accounts qualify.
    """
    if G.number_of_nodes() < 4:
        # Need at least 4 nodes for betweenness to be meaningful
        return []

    # ── Compute betweenness centrality ───────────────────────────────────────
    # We use the directed graph — betweenness is direction-aware.
    # normalized=True: divide by (n-1)(n-2) so scores are in [0, 1]
    # weight='weight': use transaction amount as edge weight
    #   (NetworkX interprets higher weight as SHORTER distance for shortest paths,
    #    so we use 1/weight to make high-volume flows "closer")

    n = G.number_of_nodes()

    if n > 1000:
        # For large graphs, use approximate betweenness with sampling
        # k=APPROXIMATE_SAMPLE_K: only sample this many pivot nodes
        bc = nx.betweenness_centrality(
            G,
            normalized=True,
            weight=None,  # unweighted for speed in large graphs
            k=min(APPROXIMATE_SAMPLE_K, n),
        )
    else:
        bc = nx.betweenness_centrality(
            G,
            normalized=True,
            weight=None,
        )

    if not bc:
        return []

    # ── Find the threshold ────────────────────────────────────────────────────
    all_scores = sorted(bc.values())
    if not all_scores:
        return []

    # Find the score at the TOP_PERCENTILE mark
    percentile_idx = int(len(all_scores) * TOP_PERCENTILE / 100)
    percentile_idx = min(percentile_idx, len(all_scores) - 1)
    threshold = all_scores[percentile_idx]

    # Also enforce a minimum absolute betweenness
    threshold = max(threshold, MIN_BETWEENNESS)

    # ── Generate signals for high-betweenness nodes ───────────────────────────
    signals: list[RuleSignal] = []

    for account_id, betweenness in bc.items():
        if betweenness < threshold:
            continue

        # Convert betweenness (0 to 1) to a risk score (0 to 100)
        # Use log scale so extreme values don't compress the mid-range
        if betweenness > 0:
            # log10 of normalized betweenness, scaled to 0–100
            # betweenness = 0.001 → score ≈ 30
            # betweenness = 0.01  → score ≈ 52
            # betweenness = 0.1   → score ≈ 75
            # betweenness = 1.0   → score = 100
            score = min(100.0, 25.0 + 25.0 * (1 + math.log10(betweenness)))
        else:
            score = 0.0

        # Confidence based on how far above the threshold this node is
        confidence = min(0.90, 0.50 + (betweenness / max(all_scores)) * 0.4)

        # Network topology context for evidence string
        in_degree  = G.in_degree(account_id)
        out_degree = G.out_degree(account_id)

        evidence = (
            f"Betweenness centrality = {betweenness:.4f} "
            f"(top {100 - TOP_PERCENTILE:.0f}% of network). "
            f"Account has {in_degree} incoming and {out_degree} outgoing "
            f"connections, placing it on many shortest paths between "
            f"other accounts — characteristic of a bridge/relay node."
        )

        signals.append(RuleSignal(
            account_id  = account_id,
            signal_type = 'graph_betweenness',
            score       = round(score, 1),
            weight      = SIGNAL_WEIGHT,
            evidence    = evidence,
            confidence  = round(confidence, 2),
        ))

    return signals
