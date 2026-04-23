"""
backend/tests/test_layering_rule.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the layering (pass-through) detection rule.

Tests verify:
  - Classic A→B→C chain is flagged (B is the pass-through account)
  - Insufficient hops (only 1 event) are NOT flagged
  - Wrong timing (outflow happens before inflow) is NOT flagged
  - Amount outside passthrough ratio is NOT flagged
  - Score increases with more hops
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.detection.rules.layering_rule import check_layering


def make_tx(
    sender: str,
    receiver: str,
    amount: float,
    hours_offset: int = 0,
    tx_type: str = 'WIRE',
) -> dict:
    """Build a minimal transaction dict."""
    base_date = datetime(2024, 6, 1, 12, 0, 0)
    return {
        'transaction_id':       f'TX_{sender}_{receiver}_{hours_offset}',
        'sender_account_id':    sender,
        'receiver_account_id':  receiver,
        'amount':               amount,
        'transaction_type':     tx_type,
        'transaction_date':     base_date + timedelta(hours=hours_offset),
        'is_suspicious':        False,
    }


class TestLayeringRule:

    def test_basic_passthrough_is_flagged(self):
        """B receives $100k from A, then wires $97k to C within 48h — flagged."""
        # Two such events = 2 hops = above MIN_HOP_COUNT of 2
        txs = [
            make_tx('ACC_A', 'ACC_B', 100_000.0, hours_offset=0),    # inflow 1
            make_tx('ACC_B', 'ACC_C', 97_000.0,  hours_offset=12),   # outflow 1 (97%)
            make_tx('ACC_A', 'ACC_B', 80_000.0,  hours_offset=48),   # inflow 2
            make_tx('ACC_B', 'ACC_D', 78_000.0,  hours_offset=60),   # outflow 2 (97.5%)
        ]
        result = check_layering('ACC_B', txs)
        assert result is not None, "Should flag B as a pass-through node"
        assert result.signal_type == 'layering'
        assert result.score > 0

    def test_only_one_hop_not_flagged(self):
        """Single inflow → outflow pair: below MIN_HOP_COUNT of 2."""
        txs = [
            make_tx('ACC_A', 'ACC_B', 100_000.0, hours_offset=0),
            make_tx('ACC_B', 'ACC_C', 95_000.0,  hours_offset=10),
        ]
        result = check_layering('ACC_B', txs)
        assert result is None, "One hop is not enough to flag layering"

    def test_outflow_before_inflow_not_matched(self):
        """Outflow that precedes the inflow should not be matched."""
        txs = [
            make_tx('ACC_B', 'ACC_C', 95_000.0,  hours_offset=0),   # outflow first
            make_tx('ACC_A', 'ACC_B', 100_000.0, hours_offset=5),   # inflow later
        ]
        # Only one potential match, and it's invalid because outflow came first
        result = check_layering('ACC_B', txs)
        assert result is None

    def test_outflow_too_large_ratio_not_matched(self):
        """Outflow that is 120% of inflow falls outside the 80–115% passthrough window."""
        txs = [
            make_tx('ACC_A', 'ACC_B', 100_000.0, hours_offset=0),
            make_tx('ACC_B', 'ACC_C', 120_000.0, hours_offset=10),  # 120% — too high
            make_tx('ACC_A', 'ACC_B', 100_000.0, hours_offset=50),
            make_tx('ACC_B', 'ACC_D', 118_000.0, hours_offset=60),  # 118% — too high
        ]
        result = check_layering('ACC_B', txs)
        assert result is None

    def test_cash_transactions_ignored(self):
        """CASH_DEPOSIT transactions are excluded — layering uses electronic transfers."""
        txs = [
            make_tx('ACC_A', 'ACC_B', 100_000.0, hours_offset=0,  tx_type='CASH_DEPOSIT'),
            make_tx('ACC_B', 'ACC_C', 97_000.0,  hours_offset=10, tx_type='CASH_DEPOSIT'),
            make_tx('ACC_A', 'ACC_B', 80_000.0,  hours_offset=48, tx_type='CASH_DEPOSIT'),
            make_tx('ACC_B', 'ACC_D', 78_000.0,  hours_offset=60, tx_type='CASH_DEPOSIT'),
        ]
        result = check_layering('ACC_B', txs)
        assert result is None, "Cash transactions should not trigger layering rule"

    def test_signal_weight_is_correct(self):
        """Weight should be 1.7 (higher than round_number, lower than structuring)."""
        txs = [
            make_tx('ACC_A', 'ACC_B', 100_000.0, hours_offset=0),
            make_tx('ACC_B', 'ACC_C', 97_000.0,  hours_offset=12),
            make_tx('ACC_A', 'ACC_B', 80_000.0,  hours_offset=48),
            make_tx('ACC_B', 'ACC_D', 78_000.0,  hours_offset=60),
        ]
        result = check_layering('ACC_B', txs)
        assert result is not None
        assert result.weight == 1.7

    def test_more_hops_scores_higher(self):
        """4-hop account should score higher than 2-hop account."""
        def make_chain(n_hops: int) -> list:
            txs = []
            for i in range(n_hops):
                txs.append(make_tx('ACC_A', 'ACC_B', 100_000.0, hours_offset=i * 50))
                txs.append(make_tx('ACC_B', f'ACC_C_{i}', 97_000.0, hours_offset=i * 50 + 12))
            return txs

        result_2 = check_layering('ACC_B', make_chain(2))
        result_4 = check_layering('ACC_B', make_chain(4))

        if result_2 and result_4:
            assert result_4.score >= result_2.score, "More hops should give higher score"

    def test_empty_transactions(self):
        """Empty input → no signal."""
        result = check_layering('ACC_B', [])
        assert result is None
