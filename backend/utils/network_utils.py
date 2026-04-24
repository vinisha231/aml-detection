"""
backend/utils/network_utils.py
─────────────────────────────────────────────────────────────────────────────
Network/graph utility functions shared across detection modules.

Why separate from graph_utils.py?
  graph_utils.py handles NetworkX graph operations (percentile thresholds,
  graph summarization). This module handles higher-level graph construction
  and network analysis helpers — building the transaction graph from raw data,
  extracting ego-networks, etc.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import networkx as nx
from collections import defaultdict


def build_transaction_graph(transactions: list[dict]) -> nx.DiGraph:
    """
    Build a directed transaction graph from a list of transaction dicts.

    Each edge represents the relationship between sender and receiver.
    Edge attributes:
      - weight: total USD volume transferred (sum of all transactions)
      - tx_count: number of transactions between this pair

    Args:
        transactions: List of transaction dicts with sender_account_id,
                      receiver_account_id, and amount fields.

    Returns:
        Directed weighted graph (DiGraph).
    """
    G = nx.DiGraph()

    # Accumulate edge data in a dict before adding to graph
    # This lets us aggregate multiple transactions into a single edge
    edge_data: dict[tuple[str, str], dict] = defaultdict(lambda: {'weight': 0.0, 'tx_count': 0})

    for tx in transactions:
        sender   = tx.get('sender_account_id', '')
        receiver = tx.get('receiver_account_id', '')
        amount   = float(tx.get('amount', 0) or 0)

        if not sender or not receiver or sender == receiver:
            continue  # Skip self-loops and missing data

        key = (sender, receiver)
        edge_data[key]['weight']   += amount
        edge_data[key]['tx_count'] += 1

    # Add all nodes and edges to the graph
    for (sender, receiver), data in edge_data.items():
        G.add_edge(sender, receiver, **data)

    return G


def get_ego_network(
    G:          nx.DiGraph,
    account_id: str,
    radius:     int = 2,
) -> nx.DiGraph:
    """
    Extract the ego-network for a specific account.

    The ego-network includes:
    - The account itself (ego)
    - All accounts within `radius` hops (alters)
    - All edges between accounts in this set

    This is what the GraphViewer shows — not the full network (which could
    have thousands of nodes), but the local neighborhood.

    Args:
        G:          The full transaction graph.
        account_id: The focal account (ego).
        radius:     Number of hops to include. Default 2 (2 degrees of separation).

    Returns:
        A subgraph containing only the ego and its neighborhood.
    """
    if account_id not in G:
        # Return an empty graph if the account doesn't exist
        return nx.DiGraph()

    # ego_graph gets the subgraph centered on account_id up to `radius` hops away
    # It works on the undirected version to capture both in- and out-neighbors
    undirected = G.to_undirected()
    ego_nodes  = nx.ego_graph(undirected, account_id, radius=radius).nodes()

    # Return the induced subgraph from the original directed graph
    # (preserves edge directionality)
    return G.subgraph(ego_nodes).copy()


def get_connected_components(G: nx.DiGraph) -> list[set[str]]:
    """
    Find weakly connected components in a directed transaction graph.

    Weakly connected = connected if you ignore edge direction.
    This groups accounts that are reachable from each other via any path.

    Money laundering networks are usually one connected component.
    Isolated accounts that never transact with suspicious accounts are
    unlikely to be involved.

    Args:
        G: The transaction graph.

    Returns:
        List of sets, each set being a group of connected account IDs.
    """
    return [set(c) for c in nx.weakly_connected_components(G)]


def account_degree_stats(G: nx.DiGraph, account_id: str) -> dict[str, int]:
    """
    Get in-degree, out-degree, and total degree for an account.

    Args:
        G:          The transaction graph.
        account_id: Account to query.

    Returns:
        Dict with keys 'in_degree', 'out_degree', 'total_degree'.
        Returns zeros if account not in graph.
    """
    if account_id not in G:
        return {'in_degree': 0, 'out_degree': 0, 'total_degree': 0}

    in_deg  = G.in_degree(account_id)
    out_deg = G.out_degree(account_id)
    return {
        'in_degree':    in_deg,
        'out_degree':   out_deg,
        'total_degree': in_deg + out_deg,
    }
