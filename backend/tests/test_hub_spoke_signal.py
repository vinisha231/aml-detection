"""
backend/tests/test_hub_spoke_signal.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the hub-and-spoke graph signal.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.detection.graph.hub_spoke_signal import compute_hub_spoke_signals


def build_star_graph(hub: str, n_spokes: int, amount: float = 50_000.0) -> nx.DiGraph:
    """
    One hub sends money to N spoke accounts.
    Each spoke has degree 1 (only connected to the hub).
    """
    G = nx.DiGraph()
    for i in range(n_spokes):
        spoke = f'ACC_SPOKE_{i}'
        G.add_edge(hub, spoke, weight=amount, tx_count=1)
    return G


class TestComputeHubSpokeSignals:

    def test_hub_with_many_spokes_flagged(self):
        """Hub sending to 15 low-degree spokes should be flagged."""
        G = build_star_graph('ACC_HUB', n_spokes=15)
        signals = compute_hub_spoke_signals(G)
        flagged = {s.account_id for s in signals}
        assert 'ACC_HUB' in flagged, "Hub account should be flagged"

    def test_small_graph_not_flagged(self):
        """Hub with only 3 spokes (below MIN_HUB_DEGREE of 8) should not flag."""
        G = build_star_graph('ACC_HUB', n_spokes=3)
        signals = compute_hub_spoke_signals(G)
        flagged = {s.account_id for s in signals}
        assert 'ACC_HUB' not in flagged

    def test_empty_graph_returns_empty(self):
        assert compute_hub_spoke_signals(nx.DiGraph()) == []

    def test_signal_type_is_correct(self):
        G = build_star_graph('ACC_HUB', n_spokes=12)
        signals = compute_hub_spoke_signals(G)
        for sig in signals:
            assert sig.signal_type == 'graph_hub_spoke'

    def test_scores_bounded(self):
        G = build_star_graph('ACC_HUB', n_spokes=50)
        signals = compute_hub_spoke_signals(G)
        for sig in signals:
            assert 0 <= sig.score <= 100

    def test_spoke_accounts_not_flagged(self):
        """Spoke accounts (degree 1, isolated) should not appear in signals."""
        G = build_star_graph('ACC_HUB', n_spokes=15)
        signals = compute_hub_spoke_signals(G)
        flagged = {s.account_id for s in signals}
        for i in range(15):
            assert f'ACC_SPOKE_{i}' not in flagged, f"Spoke account should not be flagged"
