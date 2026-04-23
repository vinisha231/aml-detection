"""
backend/api/exceptions.py
─────────────────────────────────────────────────────────────────────────────
Custom exception handlers for the FastAPI application.

What are exception handlers?
  When an endpoint raises an exception that isn't caught, FastAPI
  would normally return a generic 500 Internal Server Error.

  Exception handlers let us intercept specific exceptions and return
  helpful, consistent error responses instead.

  Format we use:
  {
    "error": "Account not found",
    "detail": "No account with ID ACC_999999 exists in the database.",
    "status_code": 404
  }
─────────────────────────────────────────────────────────────────────────────
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors (malformed request bodies).

    Instead of returning Pydantic's verbose error format, we return
    a cleaner response that's easier for clients to parse.

    Example trigger:
        POST /dispositions/ACC_001
        Body: {"decision": "maybe"}  ← invalid decision value

    Returns a 422 response with a readable error message.
    """
    # Extract the first validation error for a clean message
    first_error = exc.errors()[0] if exc.errors() else {}
    field  = ".".join(str(x) for x in first_error.get("loc", ["unknown"]))
    msg    = first_error.get("msg", "Validation failed")

    return JSONResponse(
        status_code=422,
        content={
            "error":       "Validation Error",
            "detail":      f"Field '{field}': {msg}",
            "status_code": 422,
        }
    )


async def generic_error_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Catch-all handler for unhandled exceptions.

    In production, this would log to a monitoring system (Sentry, DataDog).
    In development, it returns the error message for debugging.

    Never expose internal details (stack traces, DB queries) in production.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error":       "Internal Server Error",
            "detail":      "An unexpected error occurred. Check the server logs.",
            "status_code": 500,
        }
    )
