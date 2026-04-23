"""
backend/generator/typologies/structuring.py
─────────────────────────────────────────────────────────────────────────────
Generates the STRUCTURING (smurfing) money laundering pattern.

What is structuring?
  Breaking large cash amounts into multiple smaller deposits,
  each just below the $10,000 CTR (Currency Transaction Report) threshold,
  to avoid triggering mandatory bank reporting.

Example real pattern (from FinCEN reports):
  Week 1: $9,500 deposit at Branch A
  Week 1: $9,800 deposit at Branch B
  Week 1: $9,200 deposit at Branch A
  Week 2: $9,650 deposit at Branch C
  ... continues until $100k+ deposited

Our simulation:
  - 5–15 deposits over 3–14 days
  - Each deposit: $9,100 – $9,950
  - Deposits spread randomly but within the window
  - Account has "no legitimate reason" to make repeated near-limit deposits

Detection in our rules engine:
  backend/detection/rules/structuring_rule.py
  Looks for: ≥5 deposits in 14 days, each between $8,500 and $10,000
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from typing import List

# Import the transaction helper from the parent package
from ..transactions import make_transaction, random_business_hours_datetime

# The CTR threshold — structuring happens just below this
CTR_THRESHOLD = 10_000.00

# Range of "structuring" deposit amounts — just under the threshold
# Real structurers often go $9,000–$9,900; we use $9,100–$9,950
STRUCTURING_AMOUNT_MIN = 9_100.00
STRUCTURING_AMOUNT_MAX = 9_950.00

# How many deposits in a structuring pattern
DEPOSIT_COUNT_MIN = 5
DEPOSIT_COUNT_MAX = 15

# Duration of the pattern (in days)
PATTERN_DURATION_MIN = 3
PATTERN_DURATION_MAX = 14

# A "bank" account — we need somewhere the money comes FROM.
# In our simulation, the bank itself is a special account.
BANK_SOURCE_ACCOUNT = "ACC_BANK_SOURCE"


def generate_structuring_transactions(
    account_ids: List[str],
    simulation_start: datetime,
    simulation_end: datetime,
    rng: random.Random = None
) -> List[dict]:
    """
    Generate structuring transactions for a list of accounts.

    Each account in account_ids gets its own structuring pattern —
    multiple deposits just under $10,000 over a short period.

    Args:
        account_ids:      List of account IDs to generate patterns for.
                          These should be accounts flagged as "structuring" typology.
        simulation_start: Earliest date any transaction can occur
        simulation_end:   Latest date any transaction can occur
        rng:              Seeded random number generator

    Returns:
        List of transaction dicts. Each dict matches the Transaction schema.

    Example:
        txs = generate_structuring_transactions(
            account_ids=["ACC_000001", "ACC_000002"],
            simulation_start=datetime(2024, 1, 1),
            simulation_end=datetime(2024, 12, 31),
            rng=random.Random(42)
        )
        # Returns ~10-20 transactions total (5-15 per account)
    """
    if rng is None:
        rng = random

    all_transactions = []

    # Generate a pattern for each structuring account
    for account_id in account_ids:

        # ── Choose when this pattern happens ─────────────────────────────────
        # Pick a random start date within the simulation window
        # Leave enough room at the end for the pattern to complete
        pattern_duration = rng.randint(PATTERN_DURATION_MIN, PATTERN_DURATION_MAX)
        max_start_offset = (simulation_end - simulation_start).days - pattern_duration

        if max_start_offset <= 0:
            # Simulation window too short, skip this account
            continue

        start_offset = rng.randint(0, max_start_offset)
        pattern_start = simulation_start + timedelta(days=start_offset)
        pattern_end   = pattern_start + timedelta(days=pattern_duration)

        # ── Choose how many deposits ──────────────────────────────────────────
        deposit_count = rng.randint(DEPOSIT_COUNT_MIN, DEPOSIT_COUNT_MAX)

        # ── Generate each deposit ─────────────────────────────────────────────
        for deposit_num in range(deposit_count):

            # Pick a random date within the pattern window
            deposit_offset = rng.randint(0, pattern_duration)
            deposit_date = pattern_start + timedelta(days=deposit_offset)

            # Add realistic business hours time
            deposit_datetime = random_business_hours_datetime(deposit_date, rng)

            # Amount just under the CTR threshold
            # Small variation makes it look less mechanical
            amount = rng.uniform(STRUCTURING_AMOUNT_MIN, STRUCTURING_AMOUNT_MAX)

            # Cash deposit descriptions used by structurers
            # Note: they don't write "drug money" — they write normal memos
            descriptions = [
                "cash deposit",
                "deposit",
                "teller deposit",
                "branch deposit",
                "currency deposit",
            ]

            # Create the transaction
            # Sender: the bank source account (represents physical cash)
            # Receiver: the structuring account
            tx = make_transaction(
                sender_id=BANK_SOURCE_ACCOUNT,
                receiver_id=account_id,
                amount=amount,
                transaction_date=deposit_datetime,
                transaction_type="cash_deposit",
                description=rng.choice(descriptions),
                is_suspicious=True,
                typology="structuring",
            )
            all_transactions.append(tx)

    return all_transactions


def is_structuring_amount(amount: float) -> bool:
    """
    Check if a single amount falls in the typical structuring range.

    This is used by the detection rule to quickly filter transactions.

    Args:
        amount: Transaction amount in USD

    Returns:
        True if the amount is in the classic structuring range ($8,500–$10,000)

    Note:
        We use $8,500 as the lower bound in detection (wider than generation range)
        because real structurers sometimes go a bit lower to be less obvious.
    """
    # Detection range is slightly wider than generation range
    # This is intentional — real structuring doesn't always hit the same numbers
    return 8_500.00 <= amount < CTR_THRESHOLD
