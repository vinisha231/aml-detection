"""
backend/tests/test_round_number_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the round number detection rule.

The round number rule is a SUPPORTING signal with a low weight.
Tests verify it fires correctly but doesn't produce inflated scores.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.round_number_rule import check_round_numbers, is_round_number


def make_tx(sender: str, receiver: str, amount: float, days_ago: float = 5.0) -> dict:
    return {
        "transaction_id":      f"TX_{amount}_{days_ago}",
        "sender_account_id":   sender,
        "receiver_account_id": receiver,
        "amount":              float(amount),
        "transaction_type":    "wire_transfer",
        "description":         "transfer",
        "transaction_date":    datetime.now() - timedelta(days=days_ago),
        "is_suspicious":       False,
        "typology":            "benign",
    }


class TestIsRoundNumber:
    """Tests for the is_round_number() helper function."""

    def test_exact_10k_is_round(self):
        assert is_round_number(10_000.00) is True

    def test_exact_50k_is_round(self):
        assert is_round_number(50_000.00) is True

    def test_9500_not_round(self):
        """$9,500 is not a multiple of $1,000."""
        assert is_round_number(9_500.00) is False

    def test_below_5k_threshold(self):
        """Small amounts below $5,000 threshold should never be flagged."""
        assert is_round_number(1_000.00) is False
        assert is_round_number(3_000.00) is False

    def test_25k_is_round(self):
        assert is_round_number(25_000.00) is True


class TestCheckRoundNumbers:

    def test_detects_high_fraction_round_numbers(self):
        """
        If 80%+ of transactions are round numbers ≥ $5,000 → should fire.
        """
        account_id = "ACC_SHELL"
        transactions = [
            make_tx(account_id, "ACC_B", amount, days_ago=float(i))
            for i, amount in enumerate([
                10_000, 25_000, 50_000, 10_000, 25_000,
                50_000, 10_000, 25_000, 50_000, 10_000,  # 10 round numbers
                10_247.50,  # one non-round
            ])
        ]
        signals = check_round_numbers(account_id, transactions)
        assert len(signals) == 1
        assert signals[0].signal_type == "round_number_rule"

    def test_no_signal_for_normal_amounts(self):
        """Normal accounts have varied amounts — should not fire."""
        account_id = "ACC_NORMAL"
        transactions = [
            make_tx(account_id, "ACC_B", amount, float(i))
            for i, amount in enumerate([
                1234.56, 89.99, 2500.00, 567.89, 12345.67,
                450.00, 78.50, 9876.54, 234.12, 567.00,
                1500.00, 890.25
            ])
        ]
        signals = check_round_numbers(account_id, transactions)
        assert len(signals) == 0

    def test_too_few_transactions(self):
        """Fewer than MIN_TX_TO_ANALYZE transactions → no signal."""
        account_id = "ACC_FEW"
        transactions = [
            make_tx(account_id, "ACC_B", 10_000.00, float(i))
            for i in range(5)  # only 5 transactions — below minimum of 10
        ]
        signals = check_round_numbers(account_id, transactions)
        assert len(signals) == 0

    def test_low_weight(self):
        """Round number rule must have low weight (supporting signal, not primary)."""
        account_id = "ACC_WEIGHT"
        transactions = [
            make_tx(account_id, "ACC_B", 10_000.00, float(i))
            for i in range(15)
        ]
        signals = check_round_numbers(account_id, transactions)
        if signals:
            assert signals[0].weight <= 1.0, "Round number rule should have low weight"

    def test_score_capped_below_70(self):
        """Score should stay below 70 (this is a supporting signal only)."""
        account_id = "ACC_CAP"
        transactions = [
            make_tx(account_id, "ACC_B", 10_000.00, float(i))
            for i in range(20)  # all round numbers
        ]
        signals = check_round_numbers(account_id, transactions)
        if signals:
            assert signals[0].score <= 70.0
