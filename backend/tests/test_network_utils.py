"""
backend/tests/test_network_utils.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for backend/utils/network_utils.py
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.utils.network_utils import (
    build_transaction_graph,
    get_ego_network,
    get_connected_components,
    account_degree_stats,
)


def make_tx(sender: str, receiver: str, amount: float = 1_000.0):
    return {
        'sender_account_id':   sender,
        'receiver_account_id': receiver,
        'amount':              amount,
        'transaction_date':    None,
    }


class TestBuildTransactionGraph:

    def test_builds_graph_from_transactions(self):
        txs = [make_tx('A', 'B'), make_tx('B', 'C')]
        G = build_transaction_graph(txs)
        assert G.has_edge('A', 'B')
        assert G.has_edge('B', 'C')

    def test_aggregates_multiple_transactions(self):
        """Two transactions between same pair should be summed into one edge."""
        txs = [make_tx('A', 'B', 1_000.0), make_tx('A', 'B', 2_000.0)]
        G = build_transaction_graph(txs)
        assert G['A']['B']['weight'] == pytest.approx(3_000.0)
        assert G['A']['B']['tx_count'] == 2

    def test_skips_self_loops(self):
        """A → A transactions should be ignored."""
        txs = [make_tx('A', 'A')]
        G = build_transaction_graph(txs)
        assert G.number_of_edges() == 0

    def test_empty_transactions_returns_empty_graph(self):
        G = build_transaction_graph([])
        assert G.number_of_nodes() == 0

    def test_directed_graph(self):
        """The result should be a directed graph."""
        txs = [make_tx('A', 'B')]
        G = build_transaction_graph(txs)
        assert isinstance(G, nx.DiGraph)


class TestGetEgoNetwork:

    def test_returns_neighborhood(self):
        G = nx.DiGraph()
        G.add_edge('CENTER', 'NEIGHBOR1')
        G.add_edge('CENTER', 'NEIGHBOR2')
        G.add_edge('FAR_NODE', 'UNRELATED')

        ego = get_ego_network(G, 'CENTER', radius=1)
        assert 'CENTER' in ego
        assert 'NEIGHBOR1' in ego
        assert 'FAR_NODE' not in ego

    def test_unknown_account_returns_empty(self):
        G = nx.DiGraph()
        ego = get_ego_network(G, 'NONEXISTENT')
        assert ego.number_of_nodes() == 0


class TestGetConnectedComponents:

    def test_finds_two_components(self):
        G = nx.DiGraph()
        G.add_edge('A', 'B')
        G.add_edge('C', 'D')
        components = get_connected_components(G)
        assert len(components) == 2

    def test_single_component(self):
        G = nx.DiGraph()
        G.add_edge('A', 'B')
        G.add_edge('B', 'C')
        components = get_connected_components(G)
        assert len(components) == 1


class TestAccountDegreeStats:

    def test_correct_degrees(self):
        G = nx.DiGraph()
        G.add_edge('A', 'HUB')
        G.add_edge('B', 'HUB')
        G.add_edge('HUB', 'C')

        stats = account_degree_stats(G, 'HUB')
        assert stats['in_degree']    == 2
        assert stats['out_degree']   == 1
        assert stats['total_degree'] == 3

    def test_unknown_account_returns_zeros(self):
        G = nx.DiGraph()
        stats = account_degree_stats(G, 'GHOST')
        assert stats == {'in_degree': 0, 'out_degree': 0, 'total_degree': 0}
