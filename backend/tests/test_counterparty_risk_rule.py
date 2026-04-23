"""
backend/tests/test_counterparty_risk_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the counterparty risk rule.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.detection.rules.counterparty_risk_rule import run


def make_tx(sender: str, receiver: str, amount: float = 5_000.0):
    return {
        'sender_account_id':   sender,
        'receiver_account_id': receiver,
        'amount':              amount,
        'transaction_date':    None,
    }


class TestCounterpartyRiskRule:

    def test_no_transactions_no_signal(self):
        """Account with no transactions produces no signal."""
        signals = run('ACC_TARGET', [], account_scores={})
        assert signals == []

    def test_low_risk_counterparties_no_signal(self):
        """All counterparties have low scores — no signal."""
        txs = [
            make_tx('ACC_TARGET', 'ACC_LOW_1'),
            make_tx('ACC_TARGET', 'ACC_LOW_2'),
        ]
        scores = {'ACC_LOW_1': 20.0, 'ACC_LOW_2': 15.0}
        signals = run('ACC_TARGET', txs, account_scores=scores)
        assert signals == []

    def test_high_risk_counterparties_flagged(self):
        """Two counterparties with score >60 should trigger."""
        txs = [
            make_tx('ACC_TARGET', 'ACC_HIGH_1'),
            make_tx('ACC_TARGET', 'ACC_HIGH_2'),
            make_tx('ACC_TARGET', 'ACC_HIGH_3'),
        ]
        scores = {'ACC_HIGH_1': 80.0, 'ACC_HIGH_2': 75.0, 'ACC_HIGH_3': 70.0}
        signals = run('ACC_TARGET', txs, account_scores=scores)
        assert len(signals) == 1
        assert signals[0].account_id == 'ACC_TARGET'
        assert 'counterpart' in signals[0].evidence.lower()

    def test_mixed_counterparties(self):
        """One high-risk and one low-risk — not enough to trigger."""
        txs = [
            make_tx('ACC_TARGET', 'ACC_HIGH'),
            make_tx('ACC_TARGET', 'ACC_LOW'),
        ]
        scores = {'ACC_HIGH': 90.0, 'ACC_LOW': 10.0}
        signals = run('ACC_TARGET', txs, account_scores=scores)
        # Only 1 high-risk counterparty — below MIN_HIGH_RISK_COUNTERPARTIES=2
        assert signals == []

    def test_no_scores_no_crash(self):
        """When account_scores is empty, rule should not crash."""
        txs = [make_tx('ACC_TARGET', 'ACC_OTHER')]
        signals = run('ACC_TARGET', txs, account_scores={})
        assert isinstance(signals, list)
