"""
backend/utils/date_utils.py
─────────────────────────────────────────────────────────────────────────────
Date and time utility functions used throughout the detection pipeline.

Why centralise date utilities?
  Date manipulation is surprisingly tricky:
  - timezone-naive vs timezone-aware datetimes cause subtle comparison bugs
  - "days between two dates" depends on whether you count the endpoints
  - sliding windows need careful boundary handling (inclusive vs exclusive)

  Centralising these functions means one place to fix if a bug is found,
  and consistent behavior across all rules.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from datetime import datetime, timedelta, date
from typing import Iterator


def days_between(start: datetime, end: datetime) -> int:
    """
    Number of complete days between two datetimes (ignoring time of day).

    Args:
        start: Earlier datetime.
        end:   Later datetime.

    Returns:
        Integer number of days. Negative if end < start.
    """
    return (end.date() - start.date()).days


def hours_between(start: datetime, end: datetime) -> float:
    """
    Number of hours (including fractional) between two datetimes.

    Args:
        start: Earlier datetime.
        end:   Later datetime.

    Returns:
        Float hours. Negative if end < start.
    """
    delta = end - start
    return delta.total_seconds() / 3600.0


def is_within_window(
    event_time:   datetime,
    window_start: datetime,
    window_end:   datetime,
    inclusive:    bool = True,
) -> bool:
    """
    Check if an event falls within a time window.

    Args:
        event_time:   The datetime to check.
        window_start: Start of the window.
        window_end:   End of the window.
        inclusive:    If True, the endpoints are included (>=, <=).

    Returns:
        True if event_time is within the window.
    """
    if inclusive:
        return window_start <= event_time <= window_end
    else:
        return window_start < event_time < window_end


def sliding_windows(
    start: datetime,
    end:   datetime,
    window_days: int,
    step_days:   int | None = None,
) -> Iterator[tuple[datetime, datetime]]:
    """
    Generate sliding time windows between start and end.

    Useful for rules that need to look at activity in overlapping windows,
    e.g., "total deposits in any 7-day period exceeds $X".

    Args:
        start:       Start of the overall period.
        end:         End of the overall period.
        window_days: Width of each window in days.
        step_days:   How far to advance each step. Defaults to window_days
                     (non-overlapping). Set to 1 for fully sliding windows.

    Yields:
        (window_start, window_end) tuples for each window.
    """
    if step_days is None:
        step_days = window_days

    window_start = start
    step = timedelta(days=step_days)
    width = timedelta(days=window_days)

    while window_start < end:
        window_end = min(window_start + width, end)
        yield (window_start, window_end)
        window_start += step


def bucket_by_day(transactions: list[dict]) -> dict[date, list[dict]]:
    """
    Group a list of transactions by their transaction date (day bucket).

    Useful for rules that compute per-day aggregates, like velocity checks
    or structuring detection (transactions on the same day).

    Args:
        transactions: List of transaction dicts with 'transaction_date' field.

    Returns:
        Dict mapping date → list of transactions on that date.
    """
    buckets: dict[date, list[dict]] = {}
    for tx in transactions:
        dt = tx.get('transaction_date')
        if dt is None:
            continue
        day = dt.date() if isinstance(dt, datetime) else dt
        if day not in buckets:
            buckets[day] = []
        buckets[day].append(tx)
    return buckets


def bucket_by_week(transactions: list[dict]) -> dict[int, list[dict]]:
    """
    Group transactions by ISO week number (within the year).

    Args:
        transactions: List of transaction dicts.

    Returns:
        Dict mapping ISO week number → list of transactions.
    """
    buckets: dict[int, list[dict]] = {}
    for tx in transactions:
        dt = tx.get('transaction_date')
        if dt is None:
            continue
        week = dt.isocalendar()[1]  # ISO week number (1–53)
        if week not in buckets:
            buckets[week] = []
        buckets[week].append(tx)
    return buckets


def is_after_hours(dt: datetime, start_hour: int = 23, end_hour: int = 6) -> bool:
    """
    Check if a datetime falls in the "after hours" window.

    Used by cash_intensive_rule to flag late-night transactions that are
    inconsistent with legitimate business operation hours.

    Args:
        dt:         Datetime to check.
        start_hour: Start of the after-hours window (inclusive). Default: 11pm.
        end_hour:   End of the after-hours window (exclusive). Default: 6am.

    Returns:
        True if the time is in the after-hours range.
    """
    hour = dt.hour
    if start_hour > end_hour:
        # Window wraps midnight (e.g., 23:00 to 06:00)
        return hour >= start_hour or hour < end_hour
    else:
        # Window doesn't wrap midnight
        return start_hour <= hour < end_hour


def account_age_days(account: dict, reference_date: datetime) -> int | None:
    """
    Compute the age of an account in days.

    Args:
        account:        Account dict with optional 'created_at' field.
        reference_date: The date to measure age from (usually simulation end).

    Returns:
        Age in days, or None if created_at is not available.
    """
    created_at = account.get('created_at')
    if created_at is None:
        return None
    return days_between(created_at, reference_date)
