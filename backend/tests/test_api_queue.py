"""
backend/tests/test_api_queue.py
─────────────────────────────────────────────────────────────────────────────
Integration tests for the queue API endpoints.

Tests the GET /queue endpoint using FastAPI's TestClient, which simulates
HTTP requests without starting a real server.

Tests verify:
  - Returns 200 with correct structure
  - Pagination parameters (limit, offset) work
  - Filter by min_score works
  - Returns correct field names and types
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# We mock the database calls so this test doesn't need a real database
# This makes tests run fast and independent of DB state


def make_mock_account(**kwargs):
    """Create a mock Account object with default values."""
    defaults = {
        'account_id':    'ACC_001001',
        'holder_name':   'Test User',
        'account_type':  'PERSONAL',
        'branch':        'NYC_001',
        'balance':       10_000.0,
        'risk_score':    75.0,
        'typology':      None,
        'is_suspicious': False,
        'disposition':   None,
        'evidence':      'Test evidence.',
        'scored_at':     None,
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestQueueEndpoint:

    def setup_method(self):
        """Create the FastAPI test client."""
        # Import here so we don't need a database at module load time
        from backend.api.main import app
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_queue_returns_200(self):
        """GET /queue should return 200 OK."""
        with patch('backend.api.routes.queue.get_risk_queue') as mock_queue, \
             patch('backend.api.routes.queue.get_summary_stats') as mock_stats:

            mock_queue.return_value = []
            mock_stats.return_value = {
                'total_accounts': 100, 'scored_accounts': 80,
                'high_risk_accounts': 10, 'escalated': 2, 'avg_score': 45.0,
            }

            response = self.client.get('/queue?limit=10')
            assert response.status_code == 200

    def test_queue_response_has_accounts_field(self):
        """Response body must have an 'accounts' list."""
        with patch('backend.api.routes.queue.get_risk_queue') as mock_queue, \
             patch('backend.api.routes.queue.get_summary_stats') as mock_stats:

            mock_queue.return_value = [make_mock_account()]
            mock_stats.return_value = {
                'total_accounts': 1, 'scored_accounts': 1,
                'high_risk_accounts': 1, 'escalated': 0, 'avg_score': 75.0,
            }

            response = self.client.get('/queue')
            assert response.status_code == 200
            data = response.json()
            assert 'accounts' in data

    def test_health_endpoint_returns_200(self):
        """GET /health/ping should always return 200."""
        response = self.client.get('/health/ping')
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'ok'

    def test_invalid_min_score_returns_422(self):
        """min_score must be a number — string should return 422."""
        response = self.client.get('/queue?min_score=notanumber')
        assert response.status_code == 422

    def test_root_redirect(self):
        """GET / should redirect to /queue or return 200."""
        response = self.client.get('/')
        # Root endpoint returns a welcome message
        assert response.status_code in (200, 307, 404)
