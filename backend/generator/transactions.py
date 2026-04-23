"""
backend/generator/transactions.py
─────────────────────────────────────────────────────────────────────────────
Base utilities for generating transactions.

This module contains shared helpers that BOTH benign and typology generators use.
Instead of duplicating transaction-creation code in every file, we define it once here.

This is the "Don't Repeat Yourself" (DRY) principle in practice.
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

# Transaction types that appear in real bank data
TRANSACTION_TYPES = [
    "cash_deposit",       # customer brings physical cash to a teller
    "wire_transfer",      # electronic transfer (often between banks)
    "ach",                # Automated Clearing House (payroll, bills)
    "internal_transfer",  # transfer between accounts at the same bank
    "atm",                # ATM withdrawal or deposit
    "check",              # paper check deposit
]

# ─── Global transaction counter ──────────────────────────────────────────────
# This global counter ensures every transaction gets a unique ID
# even when called from multiple generators.
_tx_counter = 0


def reset_transaction_counter(start: int = 0) -> None:
    """
    Reset the transaction counter to a starting value.

    Call this at the beginning of data generation to ensure IDs start fresh.

    Args:
        start: Starting number (default 0)
    """
    global _tx_counter
    _tx_counter = start


def generate_transaction_id() -> str:
    """
    Generate the next sequential transaction ID.

    Returns:
        String like "TX_00000001"

    Example:
        generate_transaction_id()  → "TX_00000001"
        generate_transaction_id()  → "TX_00000002"
    """
    global _tx_counter
    _tx_counter += 1
    # :08d = 8-digit zero-padded integer
    return f"TX_{_tx_counter:08d}"


def make_transaction(
    sender_id: str,
    receiver_id: str,
    amount: float,
    transaction_date: datetime,
    transaction_type: str = "wire_transfer",
    description: str = None,
    is_suspicious: bool = False,
    typology: str = "benign",
) -> dict:
    """
    Create a transaction dictionary with all required fields.

    This is the CORE function used by all generators.
    Every transaction in the system goes through this function.

    Args:
        sender_id:        Account ID sending the money
        receiver_id:      Account ID receiving the money
        amount:           Amount in USD (should be positive)
        transaction_date: When the transaction occurred
        transaction_type: Type of transaction (wire, cash, etc.)
        description:      What the transaction is for (memo field)
        is_suspicious:    True if this is part of a money laundering pattern
        typology:         Which typology this belongs to, or "benign"

    Returns:
        Dict with all transaction fields matching our schema.Transaction model

    Example:
        tx = make_transaction(
            sender_id="ACC_000001",
            receiver_id="ACC_000042",
            amount=9500.00,
            transaction_date=datetime(2024, 3, 15),
            transaction_type="cash_deposit",
            description="cash deposit",
            is_suspicious=True,
            typology="structuring"
        )
    """
    # Auto-generate a description if none provided
    if description is None:
        description = fake.bs()  # generates corporate-speak like "synergize value-added matrices"

    return {
        "transaction_id":       generate_transaction_id(),
        "sender_account_id":    sender_id,
        "receiver_account_id":  receiver_id,
        "amount":               round(amount, 2),
        "transaction_type":     transaction_type,
        "description":          description,
        "transaction_date":     transaction_date,
        "is_suspicious":        is_suspicious,
        "typology":             typology,
    }


def random_datetime_in_range(
    start: datetime,
    end: datetime,
    rng: random.Random = None
) -> datetime:
    """
    Generate a random datetime between start and end.

    Used to spread transactions across realistic time windows.

    Args:
        start: Earliest possible datetime
        end:   Latest possible datetime
        rng:   Random number generator (for reproducibility)

    Returns:
        Random datetime between start and end

    Example:
        # Random time between 9am and 5pm on Jan 15
        dt = random_datetime_in_range(
            datetime(2024, 1, 15, 9, 0),
            datetime(2024, 1, 15, 17, 0)
        )
    """
    if rng is None:
        rng = random

    delta = end - start
    total_seconds = int(delta.total_seconds())

    if total_seconds <= 0:
        return start

    # Pick a random number of seconds within the range
    random_seconds = rng.randint(0, total_seconds)
    return start + timedelta(seconds=random_seconds)


def random_business_hours_datetime(
    date: datetime,
    rng: random.Random = None
) -> datetime:
    """
    Generate a random datetime during business hours (9am–5pm) on a given date.

    Why does this matter?
    Legitimate cash deposits mostly happen during business hours.
    Suspicious transactions sometimes happen at unusual hours — but not always.
    We use this for benign transactions to add realism.

    Args:
        date: The date to use
        rng:  Random number generator

    Returns:
        Datetime with a random hour between 9 and 17, random minutes
    """
    if rng is None:
        rng = random

    hour = rng.randint(9, 16)    # 9am to 4pm (last hour before close)
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)

    return date.replace(hour=hour, minute=minute, second=second, microsecond=0)


def days_range(start: datetime, end: datetime) -> list[datetime]:
    """
    Return a list of datetime objects for every day between start and end.

    Useful for spreading transactions across multiple days in a pattern.

    Args:
        start: First day
        end:   Last day (inclusive)

    Returns:
        List of datetime objects, one per day

    Example:
        dates = days_range(datetime(2024, 1, 1), datetime(2024, 1, 5))
        # [datetime(2024, 1, 1), datetime(2024, 1, 2), ..., datetime(2024, 1, 5)]
    """
    result = []
    current = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end_clean = end.replace(hour=23, minute=59, second=59, microsecond=0)

    while current <= end_clean:
        result.append(current)
        current += timedelta(days=1)

    return result
