"""
backend/detection/graph/hub_spoke_signal.py
─────────────────────────────────────────────────────────────────────────────
Graph signal for detecting hub-and-spoke money distribution patterns.

What is a hub-and-spoke pattern?
  A central "hub" account receives a large sum of money, then distributes
  small amounts to many "spoke" accounts. The spoke accounts may then
  aggregate and forward funds elsewhere.

  This is a common pattern for:
    1. Funnel accounts: aggregate from many small senders, send to one receiver
    2. Distribution networks: one source sends to many mules
    3. Smurfing at scale: central coordinator sends sub-threshold amounts

  Network structure:
    - Hub has HIGH out-degree (many receivers) OR high in-degree (many senders)
    - Hub's total flow volume is disproportionately large relative to spoke accounts
    - Spokes have very low degree (usually just 1 connection to the hub)

How this differs from PageRank:
  PageRank scores a node based on the quality (PageRank) of its neighbours.
  A node with few high-PageRank neighbours scores well.

  Hub-spoke detection looks at STRUCTURAL pattern:
    - Star topology (hub with many leaves)
    - Asymmetry: hub is much more connected than its neighbours
    - Volume: hub handles much more money than spoke accounts

Implementation:
  We look for accounts where:
    - out_degree ≥ 10 AND avg spoke degree ≤ 2 (hub sends to isolated accounts)
    - OR in_degree ≥ 10 AND avg spoke degree ≤ 2 (hub aggregates from isolated accounts)
    - The hub account handles ≥ 60% of the total flow through its neighbourhood
─────────────────────────────────────────────────────────────────────────────
"""

import networkx as nx
from backend.detection.rules.base_rule import RuleSignal

# ─── Configuration ────────────────────────────────────────────────────────────

# Minimum out-degree or in-degree to be considered a potential hub
MIN_HUB_DEGREE = 8

# Maximum average degree of spoke nodes (they should be poorly connected)
MAX_SPOKE_AVG_DEGREE = 2.5

# Minimum fraction of neighbourhood volume flowing through the hub
MIN_HUB_VOLUME_SHARE = 0.60  # hub handles ≥ 60% of neighbourhood flow

SIGNAL_WEIGHT = 1.6
BASE_SCORE    = 50.0


def compute_hub_spoke_signals(G: nx.DiGraph) -> list[RuleSignal]:
    """
    Detect accounts that are hubs in a star-shaped transaction network.

    Args:
        G: Directed transaction graph with 'weight' edge attributes
           representing total transaction amounts.

    Returns:
        List of RuleSignals for hub accounts. Empty list if none qualify.
    """
    if G.number_of_nodes() < 5:
        return []

    signals: list[RuleSignal] = []

    for node in G.nodes():
        # Get neighbours in both directions
        successors   = list(G.successors(node))    # accounts this node sent money to
        predecessors = list(G.predecessors(node))   # accounts that sent money to this node

        out_degree = len(successors)
        in_degree  = len(predecessors)

        # Check hub conditions: must have high degree in at least one direction
        is_distribution_hub = out_degree >= MIN_HUB_DEGREE  # sends to many spokes
        is_collection_hub   = in_degree  >= MIN_HUB_DEGREE  # receives from many spokes

        if not (is_distribution_hub or is_collection_hub):
            continue

        # Compute the average degree of spoke nodes
        # Spokes should be low-degree (connected only to the hub)
        spokes = set(successors + predecessors)
        if not spokes:
            continue

        spoke_degrees = [G.degree(s) for s in spokes]
        avg_spoke_degree = sum(spoke_degrees) / len(spoke_degrees)

        if avg_spoke_degree > MAX_SPOKE_AVG_DEGREE:
            continue  # spokes are too well-connected — not a hub-spoke pattern

        # Compute volume share: what fraction of the neighbourhood's total flow
        # passes through this hub?
        hub_volume = (
            sum(G[node][s].get('weight', 0) for s in successors) +
            sum(G[p][node].get('weight', 0) for p in predecessors)
        )

        spoke_volume = sum(
            sum(G[s][t].get('weight', 0) for t in G.successors(s) if t != node) +
            sum(G[p][s].get('weight', 0) for p in G.predecessors(s) if p != node)
            for s in spokes
        )

        total_volume = hub_volume + spoke_volume
        if total_volume == 0:
            continue

        hub_share = hub_volume / total_volume
        if hub_share < MIN_HUB_VOLUME_SHARE:
            continue  # hub doesn't dominate the flow — probably not a real hub

        # ── Score calculation ─────────────────────────────────────────────────
        max_degree = max(in_degree, out_degree)
        degree_bonus = min(25.0, (max_degree - MIN_HUB_DEGREE) * 2.5)
        volume_bonus = min(15.0, (hub_share - MIN_HUB_VOLUME_SHARE) * 50)
        score = min(95.0, BASE_SCORE + degree_bonus + volume_bonus)

        confidence = min(0.90, 0.55 + (max_degree / 50) * 0.25)

        hub_type = 'distribution' if is_distribution_hub else 'collection'
        evidence = (
            f"Hub-and-spoke {hub_type} pattern: "
            f"{max_degree} spokes with avg degree {avg_spoke_degree:.1f}. "
            f"Hub controls {hub_share*100:.0f}% of neighbourhood transaction volume. "
            f"Characteristic of a coordinator account in a mule network or "
            f"aggregation point for smurfed funds."
        )

        signals.append(RuleSignal(
            account_id  = node,
            signal_type = 'graph_hub_spoke',
            score       = round(score, 1),
            weight      = SIGNAL_WEIGHT,
            evidence    = evidence,
            confidence  = round(confidence, 2),
        ))

    return signals
