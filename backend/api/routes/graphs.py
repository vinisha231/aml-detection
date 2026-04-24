"""
backend/api/routes/graphs.py
─────────────────────────────────────────────────────────────────────────────
API endpoint for serving transaction network graph data.

GET /accounts/{account_id}/graph
  Returns the ego-network for a specific account — the account itself plus
  all accounts within 2 hops, with edges representing money flows.

  Response shape (matches GraphViewer component expectations):
  {
    "nodes": [
      { "id": "ACC_001", "risk_score": 75.2, "typology": "structuring" },
      ...
    ],
    "links": [
      { "source": "ACC_001", "target": "ACC_002", "weight": 50000, "tx_count": 3 },
      ...
    ]
  }

Why separate from the accounts router?
  Graph computation is expensive (NetworkX ego-network extraction, up to O(V+E)).
  Keeping it in a dedicated router makes it easier to add caching or rate limiting
  to just this endpoint in the future.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.database.models import Account, Transaction
from backend.utils.network_utils import build_transaction_graph, get_ego_network

router = APIRouter(prefix='/accounts', tags=['graphs'])


@router.get('/{account_id}/graph')
def get_account_graph(
    account_id: str,
    db:         Session = Depends(get_db),
    radius:     int     = 2,
) -> dict:
    """
    Return the transaction network graph centered on the given account.

    Args:
        account_id: The focal account ID (the ego node).
        db:         Database session (injected by FastAPI).
        radius:     Number of hops to include. Default 2. Capped at 3 for performance.

    Returns:
        JSON with 'nodes' (list of account dicts) and 'links' (list of edge dicts).

    Raises:
        HTTPException 404: If the account doesn't exist.
    """
    # Validate the account exists
    account = db.query(Account).filter(Account.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    # Cap radius to avoid extremely large subgraphs
    radius = min(radius, 3)

    # Load all transactions from the database
    # In production, we'd limit to recent transactions or cache the graph
    transactions = db.query(Transaction).all()
    tx_dicts = [
        {
            'sender_account_id':   tx.sender_account_id,
            'receiver_account_id': tx.receiver_account_id,
            'amount':              float(tx.amount or 0),
        }
        for tx in transactions
    ]

    # Build the full transaction graph, then extract ego-network
    full_graph = build_transaction_graph(tx_dicts)
    ego_graph  = get_ego_network(full_graph, account_id, radius=radius)

    # Load account metadata for all nodes in the ego-network
    node_ids = list(ego_graph.nodes())
    accounts_in_graph = {
        acc.account_id: acc
        for acc in db.query(Account).filter(Account.account_id.in_(node_ids)).all()
    }

    # Build nodes list
    nodes = []
    for node_id in node_ids:
        acc = accounts_in_graph.get(node_id)
        nodes.append({
            'id':         node_id,
            'risk_score': float(acc.risk_score or 0) if acc else 0.0,
            'typology':   acc.typology if acc else None,
            'is_focal':   node_id == account_id,
        })

    # Build links list
    links = []
    for source, target, data in ego_graph.edges(data=True):
        links.append({
            'source':   source,
            'target':   target,
            'weight':   data.get('weight', 0),
            'tx_count': data.get('tx_count', 1),
        })

    return {'nodes': nodes, 'links': links}
