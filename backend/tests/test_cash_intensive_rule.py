"""
backend/tests/test_cash_intensive_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the cash-intensive business rule.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.cash_intensive_rule import check_cash_intensive


def make_tx(
    account_id: str,
    amount: float,
    tx_type: str,
    days_offset: int = 0,
    hour: int = 10,
    is_inbound: bool = True,
) -> dict:
    base = datetime(2024, 5, 1, hour, 0)
    return {
        'transaction_id':      f'TX_{account_id}_{days_offset}_{tx_type}',
        'sender_account_id':   'OTHER' if is_inbound else account_id,
        'receiver_account_id': account_id if is_inbound else 'OTHER',
        'amount':              amount,
        'transaction_type':    tx_type,
        'transaction_date':    base + timedelta(days=days_offset),
        'is_suspicious':       False,
    }


class TestCashIntensiveRule:

    def test_high_cash_ratio_flagged(self):
        """Personal account: 90% cash deposits → flagged."""
        txs = [make_tx('ACC_A', 5_000.0, 'CASH_DEPOSIT', days_offset=i) for i in range(9)]
        txs.append(make_tx('ACC_A', 5_000.0, 'ACH', days_offset=10))
        result = check_cash_intensive('ACC_A', txs, account_type='PERSONAL')
        assert result is not None
        assert result.signal_type == 'cash_intensive'

    def test_low_cash_ratio_not_flagged(self):
        """Account with 30% cash deposits — within normal range."""
        txs = [make_tx('ACC_A', 2_000.0, 'CASH_DEPOSIT', days_offset=i) for i in range(3)]
        txs += [make_tx('ACC_A', 2_000.0, 'ACH', days_offset=i + 3) for i in range(7)]
        result = check_cash_intensive('ACC_A', txs, account_type='PERSONAL')
        assert result is None

    def test_after_hours_deposits_flagged(self):
        """Cash deposits at 4am (suspicious hour) contribute to score."""
        # Mix of cash and non-cash; all cash deposits are at 4am
        txs = [make_tx('ACC_A', 8_000.0, 'CASH_DEPOSIT', days_offset=i, hour=4) for i in range(8)]
        txs += [make_tx('ACC_A', 1_000.0, 'ACH', days_offset=i + 8) for i in range(2)]
        result = check_cash_intensive('ACC_A', txs, account_type='PERSONAL')
        assert result is not None
        # After-hours should be mentioned in evidence
        assert 'am' in result.evidence.lower() or '3–6' in result.evidence

    def test_outbound_transactions_excluded(self):
        """Outbound (sender) transactions should not count as deposits."""
        # All outbound — account is sending money, not receiving cash deposits
        txs = [make_tx('ACC_A', 8_000.0, 'CASH_DEPOSIT', is_inbound=False, days_offset=i) for i in range(10)]
        result = check_cash_intensive('ACC_A', txs)
        assert result is None

    def test_score_bounded(self):
        """Score must be between 0 and 100."""
        txs = [make_tx('ACC_A', 9_999.0, 'CASH_DEPOSIT', days_offset=i, hour=4) for i in range(50)]
        result = check_cash_intensive('ACC_A', txs, account_type='PERSONAL')
        if result:
            assert 0 <= result.score <= 100

    def test_empty_returns_none(self):
        assert check_cash_intensive('ACC_A', []) is None
