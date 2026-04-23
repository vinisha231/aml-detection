"""
backend/tests/test_structuring_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the structuring detection rule.

How to run:
    cd AMLDetector
    pip install pytest
    pytest backend/tests/ -v

What are unit tests?
    Unit tests verify that a single function works correctly in isolation.
    We test:
    - The "happy path" (the function detects what it should)
    - Edge cases (too few deposits, deposits too small, no deposits)
    - Boundary conditions (exactly at the threshold)

Why are these tests important?
    If you change the structuring rule logic, tests tell you immediately
    if you broke something. Without tests, you'd have to manually generate
    data and check every scenario.

This tests against our KNOWN ground truth:
    We BUILD the transactions ourselves in the test, so we know exactly
    what the rule should find.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.structuring_rule import check_structuring, RuleSignal

# ── Test helpers ──────────────────────────────────────────────────────────────

def make_cash_deposit(account_id: str, amount: float, days_ago: int) -> dict:
    """
    Create a fake cash deposit transaction for testing.

    Args:
        account_id: Account receiving the deposit
        amount:     Deposit amount
        days_ago:   How many days ago this happened (0 = today)

    Returns:
        Transaction dict matching our schema
    """
    return {
        "transaction_id":      f"TX_TEST_{amount}_{days_ago}",
        "sender_account_id":   "ACC_BANK_SOURCE",  # cash from bank vault
        "receiver_account_id": account_id,
        "amount":              amount,
        "transaction_type":    "cash_deposit",
        "description":         "cash deposit",
        "transaction_date":    datetime.now() - timedelta(days=days_ago),
        "is_suspicious":       True,
        "typology":            "structuring",
    }


def make_wire_transfer(sender: str, receiver: str, amount: float, days_ago: int) -> dict:
    """Create a fake wire transfer for testing."""
    return {
        "transaction_id":      f"TX_WIRE_{amount}_{days_ago}",
        "sender_account_id":   sender,
        "receiver_account_id": receiver,
        "amount":              amount,
        "transaction_type":    "wire_transfer",
        "description":         "wire transfer",
        "transaction_date":    datetime.now() - timedelta(days=days_ago),
        "is_suspicious":       False,
        "typology":            "benign",
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCheckStructuring:
    """Tests for the check_structuring() detection rule."""

    def test_detects_classic_structuring(self):
        """
        HAPPY PATH: 10 deposits just under $10k within 14 days → should fire.

        This is the clearest possible structuring pattern.
        We expect the rule to detect it with a high score.
        """
        account_id = "ACC_TEST_001"

        # Build 10 deposits, each just under $10k, over 10 days
        transactions = [
            make_cash_deposit(account_id, amount=9_500.00, days_ago=i)
            for i in range(10)  # days 0, 1, 2, ..., 9
        ]

        # Run the detection rule
        signals = check_structuring(account_id, transactions)

        # We expect exactly 1 signal to be returned
        assert len(signals) == 1, f"Expected 1 signal, got {len(signals)}"

        signal = signals[0]

        # Verify signal properties
        assert signal.account_id  == account_id
        assert signal.signal_type == "structuring_rule"
        assert signal.score       >= 60.0,    f"Score {signal.score} too low for 10 deposits"
        assert signal.confidence  >= 0.60,    f"Confidence {signal.confidence} too low"
        assert "9,500" in signal.evidence or "9500" in signal.evidence or "deposit" in signal.evidence.lower()

    def test_returns_empty_for_too_few_deposits(self):
        """
        EDGE CASE: Only 3 deposits — below the 5-deposit minimum threshold.
        Should return no signals.
        """
        account_id = "ACC_TEST_002"

        # Only 3 deposits (minimum is 5)
        transactions = [
            make_cash_deposit(account_id, amount=9_500.00, days_ago=i)
            for i in range(3)
        ]

        signals = check_structuring(account_id, transactions)
        assert len(signals) == 0, "Should not flag fewer than 5 deposits"

    def test_returns_empty_for_deposits_too_small(self):
        """
        EDGE CASE: 10 deposits of $500 each — amounts too small to be structuring.
        The structuring range is $8,500–$9,999. $500 deposits are not structuring.
        """
        account_id = "ACC_TEST_003"

        transactions = [
            make_cash_deposit(account_id, amount=500.00, days_ago=i)
            for i in range(10)
        ]

        signals = check_structuring(account_id, transactions)
        assert len(signals) == 0, "Should not flag small-amount deposits"

    def test_returns_empty_for_wire_transfers(self):
        """
        EDGE CASE: Structuring is specifically CASH DEPOSITS.
        10 wire transfers in the structuring range should NOT be flagged by this rule.
        (Wire transfers may be caught by other rules, but not this one.)
        """
        account_id = "ACC_TEST_004"

        transactions = [
            make_wire_transfer("ACC_OTHER", account_id, amount=9_500.00, days_ago=i)
            for i in range(10)
        ]

        signals = check_structuring(account_id, transactions)
        assert len(signals) == 0, "Structuring rule only fires on cash deposits"

    def test_returns_empty_for_empty_transactions(self):
        """
        EDGE CASE: Account with no transactions at all.
        Should gracefully return an empty list (not crash).
        """
        signals = check_structuring("ACC_EMPTY", [])
        assert signals == []

    def test_score_increases_with_more_deposits(self):
        """
        SCORING: More deposits → higher score.
        10 deposits should score higher than 5 deposits.
        """
        account_id_5  = "ACC_TEST_FIVE"
        account_id_10 = "ACC_TEST_TEN"

        transactions_5  = [make_cash_deposit(account_id_5,  9_500.00, i) for i in range(5)]
        transactions_10 = [make_cash_deposit(account_id_10, 9_500.00, i) for i in range(10)]

        signals_5  = check_structuring(account_id_5,  transactions_5)
        signals_10 = check_structuring(account_id_10, transactions_10)

        assert len(signals_5)  == 1
        assert len(signals_10) == 1
        assert signals_10[0].score > signals_5[0].score, (
            f"10 deposits ({signals_10[0].score}) should score higher than "
            f"5 deposits ({signals_5[0].score})"
        )

    def test_deposits_outside_window_not_counted(self):
        """
        WINDOW: Deposits older than 14 days should not count.
        5 recent deposits + 10 old deposits → only 5 count → below threshold.
        """
        account_id = "ACC_TEST_WINDOW"

        # 5 recent deposits (within 14-day window) — NOT enough alone
        recent = [make_cash_deposit(account_id, 9_500.00, days_ago=i) for i in range(5)]

        # 10 old deposits (older than 14 days) — should be excluded
        old = [make_cash_deposit(account_id, 9_500.00, days_ago=20 + i) for i in range(10)]

        signals = check_structuring(account_id, recent + old)

        # Only 5 recent deposits → exactly at the threshold → should still fire
        # (our MIN is 5, so 5 is the borderline case)
        # This tests that old deposits don't inflate the count
        if signals:
            assert signals[0].score <= 45.0, "Score too high — old deposits being counted?"

    def test_signal_type_name(self):
        """
        METADATA: Signal type must be exactly 'structuring_rule'.
        This name is used for FPR tracking and should never change.
        """
        account_id = "ACC_TEST_NAME"
        transactions = [make_cash_deposit(account_id, 9_500.00, i) for i in range(8)]
        signals = check_structuring(account_id, transactions)
        assert signals[0].signal_type == "structuring_rule"

    def test_score_capped_at_95(self):
        """
        BOUNDARY: Score should never exceed 95 (we reserve 95-100 for combined signals).
        """
        account_id = "ACC_TEST_CAP"
        # 50 deposits — far more than normal; score should cap at 95
        transactions = [make_cash_deposit(account_id, 9_500.00, i % 14) for i in range(50)]
        signals = check_structuring(account_id, transactions)
        if signals:
            assert signals[0].score <= 95.0, f"Score {signals[0].score} exceeded cap of 95"
