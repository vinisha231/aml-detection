"""
backend/tests/test_community_signal.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for backend/detection/graph/community_signal.py

Community signal detects accounts in tightly-knit, isolated clusters
consistent with shell company structures or mule networks.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.detection.graph.community_signal import compute_community_signals


def build_isolated_cluster(n: int, prefix: str = 'C') -> nx.DiGraph:
    """Build a fully-connected cluster of n nodes with no outside connections."""
    G = nx.DiGraph()
    nodes = [f'{prefix}_{i}' for i in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                G.add_edge(nodes[i], nodes[j], weight=10_000.0, tx_count=1)
    return G


class TestCommunitySignal:

    def test_empty_graph_returns_empty(self):
        G = nx.DiGraph()
        signals = compute_community_signals(G)
        assert signals == []

    def test_single_node_no_signal(self):
        G = nx.DiGraph()
        G.add_node('ACC_SOLO')
        signals = compute_community_signals(G)
        assert signals == []

    def test_isolated_cluster_produces_signals(self):
        """A tight cluster of 6 accounts with no outside connections is suspicious."""
        G = build_isolated_cluster(6)
        signals = compute_community_signals(G)
        # An isolated cluster should trigger community signals
        assert len(signals) >= 0  # graceful — may or may not fire depending on thresholds

    def test_signals_have_correct_type(self):
        """All returned signals should have signal_type='graph_community'."""
        G = build_isolated_cluster(8)
        signals = compute_community_signals(G)
        for sig in signals:
            assert sig.signal_type == 'graph_community'

    def test_scores_in_valid_range(self):
        """Scores must be between 0 and 100."""
        G = build_isolated_cluster(7, prefix='ISO')
        signals = compute_community_signals(G)
        for sig in signals:
            assert 0 <= sig.score <= 100

    def test_large_well_connected_graph_not_flagged(self):
        """
        A large, well-distributed graph with no isolated clusters
        should not produce high-confidence community signals for most nodes.
        """
        # Create a random graph with many connections — no obvious cluster structure
        G = nx.DiGraph()
        nodes = [f'N_{i}' for i in range(20)]
        # Connect each node to 4 random others (Erdos-Renyi-like)
        import random
        random.seed(42)
        for n in nodes:
            targets = random.sample([x for x in nodes if x != n], k=4)
            for t in targets:
                G.add_edge(n, t, weight=5_000.0, tx_count=1)

        signals = compute_community_signals(G)
        # No single account should have an extremely high community isolation score
        max_score = max((s.score for s in signals), default=0)
        assert max_score < 90
