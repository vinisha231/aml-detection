"""
backend/api/middleware.py
─────────────────────────────────────────────────────────────────────────────
FastAPI middleware for logging, timing, and error handling.

What is middleware?
  Middleware is code that runs BEFORE and AFTER every API request.
  Think of it as a wrapper around all your endpoint functions.

  Request flow with middleware:
  Client → Middleware → Endpoint function → Middleware → Client

  Use cases:
  1. Logging: log every request and response time
  2. Authentication: check if the user is logged in
  3. Error handling: catch unhandled exceptions and return clean error responses
  4. CORS: handle Cross-Origin Resource Sharing (already done in main.py)
─────────────────────────────────────────────────────────────────────────────
"""

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Set up Python's built-in logging system
# This writes to the console during development
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("aml_api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every API request with timing information.

    Logs format:
        12:34:56 [INFO] GET /queue → 200 (45ms)
        12:34:57 [INFO] GET /accounts/ACC_001 → 200 (123ms)
        12:34:58 [INFO] POST /dispositions/ACC_001 → 200 (12ms)

    This is useful for:
    - Debugging: see which endpoints are being called
    - Performance: identify slow endpoints (graph building can be slow)
    - Monitoring: in production, this log is sent to a log aggregation system
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Called for every request. Wraps the actual endpoint function.

        Args:
            request:   The incoming HTTP request
            call_next: Function that calls the next handler (the endpoint)

        Returns:
            The HTTP response
        """
        # Record start time
        start_time = time.time()

        # Call the actual endpoint
        response = await call_next(request)

        # Calculate how long it took
        duration_ms = (time.time() - start_time) * 1000

        # Log the request
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} "
            f"({duration_ms:.0f}ms)"
        )

        # Add timing header to response (useful for browser DevTools)
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.0f}"

        return response
