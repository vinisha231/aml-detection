"""
backend/api/routes/dispositions.py
─────────────────────────────────────────────────────────────────────────────
API endpoints for analyst disposition decisions.

The disposition workflow is the feedback loop:
  - Analyst reviews account detail
  - Clicks "Escalate to SAR" or "Dismiss — False Positive"
  - Optionally adds a note explaining their reasoning
  - Decision is saved to database
  - This data feeds into false positive rate calculation

Endpoints:
  POST /dispositions/{account_id}  — record a disposition decision
  GET  /dispositions/{account_id}  — get disposition history for an account
─────────────────────────────────────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..models import DispositionRequest
from ...database.schema import get_engine, get_session_factory
from ...database.queries import get_account, record_disposition

router = APIRouter(prefix="/dispositions", tags=["dispositions"])


def get_db():
    """Database session dependency."""
    engine = get_engine("data/aml.db")
    Session = get_session_factory(engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@router.post("/{account_id}")
def create_disposition(
    account_id: str,
    body:       DispositionRequest,
    db:         Session = Depends(get_db)
):
    """
    Record an analyst's disposition decision for an account.

    This is the most important user action in the dashboard.
    It:
      1. Updates the account's disposition field
      2. Inserts a row into the dispositions history table
      3. This history is used to calculate false positive rates per rule

    Request body:
      { "decision": "escalated" | "dismissed", "note": "optional text" }

    Returns:
      { "success": true, "account_id": "...", "decision": "..." }

    Raises:
        404: Account not found
        400: Invalid decision value
    """
    # Verify account exists
    account = get_account(db, account_id)
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=f"Account {account_id} not found"
        )

    # Record the decision
    try:
        record_disposition(
            session=db,
            account_id=account_id,
            decision=body.decision,
            note=body.note,
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success":    True,
        "account_id": account_id,
        "decision":   body.decision,
        "message":    f"Account {account_id} marked as {body.decision}.",
    }


@router.delete("/{account_id}")
def undo_disposition(
    account_id: str,
    db:         Session = Depends(get_db)
):
    """
    Undo a disposition decision — reset account to unreviewed state.

    Analysts sometimes make mistakes. This endpoint lets them take back
    a disposition and put the account back in the unreviewed queue.

    Returns:
      { "success": true, "account_id": "..." }
    """
    account = get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    if account.disposition is None:
        raise HTTPException(
            status_code=400,
            detail=f"Account {account_id} has no disposition to undo"
        )

    account.disposition      = None
    account.disposition_note = None
    account.disposition_at   = None
    db.commit()

    return {
        "success":    True,
        "account_id": account_id,
        "message":    f"Disposition for {account_id} cleared.",
    }
