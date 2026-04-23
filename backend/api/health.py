"""
backend/api/health.py
─────────────────────────────────────────────────────────────────────────────
Health check endpoint for monitoring and container orchestration.

Why health checks matter:
  1. Docker / Kubernetes uses health checks to know if the container is ready
     to receive traffic. If the health check fails, the container is restarted.

  2. Load balancers route traffic only to healthy instances.

  3. Monitoring systems (Datadog, Grafana) alert when health checks fail.

  4. Integration test suites can wait for the server to be ready before
     sending requests.

The health check tests:
  - The API process is running (if we get here, it is)
  - The database is reachable (we run a simple query)
  - Core dependencies are importable (checked at startup via main.py)

Response format:
  200 OK: {"status": "healthy", "database": "connected", "accounts": 5000}
  503 Service Unavailable: {"status": "unhealthy", "detail": "Database connection failed"}
─────────────────────────────────────────────────────────────────────────────
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.database.schema import get_engine, Account, get_session_factory

router = APIRouter(tags=['health'])


@router.get('/health')
def health_check():
    """
    Comprehensive health check.

    Checks:
      1. Process is alive (implicit — if we get here, it is)
      2. Database file exists and is readable
      3. Accounts table has rows (pipeline has been run)

    Returns:
        200 with status details if healthy.
        503 if the database is unreachable.
    """
    try:
        engine  = get_engine()
        factory = get_session_factory(engine)
        session = factory()

        # Simple query — if this fails, DB is not reachable
        account_count = session.query(Account).count()
        session.close()

        return {
            'status':   'healthy',
            'database': 'connected',
            'accounts': account_count,
        }

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'detail': f'Database connection failed: {str(e)}',
            },
        )


@router.get('/health/ping')
def ping():
    """
    Lightweight ping endpoint — just confirms the process is alive.
    No database check. Used by load balancers for basic liveness.
    """
    return {'status': 'ok', 'message': 'pong'}
