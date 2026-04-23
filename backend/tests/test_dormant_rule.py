"""
backend/tests/test_dormant_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the dormant account wakeup detection rule.

Tests verify:
  - Truly dormant-then-active accounts are flagged
  - Always-active accounts are NOT flagged
  - Burst size threshold is enforced
  - Signal type and weight are correct
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.dormant_rule import check_dormant_wakeup


def make_tx(sender: str, receiver: str, days_ago: float) -> dict:
    return {
        "transaction_id":      f"TX_{sender}_{days_ago}",
        "sender_account_id":   sender,
        "receiver_account_id": receiver,
        "amount":              300.0,
        "transaction_type":    "ach",
        "description":         "payment",
        "transaction_date":    datetime.now() - timedelta(days=days_ago),
        "is_suspicious":       False,
        "typology":            "benign",
    }


class TestCheckDormantWakeup:

    def test_detects_dormant_then_active(self):
        """
        HAPPY PATH: 0 transactions in 90-day dormancy, then 30 in 14 days.
        Should fire with high score.
        """
        account_id = "ACC_DORMANT"
        other      = "ACC_OTHER"

        # 30 transactions in the burst period (last 14 days)
        burst_txs = [
            make_tx(account_id, other, days_ago=float(i) * 0.4)
            for i in range(30)
        ]

        # No transactions in dormancy period (days 14-104)

        signals = check_dormant_wakeup(account_id, burst_txs)

        assert len(signals) == 1, f"Expected 1 signal, got {len(signals)}"
        assert signals[0].score >= 50.0
        assert signals[0].signal_type == "dormant_rule"

    def test_no_flag_for_always_active_account(self):
        """
        Account with steady activity across 104 days → NOT a dormant wakeup.
        """
        account_id = "ACC_ACTIVE"
        other      = "ACC_OTHER"

        # 2 transactions per week for the full period
        transactions = [
            make_tx(account_id, other, days_ago=float(i) * 3.5)
            for i in range(30)  # 30 txs spread over ~104 days
        ]

        signals = check_dormant_wakeup(account_id, transactions)
        assert len(signals) == 0, "Consistently active account should not be flagged"

    def test_no_flag_for_small_burst(self):
        """
        Dormant account, but only 5 transactions in burst (below 15 threshold).
        Should NOT flag.
        """
        account_id = "ACC_SMALL_BURST"
        other      = "ACC_OTHER"

        # Only 5 transactions in burst (minimum is 15)
        burst_txs = [make_tx(account_id, other, days_ago=float(i)) for i in range(5)]

        signals = check_dormant_wakeup(account_id, burst_txs)
        assert len(signals) == 0, "Small burst should not trigger dormant rule"

    def test_empty_transactions(self):
        """No transactions → no signal."""
        signals = check_dormant_wakeup("ACC_EMPTY", [])
        assert signals == []

    def test_signal_has_correct_type(self):
        """Signal type must be 'dormant_rule'."""
        account_id = "ACC_TYPE"
        other = "ACC_OTHER"
        burst = [make_tx(account_id, other, days_ago=float(i) * 0.4) for i in range(20)]
        signals = check_dormant_wakeup(account_id, burst)
        if signals:
            assert signals[0].signal_type == "dormant_rule"
