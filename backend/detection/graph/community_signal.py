"""
backend/detection/graph/community_signal.py
─────────────────────────────────────────────────────────────────────────────
Detects isolated community clusters — the shell company pattern.

Louvain community detection finds groups of nodes (accounts) that are
more connected to each other than to the rest of the graph.

A suspicious community has two properties:
  1. It's SMALL (3–6 accounts)
  2. It's ISOLATED (no edges to the outside world)

Shell companies EXACTLY match this profile:
  - Small set of related companies
  - Only transact with each other (no external clients or suppliers)
─────────────────────────────────────────────────────────────────────────────
"""

import networkx as nx
import networkx.algorithms.community as nx_comm
from typing import List

from ..rules.structuring_rule import RuleSignal

# ─── Constants ─────────────────────────────────────────────────────────────────

MAX_CLUSTER_SIZE_TO_FLAG = 8    # clusters larger than this are likely legitimate orgs
MIN_CLUSTER_SIZE_TO_FLAG = 2    # need at least 2 accounts to be a cluster

SIGNAL_WEIGHT = 1.8


def compute_community_signals(
    G: nx.DiGraph,
    seed: int = 42
) -> List[RuleSignal]:
    """
    Find isolated community clusters using Louvain algorithm.

    Steps:
    1. Convert directed graph to undirected (Louvain works on undirected)
    2. Run Louvain community detection
    3. For each community: check if it's small AND isolated
    4. Flag accounts in suspicious communities

    Args:
        G:    The full transaction graph (from builder.py)
        seed: Random seed for reproducibility (Louvain is non-deterministic)

    Returns:
        List of RuleSignal objects for accounts in suspicious clusters.
    """

    if G.number_of_nodes() < 3:
        return []

    # ── Step 1: Convert to undirected ─────────────────────────────────────────
    # Louvain community detection works on undirected graphs.
    # We lose direction information here — that's acceptable for cluster detection
    # because we're looking for tight groups, not directional flow.
    G_undirected = G.to_undirected()

    # ── Step 2: Run Louvain community detection ────────────────────────────────
    # This returns a list of sets, each set containing account IDs in one community.
    # Example: [{"ACC_001", "ACC_002"}, {"ACC_003", "ACC_004", "ACC_005"}, ...]
    try:
        communities = nx_comm.louvain_communities(G_undirected, seed=seed)
    except Exception as e:
        # Louvain can fail on disconnected graphs — handle gracefully
        print(f"[CommunitySignal] Louvain failed: {e}. Skipping community detection.")
        return []

    signals = []

    # ── Step 3: Evaluate each community ───────────────────────────────────────
    for community in communities:

        # Filter by size
        if not (MIN_CLUSTER_SIZE_TO_FLAG <= len(community) <= MAX_CLUSTER_SIZE_TO_FLAG):
            continue

        # Skip communities containing special system accounts
        has_system_account = any(
            acc.startswith("ACC_") and not acc[4:].isdigit()
            for acc in community
        )
        if has_system_account:
            continue

        # ── Check isolation: does this community have ANY external edges? ──────
        external_edge_count = 0
        internal_edge_count = 0

        for account_id in community:
            # Look at all neighbors in the DIRECTED graph
            for neighbor in G.predecessors(account_id):  # incoming
                if neighbor not in community:
                    external_edge_count += 1
                else:
                    internal_edge_count += 1
            for neighbor in G.successors(account_id):    # outgoing
                if neighbor not in community:
                    external_edge_count += 1
                else:
                    internal_edge_count += 1

        # Isolation ratio: what fraction of connections are internal?
        total_connections = external_edge_count + internal_edge_count
        if total_connections == 0:
            continue  # no connections at all — can't be a shell cluster

        isolation_ratio = internal_edge_count / total_connections

        # We require HIGH isolation (≥ 80% internal) to flag as shell company
        if isolation_ratio < 0.80:
            continue

        # ── Calculate score for this cluster ───────────────────────────────────
        # Higher isolation + smaller size = more suspicious
        score = 50.0 + isolation_ratio * 35.0  # 80% isolated → score 78, 100% → score 85
        score = min(88.0, score)

        confidence = min(0.88, 0.55 + isolation_ratio * 0.33)

        # ── Calculate total money in cluster ───────────────────────────────────
        cluster_volume = sum(
            data.get("weight", 0)
            for u, v, data in G.edges(data=True)
            if u in community and v in community
        )

        # ── Generate a signal for EACH account in the cluster ─────────────────
        for account_id in community:
            evidence = (
                f"Shell cluster: member of {len(community)}-account isolated group. "
                f"Internal connections: {internal_edge_count}, "
                f"external: {external_edge_count} "
                f"({isolation_ratio:.0%} isolated). "
                f"Total cluster volume: ${cluster_volume:,.0f}."
            )

            signals.append(RuleSignal(
                account_id=account_id,
                signal_type="graph_community",
                score=round(score, 1),
                weight=SIGNAL_WEIGHT,
                evidence=evidence,
                confidence=round(confidence, 2),
            ))

    return signals
