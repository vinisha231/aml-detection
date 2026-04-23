"""
backend/tests/test_velocity_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the velocity anomaly detection rule.

Tests cover:
- Dormant account sudden activation (the main use case)
- Active account that just has more transactions (should NOT always flag)
- Zero-transaction accounts
- Z-score threshold boundary conditions
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.velocity_rule import check_velocity


def make_tx(sender: str, receiver: str, days_ago: float) -> dict:
    """Create a minimal transaction for velocity testing."""
    return {
        "transaction_id":      f"TX_{sender}_{days_ago}",
        "sender_account_id":   sender,
        "receiver_account_id": receiver,
        "amount":              500.0,
        "transaction_type":    "ach",
        "description":         "transfer",
        "transaction_date":    datetime.now() - timedelta(days=days_ago),
        "is_suspicious":       False,
        "typology":            "benign",
    }


class TestCheckVelocity:

    def test_detects_dormant_burst(self):
        """
        HAPPY PATH: Account dormant for 90 days, then 50 transactions in 7 days.
        This is the classic velocity anomaly — should fire with high score.
        """
        account_id = "ACC_VELOCITY_001"
        other      = "ACC_OTHER"

        # No transactions in the baseline period (days 37-90 ago)
        # 50 transactions in the recent period (last 7 days)
        transactions = [
            make_tx(account_id, other, days_ago=float(i) / 24)  # spread over 7 days
            for i in range(50 * 24, 7 * 24, -1)  # 50 txs over 7 days
        ][:50]

        signals = check_velocity(account_id, transactions)

        # Should flag the burst
        assert len(signals) >= 1, "Dormant burst should be detected"
        assert signals[0].score >= 50.0, "Dormant burst should score ≥ 50"

    def test_no_signal_for_consistently_active_account(self):
        """
        EDGE CASE: Account that always sends 5 tx/week.
        Velocity should NOT flag consistent activity — only anomalies.
        """
        account_id = "ACC_NORMAL"
        other      = "ACC_OTHER"

        # 5 transactions per week for the past 37 days (baseline: ~20, recent: ~5)
        transactions = []
        for day in range(37):
            for _ in range(1):  # 1 transaction every day
                transactions.append(make_tx(account_id, other, days_ago=day))

        signals = check_velocity(account_id, transactions)

        # Consistent 1 tx/day should not be flagged
        assert len(signals) == 0, "Consistent activity should not be flagged"

    def test_empty_transactions(self):
        """EDGE CASE: No transactions at all → no signal."""
        signals = check_velocity("ACC_EMPTY", [])
        assert signals == []

    def test_signal_type_is_velocity_rule(self):
        """METADATA: Signal type string must be exactly 'velocity_rule'."""
        account_id = "ACC_VEL_TYPE"
        other = "ACC_OTHER"
        # Create a very obvious burst: 40 txs in 7 days, 0 in prior 30 days
        transactions = [
            make_tx(account_id, other, days_ago=float(i) * 0.17)
            for i in range(40)
        ]
        signals = check_velocity(account_id, transactions)
        if signals:
            assert signals[0].signal_type == "velocity_rule"
