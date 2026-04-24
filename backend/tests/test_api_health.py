"""
backend/tests/test_api_health.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the /health and /health/ping endpoints.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.api.health import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestHealthPing:

    def test_ping_returns_200(self):
        """GET /health/ping should always return 200."""
        resp = client.get('/health/ping')
        assert resp.status_code == 200

    def test_ping_returns_pong(self):
        resp = client.get('/health/ping')
        data = resp.json()
        assert data.get('status') == 'ok'


class TestHealthCheck:

    def test_health_structure(self):
        """GET /health should return a dict with at least a status field."""
        resp = client.get('/health')
        # May be 200 or 503 depending on DB state — just check structure
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert 'status' in data
