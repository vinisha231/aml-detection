"""
backend/tests/test_geographic_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the geographic anomaly detection rule.

Tests verify:
  - Account in high-risk branch is flagged
  - Offshore counterparty triggers the rule
  - Benign domestic transactions are NOT flagged
  - Score is bounded 0–100
  - Signal type is correct
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.geographic_rule import check_geographic_anomaly


def make_tx(
    sender: str,
    receiver: str,
    hours_offset: int = 0,
    amount: float = 10_000.0,
) -> dict:
    base = datetime(2024, 6, 1, 12, 0)
    return {
        'transaction_id':      f'TX_{sender}_{hours_offset}',
        'sender_account_id':   sender,
        'receiver_account_id': receiver,
        'amount':              amount,
        'transaction_type':    'WIRE',
        'transaction_date':    base + timedelta(hours=hours_offset),
        'is_suspicious':       False,
    }


class TestGeographicRule:

    def test_offshore_branch_account_flagged(self):
        """Account registered at OFC branch is flagged even with benign transactions."""
        txs = [make_tx('ACC_A', 'ACC_B', hours_offset=i) for i in range(5)]
        result = check_geographic_anomaly('ACC_A', txs, account_branch='OFC_CAYMAN')
        assert result is not None
        assert 'OFC_CAYMAN' in result.evidence

    def test_offshore_counterparty_flagged(self):
        """Sending money to an OFC_ prefixed account triggers the rule."""
        txs = [
            make_tx('ACC_A', 'OFC_001', hours_offset=0),
            make_tx('ACC_A', 'OFC_002', hours_offset=12),
        ]
        result = check_geographic_anomaly('ACC_A', txs, account_branch='NYC_001')
        assert result is not None

    def test_domestic_transactions_not_flagged(self):
        """Normal domestic transactions (ACC_ prefix) should not trigger geographic rule."""
        txs = [
            make_tx('ACC_A', 'ACC_B', hours_offset=i * 10)
            for i in range(10)
        ]
        result = check_geographic_anomaly('ACC_A', txs, account_branch='NYC_001')
        assert result is None

    def test_signal_type(self):
        """Signal type must be 'geographic'."""
        txs = [make_tx('ACC_A', 'OFC_001', hours_offset=0)]
        result = check_geographic_anomaly('ACC_A', txs, account_branch='OFC_TEST')
        assert result is not None
        assert result.signal_type == 'geographic'

    def test_score_bounded(self):
        """Score must be between 0 and 100."""
        txs = [make_tx('ACC_A', f'OFC_{i:03d}', hours_offset=i) for i in range(20)]
        result = check_geographic_anomaly('ACC_A', txs, account_branch='OFC_CAYMAN')
        if result:
            assert 0 <= result.score <= 100

    def test_empty_transactions(self):
        """Empty transactions → None even with offshore branch."""
        result = check_geographic_anomaly('ACC_A', [], account_branch='OFC_001')
        assert result is None
