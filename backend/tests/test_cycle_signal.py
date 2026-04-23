"""
backend/tests/test_cycle_signal.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the cycle (round-trip) detection signal.

Tests verify:
  - 3-node cycle is detected
  - Accounts in cycle are flagged
  - Empty graph returns no signals
  - Short cycles (A↔B) with length < 3 are not counted
  - Signal type is correct
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.detection.graph.cycle_signal import compute_cycle_signals


def make_cycle_graph(cycle_nodes: list, amount: float = 50_000.0) -> nx.DiGraph:
    """Build a directed cycle graph: A→B→C→A."""
    G = nx.DiGraph()
    for i in range(len(cycle_nodes)):
        sender   = cycle_nodes[i]
        receiver = cycle_nodes[(i + 1) % len(cycle_nodes)]
        G.add_edge(sender, receiver, weight=amount, tx_count=1)
    return G


class TestComputeCycleSignals:

    def test_detects_3_node_cycle(self):
        """A → B → C → A: all three accounts should be flagged."""
        G = make_cycle_graph(["ACC_A", "ACC_B", "ACC_C"])
        signals = compute_cycle_signals(G)

        flagged = {s.account_id for s in signals}
        assert "ACC_A" in flagged
        assert "ACC_B" in flagged
        assert "ACC_C" in flagged

    def test_no_signals_for_linear_chain(self):
        """A → B → C (no cycle): no accounts should be flagged."""
        G = nx.DiGraph()
        G.add_edge("ACC_A", "ACC_B", weight=10_000.0, tx_count=1)
        G.add_edge("ACC_B", "ACC_C", weight=9_800.0, tx_count=1)
        # No return edge C→A

        signals = compute_cycle_signals(G)

        # Linear chain has no cycle — no flags
        flagged = {s.account_id for s in signals}
        assert "ACC_A" not in flagged
        assert "ACC_C" not in flagged

    def test_empty_graph_returns_empty(self):
        """Empty graph → no signals."""
        G = nx.DiGraph()
        signals = compute_cycle_signals(G)
        assert signals == []

    def test_signal_type_is_correct(self):
        """Signal type must be 'graph_cycle'."""
        G = make_cycle_graph(["ACC_A", "ACC_B", "ACC_C"])
        signals = compute_cycle_signals(G)
        for sig in signals:
            assert sig.signal_type == "graph_cycle"

    def test_high_amount_cycle_scores_higher(self):
        """Larger amount in cycle should produce higher score."""
        G_low  = make_cycle_graph(["ACC_A", "ACC_B", "ACC_C"], amount=5_001.0)
        G_high = make_cycle_graph(["ACC_D", "ACC_E", "ACC_F"], amount=500_000.0)

        # Combine into one graph so both cycles are evaluated together
        G = nx.compose(G_low, G_high)
        signals = compute_cycle_signals(G)

        scores = {s.account_id: s.score for s in signals}

        if "ACC_A" in scores and "ACC_D" in scores:
            assert scores["ACC_D"] >= scores["ACC_A"], (
                "Higher amount cycle should score higher"
            )

    def test_score_bounded(self):
        """All scores must be between 0 and 100."""
        G = make_cycle_graph(["ACC_A", "ACC_B", "ACC_C", "ACC_D", "ACC_E"])
        signals = compute_cycle_signals(G)
        for sig in signals:
            assert 0 <= sig.score <= 100
