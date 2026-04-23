"""
backend/detection/graph/graph_utils.py
─────────────────────────────────────────────────────────────────────────────
Shared utility functions for graph analysis and signal generation.

This module provides helper functions used across multiple graph signals
to avoid code duplication:
  - Percentile threshold calculation
  - Score normalisation (0–100 from raw graph metrics)
  - Graph summarisation for logging
  - Subgraph density calculation

By centralising these utilities here, each signal module (pagerank_signal.py,
betweenness_signal.py, etc.) stays focused on its specific algorithm
without duplicating threshold and normalisation logic.
─────────────────────────────────────────────────────────────────────────────
"""

import math
from typing import Sequence
import networkx as nx


def percentile_threshold(values: Sequence[float], percentile: int) -> float:
    """
    Return the value at a given percentile of a sorted sequence.

    Example:
        percentile_threshold([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 90) → 90
        (the 90th percentile is the value at position 9/10 = index 9)

    Args:
        values:     Sequence of floats (does not need to be sorted).
        percentile: Integer 0–100.

    Returns:
        The value at the given percentile, or 0.0 if the sequence is empty.
    """
    if not values:
        return 0.0

    sorted_vals = sorted(values)
    idx = max(0, min(len(sorted_vals) - 1, int(len(sorted_vals) * percentile / 100)))
    return sorted_vals[idx]


def log_normalise_score(
    value:   float,
    min_val: float,
    max_val: float,
    out_min: float = 30.0,
    out_max: float = 95.0,
) -> float:
    """
    Map a value from [min_val, max_val] to [out_min, out_max] using log scale.

    Log scaling prevents extreme values from dominating:
    - Without log: PageRank of 0.001 vs 0.1 → scores of 1 vs 100
    - With log: compresses the extreme high values while preserving ordering

    Args:
        value:   The raw metric value to normalise.
        min_val: Minimum expected value (maps to out_min).
        max_val: Maximum expected value (maps to out_max).
        out_min: Output range minimum (default 30.0).
        out_max: Output range maximum (default 95.0).

    Returns:
        Normalised score in [out_min, out_max], capped.
    """
    if max_val <= min_val:
        return out_min

    if value <= min_val:
        return out_min

    # Log transform both the value and the range
    log_value   = math.log(max(1e-10, value   - min_val) + 1)
    log_max     = math.log(max(1e-10, max_val - min_val) + 1)

    # Linear interpolation in log space
    fraction = log_value / log_max if log_max > 0 else 0.0
    score    = out_min + fraction * (out_max - out_min)

    return min(out_max, max(out_min, score))


def graph_summary(G: nx.DiGraph) -> dict:
    """
    Return a summary dict of key graph statistics for logging.

    Args:
        G: Any NetworkX graph.

    Returns:
        Dict with nodes, edges, density, and average degree.
    """
    n = G.number_of_nodes()
    e = G.number_of_edges()

    if n == 0:
        return {'nodes': 0, 'edges': 0, 'density': 0.0, 'avg_degree': 0.0}

    # Density = edges / (n*(n-1)) for directed graphs
    max_edges = n * (n - 1)
    density   = e / max_edges if max_edges > 0 else 0.0
    avg_degree = (2 * e / n) if n > 0 else 0.0  # approximate for directed

    return {
        'nodes':      n,
        'edges':      e,
        'density':    round(density, 4),
        'avg_degree': round(avg_degree, 2),
    }


def subgraph_density(G: nx.DiGraph, nodes: set) -> float:
    """
    Calculate the fraction of possible edges that are internal to a subgraph.

    Internal density = (internal edges) / (n * (n-1))

    Values close to 1.0 indicate a tight cluster (many internal connections).
    Values close to 0.0 indicate a sparse or linear structure.

    Args:
        G:     The full transaction graph.
        nodes: Set of node IDs defining the subgraph.

    Returns:
        Internal edge density as a float in [0, 1].
    """
    n = len(nodes)
    if n <= 1:
        return 0.0

    max_internal = n * (n - 1)  # directed graph: n*(n-1) max edges

    internal_edges = sum(
        1 for u in nodes for v in nodes
        if u != v and G.has_edge(u, v)
    )

    return internal_edges / max_internal


def get_top_k_nodes(
    scores: dict[str, float],
    k: int,
    threshold: float = 0.0,
) -> list[tuple[str, float]]:
    """
    Return the top-K nodes by score, filtered to those above a threshold.

    Args:
        scores:    Dict mapping node_id → score.
        k:         Maximum number of nodes to return.
        threshold: Minimum score to include.

    Returns:
        List of (node_id, score) tuples, sorted by score descending.
    """
    filtered = [
        (node, score) for node, score in scores.items()
        if score >= threshold
    ]
    return sorted(filtered, key=lambda x: x[1], reverse=True)[:k]
