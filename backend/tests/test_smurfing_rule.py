"""
backend/tests/test_smurfing_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the smurfing (multi-sender coordinated deposits) rule.

Tests verify:
  - Classic smurfing pattern (many senders, sub-threshold cash) is flagged
  - Too few unique senders → not flagged (plain structuring, not smurfing)
  - Non-cash deposits are ignored
  - Amounts outside the sub-threshold range are ignored
  - Score is bounded 0–100
  - Weight is higher than structuring
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.smurfing_rule import check_smurfing


def make_cash_deposit(
    sender: str,
    receiver: str,
    amount: float,
    days_offset: int = 0,
) -> dict:
    base = datetime(2024, 6, 15, 10, 0)
    return {
        'transaction_id':      f'TX_{sender}_{days_offset}',
        'sender_account_id':   sender,
        'receiver_account_id': receiver,
        'amount':              amount,
        'transaction_type':    'CASH_DEPOSIT',
        'transaction_date':    base + timedelta(days=days_offset),
        'is_suspicious':       False,
    }


class TestSmurfingRule:

    def test_classic_smurfing_flagged(self):
        """10 different senders each deposit $9,500 — classic smurfing ring."""
        txs = [
            make_cash_deposit(f'ACC_SMURF_{i}', 'ACC_TARGET', 9_500.0, days_offset=i)
            for i in range(10)
        ]
        result = check_smurfing('ACC_TARGET', txs)
        assert result is not None, "Classic smurfing should be flagged"
        assert result.signal_type == 'smurfing'

    def test_few_unique_senders_not_smurfing(self):
        """Same 2 senders making 8 deposits each — structuring, not smurfing."""
        txs = [
            make_cash_deposit('ACC_A', 'ACC_TARGET', 9_500.0, days_offset=i)
            for i in range(4)
        ] + [
            make_cash_deposit('ACC_B', 'ACC_TARGET', 9_200.0, days_offset=i + 4)
            for i in range(4)
        ]
        result = check_smurfing('ACC_TARGET', txs)
        # Only 2 unique senders (MIN_UNIQUE_SMURFS = 5) → not smurfing
        assert result is None, "Too few unique senders — should not flag smurfing"

    def test_amount_above_threshold_ignored(self):
        """Deposits of $15,000 are above the CTR threshold — not smurfing."""
        txs = [
            make_cash_deposit(f'ACC_SMURF_{i}', 'ACC_TARGET', 15_000.0, days_offset=i)
            for i in range(10)
        ]
        result = check_smurfing('ACC_TARGET', txs)
        assert result is None

    def test_wire_transfers_ignored(self):
        """Only CASH_DEPOSIT type is checked — wire transfers are excluded."""
        txs = [
            {
                'transaction_id':      f'TX_{i}',
                'sender_account_id':   f'ACC_SMURF_{i}',
                'receiver_account_id': 'ACC_TARGET',
                'amount':              9_500.0,
                'transaction_type':    'WIRE',  # NOT cash deposit
                'transaction_date':    datetime(2024, 6, 15) + timedelta(days=i),
                'is_suspicious':       False,
            }
            for i in range(10)
        ]
        result = check_smurfing('ACC_TARGET', txs)
        assert result is None

    def test_weight_higher_than_structuring(self):
        """Smurfing weight (2.2) should exceed structuring weight (2.0)."""
        txs = [
            make_cash_deposit(f'ACC_SMURF_{i}', 'ACC_TARGET', 9_500.0, days_offset=i)
            for i in range(10)
        ]
        result = check_smurfing('ACC_TARGET', txs)
        assert result is not None
        assert result.weight == 2.2, "Smurfing weight should be 2.2"
        assert result.weight > 2.0, "Smurfing should weigh more than structuring (2.0)"

    def test_score_bounded(self):
        """Score must be in [0, 100]."""
        txs = [
            make_cash_deposit(f'ACC_SMURF_{i}', 'ACC_TARGET', 9_500.0, days_offset=i % 30)
            for i in range(50)  # 50 unique smurfs — max score case
        ]
        result = check_smurfing('ACC_TARGET', txs)
        if result:
            assert 0 <= result.score <= 100

    def test_empty_returns_none(self):
        assert check_smurfing('ACC_TARGET', []) is None
