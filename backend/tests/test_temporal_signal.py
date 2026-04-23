"""
backend/tests/test_temporal_signal.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for backend/detection/graph/temporal_signal.py

Tests both the rapid-forwarding and synchronized-activation sub-signals.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import networkx as nx
from datetime import datetime, timedelta
from backend.detection.graph.temporal_signal import compute_temporal_signals


BASE = datetime(2024, 1, 15, 12, 0)


def make_tx(sender: str, receiver: str, hours_offset: float = 0.0, days_offset: int = 0):
    return {
        'sender_account_id':   sender,
        'receiver_account_id': receiver,
        'transaction_date':    BASE + timedelta(hours=hours_offset, days=days_offset),
        'amount': 10_000.0,
    }


def make_graph(*nodes: str) -> nx.DiGraph:
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n)
    return G


class TestRapidForwarding:

    def test_rapid_forward_flagged(self):
        """Account that receives and sends within 6 hours twice should be flagged."""
        G = make_graph('ACC_A', 'ACC_B', 'ACC_C')
        G.add_edge('ACC_A', 'ACC_B')
        G.add_edge('ACC_B', 'ACC_C')

        txs = [
            make_tx('ACC_A', 'ACC_B', hours_offset=0),
            make_tx('ACC_B', 'ACC_C', hours_offset=3),   # 3h later — rapid
            make_tx('ACC_A', 'ACC_B', hours_offset=48),
            make_tx('ACC_B', 'ACC_C', hours_offset=51),  # also rapid
        ]
        signals = compute_temporal_signals(G, txs)
        flagged = [s for s in signals if s.account_id == 'ACC_B']
        assert len(flagged) >= 1
        assert any('rapid' in s.evidence.lower() for s in flagged)

    def test_slow_forward_not_flagged(self):
        """Account that waits 3 days between receiving and forwarding is not flagged."""
        G = make_graph('ACC_A', 'ACC_B', 'ACC_C')
        G.add_edge('ACC_A', 'ACC_B')
        G.add_edge('ACC_B', 'ACC_C')

        txs = [
            make_tx('ACC_A', 'ACC_B', hours_offset=0),
            make_tx('ACC_B', 'ACC_C', hours_offset=72),  # 3 days later — normal
        ]
        signals = compute_temporal_signals(G, txs)
        rapid_signals = [
            s for s in signals
            if s.account_id == 'ACC_B' and 'rapid' in s.evidence.lower()
        ]
        assert len(rapid_signals) == 0

    def test_empty_transactions_returns_empty(self):
        G = make_graph('ACC_A', 'ACC_B')
        signals = compute_temporal_signals(G, [])
        assert signals == []

    def test_small_graph_skipped(self):
        """Graphs with fewer than 3 nodes are skipped."""
        G = make_graph('ACC_A', 'ACC_B')
        txs = [make_tx('ACC_A', 'ACC_B')]
        signals = compute_temporal_signals(G, txs)
        assert signals == []


class TestSynchronizedActivation:

    def test_synchronized_accounts_flagged(self):
        """5+ accounts all starting on the same day should be flagged."""
        # Create 6 accounts, all making their first transaction on the same day
        account_ids = [f'ACC_{i}' for i in range(6)]
        G = nx.DiGraph()
        for acc in account_ids:
            G.add_node(acc)

        txs = []
        for i, acc in enumerate(account_ids):
            # All start on Jan 15 (same day_key)
            txs.append(make_tx(acc, 'ACC_RECEIVER', hours_offset=i))

        G.add_node('ACC_RECEIVER')

        signals = compute_temporal_signals(G, txs)
        sync_signals = [s for s in signals if 'synchronized' in s.evidence.lower()]
        assert len(sync_signals) > 0

    def test_few_accounts_not_flagged(self):
        """Only 3 accounts activating on the same day is not flagged (< MIN_SYNC_ACCOUNTS=5)."""
        account_ids = ['ACC_X', 'ACC_Y', 'ACC_Z']
        G = nx.DiGraph()
        for acc in account_ids:
            G.add_node(acc)

        txs = [make_tx(acc, 'ACC_SINK', hours_offset=i) for i, acc in enumerate(account_ids)]
        G.add_node('ACC_SINK')

        signals = compute_temporal_signals(G, txs)
        sync_signals = [s for s in signals if 'synchronized' in s.evidence.lower()]
        assert len(sync_signals) == 0
