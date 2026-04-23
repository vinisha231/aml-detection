"""
backend/tests/test_high_value_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the high-value transaction detection rule.

Tests verify:
  - Single transaction above $50k is flagged
  - Burst of transactions totalling > $200k in 48h is flagged
  - Spike vs average is detected
  - Small transactions are NOT flagged
  - Empty input returns None
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.high_value_rule import check_high_value


def make_tx(
    account_id: str,
    amount: float,
    hours_offset: int = 0,
    is_sender: bool = True,
) -> dict:
    """Build a minimal transaction dict."""
    base = datetime(2024, 6, 1, 12, 0)
    return {
        'transaction_id':      f'TX_{hours_offset}',
        'sender_account_id':   account_id if is_sender else 'OTHER',
        'receiver_account_id': 'OTHER' if is_sender else account_id,
        'amount':              amount,
        'transaction_type':    'WIRE',
        'transaction_date':    base + timedelta(hours=hours_offset),
        'is_suspicious':       False,
    }


class TestHighValueRule:

    def test_single_large_tx_is_flagged(self):
        """One transaction above $50k triggers the rule."""
        txs = [make_tx('ACC_A', 75_000.0)]
        result = check_high_value('ACC_A', txs)
        assert result is not None
        assert result.signal_type == 'high_value'

    def test_small_transactions_not_flagged(self):
        """Transactions all below $50k should not trigger the rule."""
        txs = [make_tx('ACC_A', 5_000.0, hours_offset=i) for i in range(20)]
        result = check_high_value('ACC_A', txs)
        assert result is None

    def test_burst_within_48h_flagged(self):
        """Multiple transactions summing > $200k within 48 hours."""
        txs = [
            make_tx('ACC_A', 60_000.0, hours_offset=0),
            make_tx('ACC_A', 60_000.0, hours_offset=12),
            make_tx('ACC_A', 60_000.0, hours_offset=24),
            make_tx('ACC_A', 60_000.0, hours_offset=36),  # total = $240k in 36h
        ]
        result = check_high_value('ACC_A', txs)
        assert result is not None

    def test_spike_vs_average_flagged(self):
        """One giant transaction after 15 small ones triggers the spike check."""
        # 15 small transactions (avg ~$500) then one huge one
        txs = [make_tx('ACC_A', 500.0, hours_offset=i * 5) for i in range(15)]
        txs.append(make_tx('ACC_A', 75_000.0, hours_offset=100))  # 150x average
        result = check_high_value('ACC_A', txs)
        assert result is not None

    def test_score_bounded(self):
        """Score must be between 0 and 100."""
        txs = [make_tx('ACC_A', 999_999.0, hours_offset=i) for i in range(5)]
        result = check_high_value('ACC_A', txs)
        if result:
            assert 0 <= result.score <= 100

    def test_empty_returns_none(self):
        """Empty transaction list returns None."""
        assert check_high_value('ACC_A', []) is None

    def test_weight_is_low(self):
        """Weight should be 0.8 — supporting signal, not primary."""
        txs = [make_tx('ACC_A', 100_000.0)]
        result = check_high_value('ACC_A', txs)
        assert result is not None
        assert result.weight == 0.8
