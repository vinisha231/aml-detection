"""
backend/tests/test_graph_builder.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the graph builder.

Tests cover:
- Empty transaction list → empty graph
- Transactions build correct nodes and edges
- Self-loops are excluded
- Lookback window filters old transactions
- Edge weight aggregation (multiple transactions same pair → one edge, summed weight)
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
import networkx as nx
from backend.detection.graph.builder import (
    build_transaction_graph,
    get_subgraph_for_account,
    graph_to_dict,
)


def make_tx(sender: str, receiver: str, amount: float, days_ago: float = 0.0) -> dict:
    """Helper: minimal transaction dict for graph tests."""
    return {
        "transaction_id":      f"TX_{sender}_{receiver}_{amount}",
        "sender_account_id":   sender,
        "receiver_account_id": receiver,
        "amount":              amount,
        "transaction_type":    "wire_transfer",
        "description":         "test",
        "transaction_date":    datetime.now() - timedelta(days=days_ago),
        "is_suspicious":       False,
        "typology":            "benign",
    }


class TestBuildTransactionGraph:

    def test_empty_transactions_returns_empty_graph(self):
        """No transactions → empty graph."""
        G = build_transaction_graph([])
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0

    def test_single_transaction_creates_two_nodes_one_edge(self):
        """One transaction A→B creates exactly 2 nodes and 1 edge."""
        txs = [make_tx("ACC_A", "ACC_B", 1000.0)]
        G = build_transaction_graph(txs)
        assert G.number_of_nodes() == 2
        assert G.number_of_edges() == 1
        assert G.has_edge("ACC_A", "ACC_B")

    def test_edge_weight_set_correctly(self):
        """Edge weight should equal the transaction amount."""
        txs = [make_tx("ACC_A", "ACC_B", 5000.0)]
        G = build_transaction_graph(txs)
        assert G["ACC_A"]["ACC_B"]["weight"] == 5000.0

    def test_multiple_txs_same_pair_aggregated(self):
        """Two transactions A→B should create ONE edge with summed weight."""
        txs = [
            make_tx("ACC_A", "ACC_B", 3000.0),
            make_tx("ACC_A", "ACC_B", 2000.0),
        ]
        G = build_transaction_graph(txs)
        assert G.number_of_edges() == 1  # one edge, not two
        assert G["ACC_A"]["ACC_B"]["weight"] == 5000.0   # weights summed
        assert G["ACC_A"]["ACC_B"]["tx_count"] == 2       # count tracked

    def test_self_loops_excluded(self):
        """Transaction where sender == receiver should be skipped."""
        txs = [make_tx("ACC_A", "ACC_A", 500.0)]  # self-loop
        G = build_transaction_graph(txs)
        assert G.number_of_edges() == 0  # no self-loops allowed

    def test_lookback_window_filters_old_txs(self):
        """Transactions older than lookback_days should be excluded."""
        txs = [
            make_tx("ACC_A", "ACC_B", 1000.0, days_ago=10),   # recent — should be included
            make_tx("ACC_C", "ACC_D", 2000.0, days_ago=100),  # old — should be excluded
        ]
        G = build_transaction_graph(txs, lookback_days=30)
        assert G.has_edge("ACC_A", "ACC_B")
        assert not G.has_edge("ACC_C", "ACC_D")

    def test_graph_is_directed(self):
        """The graph must be a directed graph (DiGraph)."""
        txs = [make_tx("ACC_A", "ACC_B", 1000.0)]
        G = build_transaction_graph(txs)
        assert isinstance(G, nx.DiGraph)
        # Directed: A→B exists, but B→A should NOT exist
        assert G.has_edge("ACC_A", "ACC_B")
        assert not G.has_edge("ACC_B", "ACC_A")


class TestGetSubgraphForAccount:

    def test_returns_empty_for_unknown_account(self):
        """Account not in the graph → empty subgraph."""
        txs = [make_tx("ACC_A", "ACC_B", 1000.0)]
        G = build_transaction_graph(txs)
        subgraph = get_subgraph_for_account(G, "ACC_UNKNOWN")
        assert subgraph.number_of_nodes() == 0

    def test_includes_account_and_neighbors(self):
        """Subgraph at depth=1 should include the center account and its neighbors."""
        txs = [
            make_tx("ACC_CENTER", "ACC_B", 1000.0),
            make_tx("ACC_C",      "ACC_CENTER", 500.0),
        ]
        G = build_transaction_graph(txs)
        subgraph = get_subgraph_for_account(G, "ACC_CENTER", depth=1)
        assert "ACC_CENTER" in subgraph.nodes()
        assert "ACC_B"      in subgraph.nodes()
        assert "ACC_C"      in subgraph.nodes()


class TestGraphToDict:

    def test_returns_nodes_and_links(self):
        """graph_to_dict should return a dict with 'nodes' and 'links' keys."""
        txs = [make_tx("ACC_A", "ACC_B", 1000.0)]
        G = build_transaction_graph(txs)
        result = graph_to_dict(G)
        assert "nodes" in result
        assert "links" in result

    def test_nodes_have_id_field(self):
        """Each node dict must have an 'id' field for react-force-graph."""
        txs = [make_tx("ACC_A", "ACC_B", 1000.0)]
        G = build_transaction_graph(txs)
        result = graph_to_dict(G)
        for node in result["nodes"]:
            assert "id" in node, f"Node missing 'id' field: {node}"

    def test_links_have_source_target_weight(self):
        """Each link must have source, target, and weight fields."""
        txs = [make_tx("ACC_A", "ACC_B", 5000.0)]
        G = build_transaction_graph(txs)
        result = graph_to_dict(G)
        for link in result["links"]:
            assert "source" in link
            assert "target" in link
            assert "weight" in link
