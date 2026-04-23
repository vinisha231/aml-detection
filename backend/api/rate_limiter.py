"""
backend/api/rate_limiter.py
─────────────────────────────────────────────────────────────────────────────
Simple in-memory rate limiter for the AML API.

Why rate limiting?
  Even an internal AML dashboard should have basic rate limiting:
  1. Prevents accidental runaway scripts from hammering the API
  2. Protects against denial-of-service from misconfigured clients
  3. Ensures analyst A's bulk CSV export doesn't slow down analyst B's
     real-time account investigation

This is a TOKEN BUCKET implementation:
  - Each IP address has a bucket that holds up to MAX_TOKENS tokens
  - Tokens refill at REFILL_RATE tokens per second
  - Each request costs 1 token
  - If the bucket is empty, the request is rejected with 429 Too Many Requests

Token bucket vs. fixed window:
  Fixed window: "100 requests per minute". At second 59, you could send
  all 100. Then at second 61, another 100. 200 requests in 2 seconds.

  Token bucket: tokens accumulate continuously. No sudden burst at window boundary.
  Smoother and fairer for the server.

Implementation note:
  This uses a dict in memory — not suitable for multi-process deployments
  (where each process has its own dict). For production, use Redis with
  the INCR + EXPIRE pattern or a dedicated rate limiting library.
─────────────────────────────────────────────────────────────────────────────
"""

import time
from threading import Lock
from collections import defaultdict

from fastapi import Request, HTTPException


# ─── Configuration ────────────────────────────────────────────────────────────

# Maximum tokens per client (burst capacity)
MAX_TOKENS = 60

# Tokens added per second (steady-state rate)
REFILL_RATE = 10  # 10 req/sec sustained, 60 req burst

# Endpoints that are NOT rate limited (monitoring, ping)
EXEMPT_PATHS = {'/health/ping', '/health', '/'}


# ─── Token bucket store ───────────────────────────────────────────────────────

class TokenBucket:
    """Thread-safe token bucket for one client IP."""

    __slots__ = ('tokens', 'last_refill', 'lock')

    def __init__(self):
        self.tokens      = float(MAX_TOKENS)  # start full
        self.last_refill = time.monotonic()
        self.lock        = Lock()

    def consume(self) -> bool:
        """
        Try to consume one token. Returns True if allowed, False if rate-limited.
        Thread-safe via Lock.
        """
        with self.lock:
            # Add tokens for time elapsed since last request
            now      = time.monotonic()
            elapsed  = now - self.last_refill
            self.tokens = min(MAX_TOKENS, self.tokens + elapsed * REFILL_RATE)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True  # request allowed
            return False     # bucket empty — rate limited


# Global dict: IP → TokenBucket
# defaultdict automatically creates a new bucket for new IPs
_buckets: dict[str, TokenBucket] = defaultdict(TokenBucket)
_buckets_lock = Lock()


# ─── Middleware ───────────────────────────────────────────────────────────────

async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware that applies rate limiting to every request.

    Extracts the client IP from the request and checks their token bucket.
    If they're within limits, the request proceeds. Otherwise, returns 429.

    For requests behind a reverse proxy (nginx, CloudFlare), the real
    client IP is in X-Forwarded-For header. We check that first.
    """
    # Exempt monitoring endpoints from rate limiting
    if request.url.path in EXEMPT_PATHS:
        return await call_next(request)

    # Get client IP (handle reverse proxy headers)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        client_ip = forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.client.host if request.client else 'unknown'

    # Check rate limit
    bucket = _buckets[client_ip]
    if not bucket.consume():
        raise HTTPException(
            status_code=429,
            detail={
                'error':   'Rate limit exceeded',
                'message': f'Too many requests. Limit: {REFILL_RATE} req/sec sustained, {MAX_TOKENS} burst.',
                'retry_after': round(1.0 / REFILL_RATE, 1),
            },
        )

    return await call_next(request)
