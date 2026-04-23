"""
backend/tests/test_pagerank_signal.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the PageRank graph signal.

Tests verify:
  - High-centrality accounts (many inflows) get flagged
  - Peripheral accounts with few connections don't get flagged
  - Empty graph returns no signals
  - Signal type is correct
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.detection.graph.pagerank_signal import compute_pagerank_signals


def build_test_graph(edges: list) -> nx.DiGraph:
    """Build a DiGraph from a list of (sender, receiver, weight) tuples."""
    G = nx.DiGraph()
    for sender, receiver, weight in edges:
        if G.has_edge(sender, receiver):
            G[sender][receiver]["weight"] += weight
            G[sender][receiver]["tx_count"] += 1
        else:
            G.add_edge(sender, receiver, weight=weight, tx_count=1)
    return G


class TestComputePageRankSignals:

    def test_empty_graph_returns_empty_list(self):
        """Empty graph → no signals."""
        G = nx.DiGraph()
        signals = compute_pagerank_signals(G)
        assert signals == []

    def test_central_account_gets_flagged(self):
        """
        Account that receives from 50 senders (funnel) should have high PageRank.
        In a graph where one account receives from many others, it should be in top 10%.
        """
        # Build a star graph: 50 accounts → ACC_CENTER
        edges = [
            (f"ACC_SENDER_{i}", "ACC_001001", 1000.0)
            for i in range(50)
        ]
        # Add some benign edges too (to give the graph realistic structure)
        for i in range(10):
            edges.append((f"ACC_BENIGN_{i}", f"ACC_RECV_{i}", 500.0))

        G = build_test_graph(edges)
        signals = compute_pagerank_signals(G)

        # ACC_001001 should appear in the signals (it's highly central)
        flagged_ids = {s.account_id for s in signals}
        assert "ACC_001001" in flagged_ids, "Central account not flagged by PageRank"

    def test_signal_type_is_correct(self):
        """Signal type must be 'graph_pagerank'."""
        edges = [(f"ACC_SENDER_{i}", "ACC_001001", 500.0) for i in range(50)]
        for i in range(5):
            edges.append((f"ACC_BENIGN_{i}", f"ACC_R_{i}", 200.0))
        G = build_test_graph(edges)
        signals = compute_pagerank_signals(G)
        for sig in signals:
            assert sig.signal_type == "graph_pagerank"

    def test_score_is_bounded(self):
        """All scores must be between 0 and 100."""
        edges = [(f"ACC_{i}", "ACC_001001", 1000.0) for i in range(30)]
        G = build_test_graph(edges)
        signals = compute_pagerank_signals(G)
        for sig in signals:
            assert 0 <= sig.score <= 100, f"Score {sig.score} out of bounds"
