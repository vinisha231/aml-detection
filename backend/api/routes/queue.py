"""
backend/api/routes/queue.py
─────────────────────────────────────────────────────────────────────────────
API endpoints for the risk queue.

The queue is the first screen analysts see every morning.
It shows accounts sorted by risk score, highest first.

Endpoints:
  GET /queue                 — paginated list of risky accounts
  GET /queue/stats           — summary stats for dashboard header
  GET /queue/false-positive-rates — per-rule FPR for the analytics screen
─────────────────────────────────────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..models import QueueResponse, AccountSummary, StatsResponse, FPREntry
from ...database.queries import get_risk_queue, get_summary_stats, get_false_positive_rate_by_rule
from ...database.schema import get_engine, get_session_factory
from ...detection.scoring import get_risk_tier

# Create a router — this groups related endpoints together
# We mount this router in main.py under the /queue prefix
router = APIRouter(prefix="/queue", tags=["queue"])


# ── Database dependency ────────────────────────────────────────────────────────
# FastAPI's dependency injection system.
# Any endpoint that needs the database just adds `db: Session = Depends(get_db)`.
# FastAPI automatically creates a new session, passes it to the endpoint,
# and closes it when the request is done.

def get_db():
    """
    Create and yield a database session.
    The 'yield' makes this a generator — FastAPI uses it as a context manager.
    """
    engine = get_engine("data/aml.db")
    Session = get_session_factory(engine)
    session = Session()
    try:
        yield session  # FastAPI passes this session to the endpoint
    finally:
        session.close()  # always close the session, even if an error occurred


@router.get("", response_model=QueueResponse)
def get_queue(
    page:        int = Query(1, ge=1, description="Page number (1-based)"),
    page_size:   int = Query(50, ge=1, le=200, description="Items per page"),
    min_score:   float = Query(0.0, ge=0, le=100, description="Minimum risk score"),
    disposition: Optional[str] = Query(
        "unreviewed",
        description="Filter by disposition: 'unreviewed', 'escalated', 'dismissed', 'all'"
    ),
    db: Session = Depends(get_db)
):
    """
    Get the paginated risk queue.

    Returns accounts sorted by risk score (highest first).
    Supports filtering by minimum score and disposition status.

    This is the main endpoint for the analyst's morning queue.
    """
    # Calculate offset for pagination
    offset = (page - 1) * page_size

    # Get accounts from database
    # We fetch page_size + 1 to check if there are more results
    accounts_raw = get_risk_queue(
        session=db,
        limit=page_size + 1,
        min_score=min_score,
        disposition_filter=disposition,
    )

    # Check if there are more results (for pagination)
    has_more = len(accounts_raw) > page_size
    accounts_raw = accounts_raw[:page_size]  # trim back to page_size

    # Convert SQLAlchemy objects to Pydantic response models
    accounts = []
    for acc in accounts_raw:
        accounts.append(AccountSummary(
            account_id=acc.account_id,
            holder_name=acc.holder_name,
            account_type=acc.account_type,
            risk_score=acc.risk_score,
            risk_tier=get_risk_tier(acc.risk_score or 0),
            top_signal=_extract_top_signal(acc.evidence),
            typology=acc.typology,
            disposition=acc.disposition,
            scored_at=acc.scored_at,
        ))

    return QueueResponse(
        accounts=accounts,
        total=len(accounts),
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """
    Get summary statistics for the dashboard header.

    Returns:
      - Total accounts
      - Scored accounts
      - High-risk accounts (score ≥ 70)
      - Escalated count
      - Average score
    """
    stats = get_summary_stats(db)
    return StatsResponse(**stats)


@router.get("/false-positive-rates", response_model=list[FPREntry])
def get_fpr(db: Session = Depends(get_db)):
    """
    Get false positive rate per rule.

    This tells analysts which rules generate the most noise.
    Useful for tuning detection thresholds.

    Returns rules sorted by false positive rate (worst first).
    """
    fpr_data = get_false_positive_rate_by_rule(db)
    return [FPREntry(**entry) for entry in fpr_data]


def _extract_top_signal(evidence: str) -> Optional[str]:
    """
    Extract the top signal name from an evidence string.

    The evidence string format is:
      "[STRUCTURING] ... | [VELOCITY] ..."
    We want to return just "STRUCTURING" for the queue display.

    Args:
        evidence: Full evidence string from the account record

    Returns:
        Signal name string or None
    """
    if not evidence:
        return None

    # Evidence starts with [SIGNAL_TYPE] — extract what's in the first brackets
    import re
    match = re.search(r"\[([^\]]+)\]", evidence)
    if match:
        return match.group(1)
    return None
