"""
backend/api/dependencies.py
─────────────────────────────────────────────────────────────────────────────
FastAPI dependency injection functions.

What is dependency injection in FastAPI?
  FastAPI's Depends() system lets you declare shared logic that runs before
  every endpoint handler. This is cleaner than repeating the same setup code
  in every route function.

  Common uses:
    - Database session management (get a session, use it, close it)
    - Authentication (verify a token, return the current user)
    - Rate limiting (check if the caller is throttled)
    - Pagination parameters (parse page/limit from query params)

Why use Depends() instead of just calling the function?
  1. Testability: In tests, you can override dependencies with mocks
     (app.dependency_overrides[get_db] = lambda: mock_session)
  2. Lifecycle management: FastAPI handles cleanup (e.g., session.close())
  3. Reusability: Same dependency used across many routes, defined once
  4. Documentation: FastAPI adds dependency parameters to the OpenAPI schema

How FastAPI handles generator dependencies:
  Functions that use `yield` are called "generator dependencies". FastAPI
  runs the code before yield (setup), injects the yielded value, then runs
  the code after yield (teardown) after the request completes — even on error.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

# Annotated and Generator are type-hint utilities
from typing import Annotated, Generator

# FastAPI's Depends and HTTPException are the core DI tools
from fastapi import Depends, HTTPException, Query

# Our SQLAlchemy session factory — creates database sessions
from backend.database.connection import SessionLocal


# ─── Database session dependency ──────────────────────────────────────────────

def get_db() -> Generator:
    """
    Yield a SQLAlchemy database session for the duration of a request.

    This is a generator dependency. FastAPI will:
    1. Call get_db() before the endpoint handler
    2. Inject the session into the handler as `db`
    3. After the response is sent, resume execution from `yield` for cleanup

    The try/finally ensures the session is always closed, even if an exception
    occurs during request handling. Failing to close sessions causes connection
    pool exhaustion.

    Usage in a route:
        @router.get('/items')
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    # Create a new session from our session factory
    db = SessionLocal()
    try:
        # Yield the session to the endpoint handler
        # Execution pauses here until the request completes
        yield db
    finally:
        # Always close the session after the request, releasing the connection
        # back to the pool. `finally` ensures this runs even on exceptions.
        db.close()


# ─── Pagination dependency ────────────────────────────────────────────────────

class PaginationParams:
    """
    Standard pagination parameters extracted from query string.

    Endpoints that return lists should use this dependency to get consistent
    page/limit behavior across the API.

    Example URL: GET /accounts?page=2&limit=20
    """

    def __init__(
        self,
        # Query() documents and validates the parameter in OpenAPI
        page:  int = Query(default=1,   ge=1,   description="Page number (1-indexed)"),
        limit: int = Query(default=20,  ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page   = page
        self.limit  = limit
        # Compute the SQL OFFSET from page number and limit
        # OFFSET = (page - 1) * limit
        # Page 1: offset 0, page 2: offset 20, page 3: offset 40, etc.
        self.offset = (page - 1) * limit


def get_pagination(
    page:  int = Query(default=1,  ge=1,   description="Page number (1-indexed)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginationParams:
    """
    Extract and validate pagination parameters from query string.

    Args:
        page:  Page number, 1-indexed. Minimum 1.
        limit: Items per page. Between 1 and 100.

    Returns:
        PaginationParams with page, limit, and computed offset.
    """
    return PaginationParams(page=page, limit=limit)


# Type alias for cleaner route signatures
# Instead of: Depends(get_pagination), you can write: Pagination
Pagination = Annotated[PaginationParams, Depends(get_pagination)]


# ─── Score filter dependency ──────────────────────────────────────────────────

def get_score_filter(
    min_score: float = Query(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Minimum risk score to include (0–100)",
    ),
    max_score: float = Query(
        default=100.0,
        ge=0.0,
        le=100.0,
        description="Maximum risk score to include (0–100)",
    ),
) -> tuple[float, float]:
    """
    Extract and validate min/max score filter from query string.

    Validates that min_score <= max_score to prevent nonsensical ranges.

    Args:
        min_score: Lower bound for risk score filter.
        max_score: Upper bound for risk score filter.

    Returns:
        Tuple of (min_score, max_score).

    Raises:
        HTTPException 400: If min_score > max_score.
    """
    if min_score > max_score:
        raise HTTPException(
            status_code=400,
            detail=f"min_score ({min_score}) cannot exceed max_score ({max_score})",
        )
    return (min_score, max_score)
