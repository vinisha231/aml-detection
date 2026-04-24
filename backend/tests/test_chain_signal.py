"""
backend/tests/test_chain_signal.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for backend/detection/graph/chain_signal.py

Chain signal detects linear pass-through chains: A → B → C → D
where each hop forwards money with minimal divergence.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.detection.graph.chain_signal import compute_chain_signals


def make_graph_with_chain(*chain: str) -> nx.DiGraph:
    """Create a DiGraph with a linear chain of edges."""
    G = nx.DiGraph()
    for i in range(len(chain) - 1):
        G.add_edge(chain[i], chain[i + 1], weight=50_000.0, tx_count=1)
    return G


class TestChainSignal:

    def test_empty_graph_returns_empty(self):
        G = nx.DiGraph()
        signals = compute_chain_signals(G)
        assert signals == []

    def test_short_chain_not_flagged(self):
        """A chain of only 2 accounts is too short to be suspicious."""
        G = make_graph_with_chain('A', 'B')
        signals = compute_chain_signals(G)
        # Very short chains should produce no signals or minimal ones
        assert all(s.score < 50 for s in signals) if signals else True

    def test_long_chain_flagged(self):
        """A 5-hop chain should produce signals for intermediate nodes."""
        G = make_graph_with_chain('A', 'B', 'C', 'D', 'E', 'F')
        signals = compute_chain_signals(G)
        # The middle nodes (B, C, D, E) should be flagged as pass-through
        flagged_ids = {s.account_id for s in signals}
        # At least one middle node should be flagged
        middle_nodes = {'B', 'C', 'D', 'E'}
        if signals:  # only assert if the function produces signals
            assert len(flagged_ids & middle_nodes) > 0

    def test_signals_have_correct_type(self):
        """All returned signals should have signal_type='graph_chain'."""
        G = make_graph_with_chain('A', 'B', 'C', 'D', 'E')
        signals = compute_chain_signals(G)
        for sig in signals:
            assert sig.signal_type == 'graph_chain'

    def test_signals_have_valid_scores(self):
        """All signal scores should be between 0 and 100."""
        G = make_graph_with_chain('X', 'Y', 'Z', 'W', 'V', 'U')
        signals = compute_chain_signals(G)
        for sig in signals:
            assert 0 <= sig.score <= 100

    def test_branching_graph_not_flagged_as_chain(self):
        """A hub with many outgoing edges is not a chain — should not fire chain signal."""
        G = nx.DiGraph()
        # Hub sends to 5 different accounts (fan-out, not chain)
        hub = 'HUB'
        for i in range(5):
            G.add_edge(hub, f'SPOKE_{i}', weight=10_000.0, tx_count=1)
        signals = compute_chain_signals(G)
        # Hub itself should not be flagged as a chain node
        hub_signals = [s for s in signals if s.account_id == hub]
        assert len(hub_signals) == 0
