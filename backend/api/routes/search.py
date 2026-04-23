"""
backend/api/routes/search.py
─────────────────────────────────────────────────────────────────────────────
Search endpoint for finding accounts by ID, name, or typology.

Endpoints:
  GET /search?q={query}&limit={N}
    Full-text search across:
      - account_id (exact prefix match)
      - holder_name (case-insensitive substring)
      - typology (exact match)

Why a search endpoint matters for analysts:
  The risk queue shows accounts sorted by score. But sometimes an analyst
  needs to find a SPECIFIC account (e.g., a customer called about an alert,
  or a SAR was filed and the analyst needs to check related accounts).

  Without search, the analyst would have to scroll through thousands of
  accounts or know the exact account ID. Search makes the workflow much
  more efficient.

Security note:
  SQLAlchemy's ORM with bound parameters prevents SQL injection.
  Never use f-strings or string concatenation to build SQL queries.
  The `.ilike()` method uses parameterized queries internally.
─────────────────────────────────────────────────────────────────────────────
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database.schema import get_session_factory, get_engine, Account

router = APIRouter(prefix='/search', tags=['search'])


def get_db():
    engine  = get_engine()
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@router.get('')
def search_accounts(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    db: Session = Depends(get_db),
):
    """
    Search for accounts matching the query string.

    Searches:
      1. account_id: exact prefix match (e.g., "ACC_00" matches "ACC_001234")
      2. holder_name: case-insensitive substring (e.g., "smith" matches "John Smith")
      3. typology: exact match (e.g., "structuring" returns all structuring accounts)

    Results are sorted by risk_score descending so highest-risk matches appear first.

    Args:
        q:     The search query string (1–100 characters).
        limit: Maximum number of results (1–100, default 20).
        db:    Database session (injected by FastAPI).

    Returns:
        List of account summary dicts with id, name, typology, score, disposition.
    """
    # Sanitize query for LIKE patterns
    # `%` and `_` are LIKE wildcards — escape them to treat as literals
    safe_q = q.replace('%', r'\%').replace('_', r'\_')

    accounts = (
        db.query(Account)
        .filter(
            or_(
                # Prefix match on account_id (e.g., "ACC_001" matches "ACC_001234")
                Account.account_id.ilike(f'{safe_q}%'),
                # Substring match on holder name
                Account.holder_name.ilike(f'%{safe_q}%'),
                # Exact match on typology
                Account.typology.ilike(safe_q),
            )
        )
        .order_by(Account.risk_score.desc().nullslast())
        .limit(limit)
        .all()
    )

    return [
        {
            'account_id':   acc.account_id,
            'holder_name':  acc.holder_name,
            'account_type': acc.account_type,
            'typology':     acc.typology,
            'risk_score':   round(acc.risk_score, 1) if acc.risk_score else None,
            'disposition':  acc.disposition,
            'is_suspicious': acc.is_suspicious,
        }
        for acc in accounts
    ]
