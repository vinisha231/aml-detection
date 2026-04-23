"""
backend/api/routes/accounts.py
─────────────────────────────────────────────────────────────────────────────
API endpoints for account detail views.

Endpoints:
  GET /accounts/{account_id}           — full account detail + transactions + signals
  GET /accounts/{account_id}/graph     — account subgraph for visualization
  GET /accounts/{account_id}/transactions — paginated transaction history
─────────────────────────────────────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..models import AccountDetailResponse, TransactionResponse, SignalResponse, GraphDataResponse
from ...database.schema import get_engine, get_session_factory, Account
from ...database.queries import (
    get_account,
    get_account_transactions,
    get_account_signals,
)
from ...detection.graph.builder import (
    build_transaction_graph,
    get_subgraph_for_account,
    graph_to_dict,
)
from ...database.schema import Transaction

router = APIRouter(prefix="/accounts", tags=["accounts"])


def get_db():
    """Database session dependency (same as in queue.py)."""
    engine = get_engine("data/aml.db")
    Session = get_session_factory(engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@router.get("/{account_id}", response_model=AccountDetailResponse)
def get_account_detail(
    account_id: str,
    tx_limit:   int = Query(50, ge=1, le=500, description="Max transactions to return"),
    db:         Session = Depends(get_db)
):
    """
    Get full detail for a single account.

    Returns:
      - Account info (name, type, balance, etc.)
      - Risk score and evidence string
      - Last 50 transactions (default)
      - All detection signals that fired on this account

    Used by the Account Detail screen in the dashboard.

    Raises:
        404 if account not found
    """
    # ── Fetch account ─────────────────────────────────────────────────────────
    account = get_account(db, account_id)
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=f"Account {account_id} not found"
        )

    # ── Fetch transactions ────────────────────────────────────────────────────
    transactions_raw = get_account_transactions(db, account_id, limit=tx_limit)
    transactions = [
        TransactionResponse(
            transaction_id=tx.transaction_id,
            sender_account_id=tx.sender_account_id,
            receiver_account_id=tx.receiver_account_id,
            amount=tx.amount,
            transaction_type=tx.transaction_type,
            description=tx.description,
            transaction_date=tx.transaction_date,
            is_suspicious=tx.is_suspicious,
            typology=tx.typology,
        )
        for tx in transactions_raw
    ]

    # ── Fetch signals ─────────────────────────────────────────────────────────
    signals_raw = get_account_signals(db, account_id)
    signals = [
        SignalResponse(
            signal_type=sig.signal_type,
            score=sig.score,
            weight=sig.weight,
            evidence=sig.evidence,
            confidence=sig.confidence,
            created_at=sig.created_at,
        )
        for sig in signals_raw
    ]

    # ── Build response ────────────────────────────────────────────────────────
    return AccountDetailResponse(
        account_id=account.account_id,
        holder_name=account.holder_name,
        account_type=account.account_type,
        branch=account.branch,
        opened_date=account.opened_date,
        balance=account.balance,
        is_suspicious=account.is_suspicious,
        typology=account.typology,
        risk_score=account.risk_score,
        evidence=account.evidence,
        scored_at=account.scored_at,
        disposition=account.disposition,
        disposition_note=account.disposition_note,
        disposition_at=account.disposition_at,
        transactions=transactions,
        signals=signals,
    )


@router.get("/{account_id}/graph", response_model=GraphDataResponse)
def get_account_graph(
    account_id: str,
    depth:      int = Query(2, ge=1, le=3, description="Graph depth (1-3 hops)"),
    db:         Session = Depends(get_db)
):
    """
    Get the transaction subgraph for an account.

    Returns nodes and links in react-force-graph format for visualization.

    Args:
        account_id: Center account
        depth:      How many hops to include (default: 2)

    Returns:
        {"nodes": [...], "links": [...]}
    """
    # Verify account exists
    account = get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    # Load all transactions (for graph building)
    all_transactions_raw = db.query(Transaction).all()
    all_transactions = [
        {
            "transaction_id":      tx.transaction_id,
            "sender_account_id":   tx.sender_account_id,
            "receiver_account_id": tx.receiver_account_id,
            "amount":              tx.amount,
            "transaction_type":    tx.transaction_type,
            "description":         tx.description,
            "transaction_date":    tx.transaction_date,
            "is_suspicious":       tx.is_suspicious,
            "typology":            tx.typology,
        }
        for tx in all_transactions_raw
    ]

    # Build the full graph
    G = build_transaction_graph(all_transactions, lookback_days=90)

    # Extract the subgraph around this account
    subgraph = get_subgraph_for_account(G, account_id, depth=depth)

    # Add risk score to each node for visualization (color coding in frontend)
    account_scores = {}
    for acc in db.query(Account).filter(
        Account.account_id.in_(list(subgraph.nodes()))
    ).all():
        account_scores[acc.account_id] = {
            "risk_score": acc.risk_score or 0,
            "holder_name": acc.holder_name,
            "typology": acc.typology,
        }

    # Add attributes to graph nodes for visualization
    for node_id in subgraph.nodes():
        if node_id in account_scores:
            subgraph.nodes[node_id].update(account_scores[node_id])
        else:
            subgraph.nodes[node_id]["holder_name"] = node_id
            subgraph.nodes[node_id]["risk_score"] = 0

    # Convert to JSON format
    graph_data = graph_to_dict(subgraph)
    return GraphDataResponse(**graph_data)
