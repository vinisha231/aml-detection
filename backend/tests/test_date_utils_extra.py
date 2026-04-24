"""
backend/tests/test_date_utils_extra.py
─────────────────────────────────────────────────────────────────────────────
Additional edge-case tests for date_utils — bucket_by_week and sliding windows.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime
from backend.utils.date_utils import (
    bucket_by_week,
    sliding_windows,
    is_within_window,
)


class TestBucketByWeek:

    def test_groups_by_iso_week(self):
        txs = [
            {'transaction_date': datetime(2024, 1, 1)},  # week 1
            {'transaction_date': datetime(2024, 1, 3)},  # week 1
            {'transaction_date': datetime(2024, 1, 8)},  # week 2
        ]
        buckets = bucket_by_week(txs)
        assert len(buckets) == 2

    def test_empty_list_returns_empty(self):
        buckets = bucket_by_week([])
        assert buckets == {}

    def test_skips_missing_dates(self):
        txs = [{'no_date': True}, {'transaction_date': datetime(2024, 3, 1)}]
        buckets = bucket_by_week(txs)
        assert len(buckets) == 1


class TestSlidingWindowsEdgeCases:

    def test_step_smaller_than_window_creates_overlap(self):
        """step=1 on a 7-day window creates 7-day sliding windows."""
        start = datetime(2024, 1, 1)
        end   = datetime(2024, 1, 15)
        windows = list(sliding_windows(start, end, window_days=7, step_days=1))
        # Should produce many overlapping windows
        assert len(windows) > 7

    def test_window_larger_than_range(self):
        """Window larger than total range — one window covering everything."""
        start = datetime(2024, 1, 1)
        end   = datetime(2024, 1, 5)
        windows = list(sliding_windows(start, end, window_days=30))
        assert len(windows) == 1
        assert windows[0][0] == start
        assert windows[0][1] == end


class TestIsWithinWindowEdgeCases:

    def test_exclusive_endpoints(self):
        start = datetime(2024, 1, 1)
        end   = datetime(2024, 1, 31)
        # Exactly on start — excluded when inclusive=False
        assert is_within_window(start, start, end, inclusive=False) is False
        # Exactly on end — excluded when inclusive=False
        assert is_within_window(end, start, end, inclusive=False) is False

    def test_zero_width_window_inclusive(self):
        """Single-point window with inclusive endpoints."""
        d = datetime(2024, 6, 15, 12, 0)
        assert is_within_window(d, d, d, inclusive=True) is True
