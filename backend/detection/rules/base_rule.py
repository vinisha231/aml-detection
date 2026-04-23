"""
backend/detection/rules/base_rule.py
─────────────────────────────────────────────────────────────────────────────
Base utilities shared by all detection rules.

Contains:
  - The RuleSignal dataclass (canonical definition — imported by all rules)
  - Helper functions for common rule calculations

Why a base module?
  The RuleSignal dataclass was defined in structuring_rule.py initially,
  and all other rules imported it from there. That's backwards — a rule file
  shouldn't define shared infrastructure. This module is the proper home.
─────────────────────────────────────────────────────────────────────────────
"""

from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta


@dataclass
class RuleSignal:
    """
    The standard output format for ALL detection rules.

    Every rule returns a list of RuleSignal objects.
    The scoring engine reads these and combines them into a final risk score.

    Fields:
        account_id:  Which account this signal is for
        signal_type: Unique identifier for the rule (e.g., "structuring_rule")
        score:       How suspicious this specific signal is (0-100)
        weight:      How much this signal counts in the final score
                     Higher weight = more important signal
                     Structuring (2.0) > Velocity (1.5) > Round numbers (0.5)
        evidence:    Human-readable explanation for the analyst
                     This is what the analyst reads to understand why we flagged it
        confidence:  How certain we are (0.0-1.0)
                     Scales down the contribution to the final score
    """
    account_id:  str
    signal_type: str
    score:       float
    weight:      float
    evidence:    str
    confidence:  float


def filter_by_date_window(
    transactions: List[dict],
    as_of_date: datetime,
    lookback_days: int,
    account_id: str = None,
    direction: str = "both"
) -> List[dict]:
    """
    Filter transactions to those within the lookback window.

    Args:
        transactions:  All transactions
        as_of_date:    Reference date (end of window)
        lookback_days: How many days to look back
        account_id:    If provided, only include txs involving this account
        direction:     "sent"     = only sent transactions (this account is sender)
                       "received" = only received transactions (this account is receiver)
                       "both"     = all transactions involving this account (default)

    Returns:
        Filtered list of transactions
    """
    window_start = as_of_date - timedelta(days=lookback_days)

    result = []
    for tx in transactions:
        # Date check
        if not (window_start <= tx["transaction_date"] <= as_of_date):
            continue

        # Account / direction check
        if account_id:
            if direction == "sent" and tx["sender_account_id"] != account_id:
                continue
            if direction == "received" and tx["receiver_account_id"] != account_id:
                continue
            if direction == "both" and (
                tx["sender_account_id"] != account_id and
                tx["receiver_account_id"] != account_id
            ):
                continue

        result.append(tx)

    return result


def get_latest_date(transactions: List[dict]) -> datetime:
    """
    Get the most recent transaction date from a list.

    Used when as_of_date is not provided — we use the latest transaction
    as a proxy for "now" to keep results reproducible on historical data.

    Args:
        transactions: List of transaction dicts

    Returns:
        Latest datetime, or datetime.now() if list is empty
    """
    if not transactions:
        return datetime.now()
    return max(tx["transaction_date"] for tx in transactions)
