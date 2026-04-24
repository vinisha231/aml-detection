"""
backend/api/middleware.py
─────────────────────────────────────────────────────────────────────────────
Custom FastAPI middleware for request logging and timing.

What is middleware?
  Middleware is code that runs for EVERY request before it reaches your route
  handler, and for EVERY response before it's sent back to the client.

  Think of it as a pipeline:
    Request → Middleware A → Middleware B → Route Handler → Middleware B → Middleware A → Response

  FastAPI uses Starlette's middleware system under the hood.

Why request logging middleware?
  Logs every request with timing info. This tells you:
  - Which endpoints are being called (usage analytics)
  - How fast each endpoint responds (performance monitoring)
  - Which requests are failing (error tracking)

  Without this, you can only see errors — not the traffic pattern that led to them.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

# time module for measuring request duration
import time

# logging for the request log output
import logging

# Starlette types — FastAPI is built on Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Our logging utility for consistent format
from backend.utils.logging_utils import get_logger

# Module-level logger — named for this module
logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with method, path, status code, and duration.

    Extends BaseHTTPMiddleware which handles the async plumbing.
    We only need to implement dispatch(), which wraps the actual request handling.
    """

    async def dispatch(
        self,
        request:  Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Called for every request. Measures time and logs the result.

        Args:
            request:   The incoming HTTP request (method, path, headers, body).
            call_next: Function that passes the request to the next handler.
                       Awaiting it runs the route handler and returns a response.

        Returns:
            The HTTP response (possibly modified — we don't modify it here).
        """
        # Record start time before passing to the route handler
        start_time = time.perf_counter()

        # await call_next runs the actual route handler (and any other middleware)
        # This is where the database queries and business logic happen
        response = await call_next(request)

        # Record end time after the response is generated
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Choose log level based on HTTP status code
        # 4xx = client errors, 5xx = server errors → both deserve WARNING or above
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Log the request in a structured, grep-friendly format
        logger.log(
            log_level,
            "http | %s %s → %d | %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        # Add the processing time as a response header
        # This lets frontend developers see how long the API took
        # without needing server logs (useful in browser DevTools)
        response.headers['X-Process-Time-Ms'] = f'{duration_ms:.1f}'

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security-related HTTP headers to every response.

    Why security headers?
      These headers instruct browsers to apply security policies that reduce
      XSS, clickjacking, and MIME-sniffing attack surface.

      They're a defense-in-depth measure — our React frontend already sanitizes
      output, but headers provide an extra layer at the browser level.
    """

    async def dispatch(
        self,
        request:  Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        # Prevent the page from being embedded in an iframe (clickjacking protection)
        response.headers['X-Frame-Options'] = 'DENY'

        # Prevent browsers from guessing content type (MIME sniffing protection)
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Only include the origin (not full URL) in the Referer header for cross-origin requests
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response
