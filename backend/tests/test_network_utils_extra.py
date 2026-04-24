"""
backend/tests/test_network_utils_extra.py
─────────────────────────────────────────────────────────────────────────────
Additional edge-case tests for network_utils — multi-hop ego networks,
large graphs, and edge weight aggregation.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.utils.network_utils import (
    build_transaction_graph,
    get_ego_network,
    get_connected_components,
)


class TestBuildTransactionGraphEdgeCases:

    def test_missing_sender_skipped(self):
        """Transactions missing sender_account_id should be skipped."""
        txs = [{'sender_account_id': None, 'receiver_account_id': 'B', 'amount': 100}]
        G = build_transaction_graph(txs)
        assert G.number_of_edges() == 0

    def test_missing_amount_treated_as_zero(self):
        txs = [{'sender_account_id': 'A', 'receiver_account_id': 'B'}]
        G = build_transaction_graph(txs)
        assert G.has_edge('A', 'B')
        assert G['A']['B']['weight'] == 0.0

    def test_large_aggregation(self):
        """1000 transactions between the same pair should aggregate correctly."""
        txs = [
            {'sender_account_id': 'S', 'receiver_account_id': 'R', 'amount': 1.0}
            for _ in range(1000)
        ]
        G = build_transaction_graph(txs)
        assert G['S']['R']['weight'] == pytest.approx(1000.0)
        assert G['S']['R']['tx_count'] == 1000


class TestEgoNetworkRadius:

    def test_radius_0_returns_only_ego(self):
        G = nx.DiGraph()
        G.add_edge('CENTER', 'OUTER')
        ego = get_ego_network(G, 'CENTER', radius=0)
        assert 'CENTER' in ego
        # With radius=0, only the center node should be included
        assert ego.number_of_nodes() == 1

    def test_radius_2_includes_second_hop(self):
        G = nx.DiGraph()
        G.add_edge('A', 'B')
        G.add_edge('B', 'C')
        ego = get_ego_network(G, 'A', radius=2)
        # A and B (1 hop) and C (2 hops) should all be included
        assert 'C' in ego


class TestConnectedComponents:

    def test_isolated_node_is_own_component(self):
        G = nx.DiGraph()
        G.add_node('SOLO')
        G.add_edge('A', 'B')
        components = get_connected_components(G)
        all_nodes = set().union(*components)
        assert 'SOLO' in all_nodes
        assert len(components) == 2

    def test_empty_graph_returns_empty(self):
        G = nx.DiGraph()
        components = get_connected_components(G)
        assert components == []
