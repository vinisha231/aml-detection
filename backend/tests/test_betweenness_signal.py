"""
backend/tests/test_betweenness_signal.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the betweenness centrality graph signal.

Tests verify:
  - A bridge node in a two-cluster graph is flagged
  - Peripheral leaf nodes are NOT flagged
  - Empty graph returns no signals
  - Signal type is correct
  - Scores are bounded 0–100
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.detection.graph.betweenness_signal import compute_betweenness_signals


def build_dumbbell_graph() -> nx.DiGraph:
    """
    Build a dumbbell-shaped graph: two cliques connected by a single bridge node.

      Cluster A (ACC_A1..A5) ← → ACC_BRIDGE → Cluster B (ACC_B1..B5)

    ACC_BRIDGE has the highest betweenness because ALL paths from cluster A
    to cluster B must pass through it.
    """
    G = nx.DiGraph()

    # Cluster A: 5 nodes fully connected to each other
    cluster_a = [f'ACC_A{i}' for i in range(1, 6)]
    for sender in cluster_a:
        for receiver in cluster_a:
            if sender != receiver:
                G.add_edge(sender, receiver, weight=10_000, tx_count=1)

    # Cluster B: 5 nodes fully connected to each other
    cluster_b = [f'ACC_B{i}' for i in range(1, 6)]
    for sender in cluster_b:
        for receiver in cluster_b:
            if sender != receiver:
                G.add_edge(sender, receiver, weight=10_000, tx_count=1)

    # Bridge: connects the two clusters
    bridge = 'ACC_BRIDGE'
    for a in cluster_a:
        G.add_edge(a, bridge, weight=50_000, tx_count=3)
    for b in cluster_b:
        G.add_edge(bridge, b, weight=50_000, tx_count=3)

    return G


class TestComputeBetweennessSignals:

    def test_bridge_node_is_flagged(self):
        """ACC_BRIDGE connects two clusters — should have highest betweenness."""
        G = build_dumbbell_graph()
        signals = compute_betweenness_signals(G)

        flagged_ids = {s.account_id for s in signals}
        assert 'ACC_BRIDGE' in flagged_ids, "Bridge node should be flagged"

    def test_peripheral_leaf_not_flagged(self):
        """
        A simple leaf node (only one connection) should not appear in signals.
        Add a leaf to the dumbbell and verify it's not flagged.
        """
        G = build_dumbbell_graph()
        G.add_edge('ACC_LEAF', 'ACC_A1', weight=500, tx_count=1)

        signals = compute_betweenness_signals(G)
        flagged_ids = {s.account_id for s in signals}
        assert 'ACC_LEAF' not in flagged_ids, "Leaf nodes should not be flagged"

    def test_empty_graph_returns_empty(self):
        """Empty graph → no signals."""
        G = nx.DiGraph()
        assert compute_betweenness_signals(G) == []

    def test_signal_type_is_correct(self):
        """All signals must have signal_type 'graph_betweenness'."""
        G = build_dumbbell_graph()
        signals = compute_betweenness_signals(G)
        for sig in signals:
            assert sig.signal_type == 'graph_betweenness'

    def test_scores_bounded(self):
        """All scores must be in [0, 100]."""
        G = build_dumbbell_graph()
        signals = compute_betweenness_signals(G)
        for sig in signals:
            assert 0 <= sig.score <= 100, f"Score {sig.score} out of bounds"

    def test_small_graph_returns_empty(self):
        """Graph with fewer than 4 nodes returns no signals."""
        G = nx.DiGraph()
        G.add_edge('ACC_1', 'ACC_2', weight=1000, tx_count=1)
        G.add_edge('ACC_2', 'ACC_3', weight=1000, tx_count=1)
        assert compute_betweenness_signals(G) == []
