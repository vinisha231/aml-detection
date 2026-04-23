"""
backend/tests/test_funnel_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the funnel account detection rule.

A funnel account:
- Receives from MANY different senders (high in-degree)
- Sends to FEW receivers (low out-degree)
- Fan-in ratio = in_degree / out_degree >> 1
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.funnel_rule import check_funnel


def make_tx(sender: str, receiver: str, amount: float, days_ago: float = 0.0) -> dict:
    return {
        "transaction_id":      f"TX_{sender}_{receiver}_{days_ago}",
        "sender_account_id":   sender,
        "receiver_account_id": receiver,
        "amount":              float(amount),
        "transaction_type":    "ach",
        "description":         "payment",
        "transaction_date":    datetime.now() - timedelta(days=days_ago),
        "is_suspicious":       False,
        "typology":            "benign",
    }


class TestCheckFunnel:

    def test_detects_classic_funnel_pattern(self):
        """
        HAPPY PATH: 30 unique senders, 1 receiver = funnel.
        Fan-in ratio = 30:1 → well above threshold.
        """
        funnel_id = "ACC_FUNNEL"
        dest_id   = "ACC_DEST"

        # 30 different senders all sending to the funnel
        transactions = [
            make_tx(f"ACC_SENDER_{i}", funnel_id, amount=500.0, days_ago=float(i % 14))
            for i in range(30)
        ]
        # Funnel sends one large transfer to destination
        transactions.append(make_tx(funnel_id, dest_id, amount=14_000.0, days_ago=1.0))

        signals = check_funnel(funnel_id, transactions)

        assert len(signals) == 1, f"Expected 1 signal, got {len(signals)}"
        assert signals[0].signal_type == "funnel_rule"
        assert signals[0].score >= 50.0

    def test_no_signal_for_normal_account(self):
        """
        EDGE CASE: Normal account with 3 senders and 3 receivers — not a funnel.
        """
        account_id = "ACC_NORMAL"

        transactions = [
            make_tx("ACC_A", account_id, 500.0, 5.0),
            make_tx("ACC_B", account_id, 300.0, 3.0),
            make_tx(account_id, "ACC_C", 400.0, 2.0),
            make_tx(account_id, "ACC_D", 200.0, 1.0),
        ]

        signals = check_funnel(account_id, transactions)
        assert len(signals) == 0

    def test_no_signal_for_empty_transactions(self):
        """EDGE CASE: No transactions → no signal."""
        signals = check_funnel("ACC_EMPTY", [])
        assert signals == []

    def test_fan_in_ratio_threshold(self):
        """
        Only 10 unique senders — below the MIN_UNIQUE_SENDERS threshold (15).
        Should not fire.
        """
        funnel_id = "ACC_SMALL_FUNNEL"
        transactions = [
            make_tx(f"ACC_SENDER_{i}", funnel_id, 500.0, float(i))
            for i in range(10)  # only 10 senders — below threshold
        ]
        transactions.append(make_tx(funnel_id, "ACC_DEST", 5000.0, 0.5))

        signals = check_funnel(funnel_id, transactions)
        assert len(signals) == 0, "10 senders should be below detection threshold"
