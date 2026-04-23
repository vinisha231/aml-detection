"""
backend/api/main.py
─────────────────────────────────────────────────────────────────────────────
FastAPI application entry point.

This file:
  1. Creates the FastAPI app instance
  2. Configures CORS (so React can call our API)
  3. Registers all routers (queue, accounts, dispositions)
  4. Starts the database on first run

Run with:
    uvicorn backend.api.main:app --reload --port 8000

Then visit:
    http://localhost:8000/docs    ← Interactive API documentation (Swagger UI)
    http://localhost:8000/redoc  ← Alternative docs format
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os

# Add project root to Python path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import queue, accounts, dispositions
from ..database.schema import get_engine, create_all_tables


# ── Create FastAPI application ────────────────────────────────────────────────
app = FastAPI(
    title="AML Detection API",
    description="""
    Anti-Money Laundering Detection System API.

    Provides risk scores, signals, and evidence for bank account monitoring.
    Supports analyst workflow: review queue → account detail → disposition.

    Authentication: None (this is a portfolio project — add JWT in production).
    """,
    version="1.0.0",
    docs_url="/docs",    # Swagger UI at /docs
    redoc_url="/redoc",  # ReDoc at /redoc
)


# ── CORS configuration ─────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing.
# Without this, the browser blocks our React app from calling our FastAPI.
# Because React runs on localhost:5173 and FastAPI on localhost:8000 — different "origins".

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite dev server
        "http://localhost:3000",    # Create React App
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],   # allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],   # allow all headers
)


# ── Register routers ──────────────────────────────────────────────────────────
# Each router handles a different section of the API.
# Prefixes are defined in the router files, so:
#   queue.router     → /queue/*
#   accounts.router  → /accounts/*
#   dispositions.router → /dispositions/*

app.include_router(queue.router)
app.include_router(accounts.router)
app.include_router(dispositions.router)


# ── Startup event ─────────────────────────────────────────────────────────────
# This runs once when the API server starts.
# It ensures the database tables exist before any requests come in.

@app.on_event("startup")
def startup_event():
    """Initialize database on API startup."""
    try:
        engine = get_engine("data/aml.db")
        create_all_tables(engine)
        print("[API] Database initialized successfully.")
    except Exception as e:
        print(f"[API] Warning: Database initialization failed: {e}")


# ── Root endpoint ─────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """
    Root endpoint — health check.
    Returns API name and documentation links.
    """
    return {
        "name":    "AML Detection API",
        "version": "1.0.0",
        "status":  "running",
        "docs":    "/docs",
        "endpoints": {
            "queue":        "/queue",
            "stats":        "/queue/stats",
            "account":      "/accounts/{account_id}",
            "account_graph":"/accounts/{account_id}/graph",
            "disposition":  "/dispositions/{account_id}",
            "fpr":          "/queue/false-positive-rates",
        }
    }


@app.get("/health")
def health():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy"}
