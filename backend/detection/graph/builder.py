"""
backend/detection/graph/builder.py
─────────────────────────────────────────────────────────────────────────────
Builds a NetworkX DiGraph from transaction records.

The transaction graph is the foundation of ALL graph-based detection.
Every other graph signal file starts by calling build_transaction_graph().

Graph structure:
  - Nodes = bank account IDs (strings)
  - Edges = transactions (directed: sender → receiver)
  - Edge attributes: amount, date, transaction_id, typology

Building the graph on a weekly basis (batch pipeline):
  Transactions from the last 90 days are included.
  Older transactions are excluded to keep the graph current.
─────────────────────────────────────────────────────────────────────────────
"""

import networkx as nx
from datetime import datetime, timedelta
from typing import List, Optional


def build_transaction_graph(
    transactions: List[dict],
    lookback_days: int = 90,
    as_of_date: Optional[datetime] = None,
    min_amount: float = 0.0,
) -> nx.DiGraph:
    """
    Build a directed, weighted transaction graph from a list of transactions.

    Args:
        transactions:  All transaction dicts from the database.
        lookback_days: Only include transactions from this many days ago.
                       Default: 90 days (3 months). Set to 0 for all time.
        as_of_date:    Reference date for the lookback window.
                       Default: current datetime.
        min_amount:    Ignore transactions below this amount.
                       Helps reduce noise from tiny test transactions.

    Returns:
        nx.DiGraph where:
          - Each node is a string (account_id)
          - Each edge has attributes: weight, date, tx_id, typology

    Example:
        G = build_transaction_graph(all_transactions)
        print(G.number_of_nodes())  # 5,002 (5,000 + bank/payroll/utility accounts)
        print(G.number_of_edges())  # ~100,000
    """

    # Create an empty directed graph
    # DiGraph = Directed Graph (edges have direction: A→B ≠ B→A)
    G = nx.DiGraph()

    # Set the reference date for the time window
    if as_of_date is None:
        as_of_date = datetime.utcnow()

    # Calculate the earliest date we care about
    if lookback_days > 0:
        earliest_date = as_of_date - timedelta(days=lookback_days)
    else:
        earliest_date = datetime.min  # include all transactions

    # ── Add each transaction as a directed edge ───────────────────────────────
    included_count = 0
    skipped_count  = 0

    for tx in transactions:

        # Skip transactions outside the time window
        if tx["transaction_date"] < earliest_date:
            skipped_count += 1
            continue

        # Skip transactions below minimum amount
        if tx["amount"] < min_amount:
            skipped_count += 1
            continue

        sender_id   = tx["sender_account_id"]
        receiver_id = tx["receiver_account_id"]

        # Don't add self-loops (sender == receiver)
        # These can occur in test data and confuse graph algorithms
        if sender_id == receiver_id:
            skipped_count += 1
            continue

        # Add nodes if they don't exist yet
        # (NetworkX does this automatically when adding edges,
        #  but we also add them explicitly to ensure isolated nodes are included)
        if not G.has_node(sender_id):
            G.add_node(sender_id)
        if not G.has_node(receiver_id):
            G.add_node(receiver_id)

        # Add the edge (or update it if it already exists)
        # Multiple transactions between same accounts = MULTIGRAPH behavior
        # We aggregate by summing weights (total money flow between accounts)
        if G.has_edge(sender_id, receiver_id):
            # Edge already exists — update the weight (aggregate money flow)
            G[sender_id][receiver_id]["weight"]    += tx["amount"]
            G[sender_id][receiver_id]["tx_count"]  += 1
            # Keep the latest date for this edge
            if tx["transaction_date"] > G[sender_id][receiver_id]["latest_date"]:
                G[sender_id][receiver_id]["latest_date"] = tx["transaction_date"]
        else:
            # New edge — add with initial attributes
            G.add_edge(
                sender_id,
                receiver_id,
                weight=tx["amount"],          # total money flow (will be updated)
                tx_count=1,                   # number of transactions
                latest_date=tx["transaction_date"],
                # We store the typology of the first transaction as the edge typology
                # This is a simplification — an edge could have mixed typologies
                typology=tx.get("typology", "benign"),
            )

        included_count += 1

    # Log summary (useful for debugging)
    print(
        f"[GraphBuilder] Included {included_count} transactions, "
        f"skipped {skipped_count}. "
        f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges."
    )

    return G


def get_subgraph_for_account(
    G: nx.DiGraph,
    account_id: str,
    depth: int = 2
) -> nx.DiGraph:
    """
    Extract a subgraph showing an account and its neighborhood.

    Used by the dashboard to visualize one account's connections.

    Args:
        G:          The full transaction graph
        account_id: Center account
        depth:      How many hops to include (default: 2 = account + neighbors + neighbors' neighbors)

    Returns:
        A subgraph (DiGraph) with the account and all nodes within 'depth' hops.

    Example:
        # Get the 2-hop neighborhood of account ACC_000001
        subgraph = get_subgraph_for_account(G, "ACC_000001", depth=2)
        # Returns: ACC_000001 + all accounts it transacts with + THEIR counterparties
    """
    if account_id not in G:
        # Account has no transactions in the graph
        return nx.DiGraph()

    # Find all nodes within 'depth' hops
    # ego_graph returns the node + all neighbors within the specified radius
    # We look in both directions (undirected) so we see predecessors too
    G_undirected = G.to_undirected()
    ego = nx.ego_graph(G_undirected, account_id, radius=depth)

    # Return the subgraph with the original directed edges
    nodes_in_subgraph = set(ego.nodes())
    return G.subgraph(nodes_in_subgraph).copy()


def graph_to_dict(G: nx.DiGraph) -> dict:
    """
    Convert a NetworkX graph to a JSON-serializable dictionary.

    Used by the API to send graph data to the React frontend.

    Format:
        {
          "nodes": [{"id": "ACC_000001", ...}, ...],
          "links": [{"source": "ACC_000001", "target": "ACC_000002", "weight": 50000}, ...]
        }

    Args:
        G: NetworkX DiGraph to convert

    Returns:
        Dict with "nodes" and "links" keys (react-force-graph format)
    """
    nodes = []
    for node_id in G.nodes():
        node_data = dict(G.nodes[node_id])  # node attributes
        nodes.append({"id": node_id, **node_data})

    links = []
    for sender, receiver, edge_data in G.edges(data=True):
        links.append({
            "source":   sender,
            "target":   receiver,
            "weight":   round(edge_data.get("weight", 0), 2),
            "tx_count": edge_data.get("tx_count", 1),
            "typology": edge_data.get("typology", "benign"),
        })

    return {"nodes": nodes, "links": links}
