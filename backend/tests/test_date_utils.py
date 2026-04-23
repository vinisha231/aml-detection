"""
backend/tests/test_date_utils.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for backend/utils/date_utils.py
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.utils.date_utils import (
    days_between,
    hours_between,
    is_within_window,
    sliding_windows,
    bucket_by_day,
    is_after_hours,
    account_age_days,
)


class TestDaysBetween:

    def test_same_day(self):
        """Same day returns 0."""
        d = datetime(2024, 1, 15, 10, 0)
        assert days_between(d, d) == 0

    def test_one_day_apart(self):
        d1 = datetime(2024, 1, 15)
        d2 = datetime(2024, 1, 16)
        assert days_between(d1, d2) == 1

    def test_ignores_time_of_day(self):
        """23:59 on day 1 to 00:01 on day 2 = 1 day."""
        d1 = datetime(2024, 1, 15, 23, 59)
        d2 = datetime(2024, 1, 16, 0, 1)
        assert days_between(d1, d2) == 1

    def test_negative_when_reversed(self):
        d1 = datetime(2024, 1, 20)
        d2 = datetime(2024, 1, 15)
        assert days_between(d1, d2) == -5


class TestHoursBetween:

    def test_exactly_one_hour(self):
        d1 = datetime(2024, 1, 15, 10, 0)
        d2 = datetime(2024, 1, 15, 11, 0)
        assert hours_between(d1, d2) == pytest.approx(1.0)

    def test_fractional_hours(self):
        d1 = datetime(2024, 1, 15, 10, 0)
        d2 = datetime(2024, 1, 15, 10, 30)
        assert hours_between(d1, d2) == pytest.approx(0.5)

    def test_cross_day_boundary(self):
        d1 = datetime(2024, 1, 15, 22, 0)
        d2 = datetime(2024, 1, 16, 4, 0)
        assert hours_between(d1, d2) == pytest.approx(6.0)


class TestIsWithinWindow:

    def test_in_middle(self):
        start = datetime(2024, 1, 1)
        end   = datetime(2024, 1, 31)
        event = datetime(2024, 1, 15)
        assert is_within_window(event, start, end) is True

    def test_on_start_inclusive(self):
        d = datetime(2024, 1, 1)
        assert is_within_window(d, d, datetime(2024, 1, 31)) is True

    def test_on_end_inclusive(self):
        d = datetime(2024, 1, 31)
        assert is_within_window(d, datetime(2024, 1, 1), d) is True

    def test_outside_window(self):
        start = datetime(2024, 1, 1)
        end   = datetime(2024, 1, 31)
        event = datetime(2024, 2, 5)
        assert is_within_window(event, start, end) is False


class TestSlidingWindows:

    def test_non_overlapping(self):
        start = datetime(2024, 1, 1)
        end   = datetime(2024, 1, 31)
        windows = list(sliding_windows(start, end, window_days=10))
        assert len(windows) == 3

    def test_windows_cover_range(self):
        start = datetime(2024, 1, 1)
        end   = datetime(2024, 2, 1)
        windows = list(sliding_windows(start, end, window_days=7))
        # First window starts at start
        assert windows[0][0] == start
        # Last window ends at end
        assert windows[-1][1] == end


class TestBucketByDay:

    def test_groups_correctly(self):
        txs = [
            {'transaction_date': datetime(2024, 1, 15, 10, 0), 'id': 1},
            {'transaction_date': datetime(2024, 1, 15, 14, 0), 'id': 2},
            {'transaction_date': datetime(2024, 1, 16, 9, 0),  'id': 3},
        ]
        buckets = bucket_by_day(txs)
        from datetime import date
        assert len(buckets[date(2024, 1, 15)]) == 2
        assert len(buckets[date(2024, 1, 16)]) == 1

    def test_handles_missing_date(self):
        txs = [{'id': 1}]  # no transaction_date
        buckets = bucket_by_day(txs)
        assert len(buckets) == 0


class TestIsAfterHours:

    def test_midnight_is_after_hours(self):
        dt = datetime(2024, 1, 15, 0, 0)
        assert is_after_hours(dt) is True

    def test_3am_is_after_hours(self):
        dt = datetime(2024, 1, 15, 3, 0)
        assert is_after_hours(dt) is True

    def test_noon_is_not_after_hours(self):
        dt = datetime(2024, 1, 15, 12, 0)
        assert is_after_hours(dt) is False


class TestAccountAgeDays:

    def test_returns_age(self):
        account = {'created_at': datetime(2024, 1, 1)}
        ref = datetime(2024, 1, 31)
        assert account_age_days(account, ref) == 30

    def test_returns_none_when_no_created_at(self):
        account = {}
        assert account_age_days(account, datetime(2024, 1, 1)) is None
