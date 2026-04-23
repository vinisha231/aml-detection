"""
backend/tests/test_graph_utils.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for graph utility functions.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from backend.detection.graph.graph_utils import (
    percentile_threshold,
    log_normalise_score,
    graph_summary,
    subgraph_density,
    get_top_k_nodes,
)


class TestPercentileThreshold:

    def test_empty_returns_zero(self):
        assert percentile_threshold([], 90) == 0.0

    def test_90th_percentile(self):
        values = list(range(1, 11))  # [1, 2, ..., 10]
        # 90th percentile of 10 values → index 9 → value 10
        result = percentile_threshold(values, 90)
        assert result >= 9  # flexible due to rounding

    def test_0th_percentile_returns_minimum(self):
        values = [3, 1, 4, 1, 5, 9]
        assert percentile_threshold(values, 0) == 1

    def test_100th_percentile_returns_maximum(self):
        values = [3, 1, 4, 1, 5, 9]
        assert percentile_threshold(values, 100) == 9


class TestLogNormaliseScore:

    def test_min_value_returns_out_min(self):
        result = log_normalise_score(0.0, 0.0, 1.0, out_min=30.0, out_max=95.0)
        assert result == pytest.approx(30.0)

    def test_max_value_returns_out_max(self):
        result = log_normalise_score(1.0, 0.0, 1.0, out_min=30.0, out_max=95.0)
        assert abs(result - 95.0) < 1.0  # near max

    def test_output_within_range(self):
        for v in [0.001, 0.01, 0.1, 0.5, 1.0]:
            result = log_normalise_score(v, 0.0, 1.0)
            assert 0 <= result <= 100

    def test_higher_value_scores_higher(self):
        low  = log_normalise_score(0.01, 0.0, 1.0)
        high = log_normalise_score(0.5,  0.0, 1.0)
        assert high > low


class TestGraphSummary:

    def test_empty_graph(self):
        G = nx.DiGraph()
        result = graph_summary(G)
        assert result['nodes'] == 0
        assert result['edges'] == 0

    def test_basic_graph(self):
        G = nx.DiGraph()
        G.add_edge('A', 'B', weight=100)
        G.add_edge('B', 'C', weight=200)
        result = graph_summary(G)
        assert result['nodes'] == 3
        assert result['edges'] == 2


class TestSubgraphDensity:

    def test_fully_connected_returns_one(self):
        G = nx.complete_graph(4, create_using=nx.DiGraph())
        # All 4 nodes, all possible edges (4*3 = 12)
        density = subgraph_density(G, set(G.nodes()))
        assert density == pytest.approx(1.0, abs=0.01)

    def test_no_edges_returns_zero(self):
        G = nx.DiGraph()
        G.add_node('A')
        G.add_node('B')
        density = subgraph_density(G, {'A', 'B'})
        assert density == 0.0

    def test_single_node_returns_zero(self):
        G = nx.DiGraph()
        G.add_node('A')
        assert subgraph_density(G, {'A'}) == 0.0


class TestGetTopKNodes:

    def test_returns_top_k(self):
        scores = {'A': 90.0, 'B': 70.0, 'C': 50.0, 'D': 30.0}
        result = get_top_k_nodes(scores, k=2)
        assert len(result) == 2
        assert result[0][0] == 'A'
        assert result[1][0] == 'B'

    def test_threshold_filters_low_scores(self):
        scores = {'A': 80.0, 'B': 40.0, 'C': 20.0}
        result = get_top_k_nodes(scores, k=10, threshold=50.0)
        assert len(result) == 1
        assert result[0][0] == 'A'

    def test_empty_returns_empty(self):
        assert get_top_k_nodes({}, k=5) == []
