"""
backend/generator/typologies/funnel.py
─────────────────────────────────────────────────────────────────────────────
Generates the FUNNEL ACCOUNT (fan-in / fan-out) money laundering pattern.

What is a funnel account?
  An account that:
  1. Receives many small payments from many different senders (fan-in)
  2. Then sends one or a few large payments to a small number of destinations (fan-out)

The funnel account acts like a collection point — aggregating funds
from many sources before forwarding them onward.

Real-world examples:
  - Human trafficking: victims/clients send payments to one central account
  - Drug sales: many street-level sales collected into one distribution account
  - Tax fraud rings: many fake refund claims funneled to one account

Our simulation:
  - 1 funnel account (the "collector")
  - 20–80 senders (can be benign accounts or other dirty accounts)
  - Small incoming amounts: $100–$2,000 each
  - 1–3 large outgoing transfers (80–95% of collected amount)
  - All activity within 7–30 days

Detection in our rules engine:
  backend/detection/rules/funnel_rule.py
  Looks for: in-degree ≥ 20 with fan-in ratio > 10:1 (senders vs receivers)
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from typing import List

from ..transactions import make_transaction, random_business_hours_datetime

# How many incoming transactions the funnel account receives
FAN_IN_MIN = 20
FAN_IN_MAX = 80

# Individual incoming payment size
INCOMING_AMOUNT_MIN = 100.00
INCOMING_AMOUNT_MAX = 2_000.00

# What fraction of collected funds goes out in the final "push"
OUTFLOW_FRACTION_MIN = 0.80  # at least 80% goes out
OUTFLOW_FRACTION_MAX = 0.95  # at most 95% goes out (some "held back")

# How many outgoing transfers the funnel sends
OUTFLOW_COUNT_MIN = 1
OUTFLOW_COUNT_MAX = 3

# Duration of the incoming phase
COLLECTION_DAYS_MIN = 7
COLLECTION_DAYS_MAX = 30


def generate_funnel_transactions(
    account_ids: List[str],
    all_account_ids: List[str],
    simulation_start: datetime,
    simulation_end: datetime,
    rng: random.Random = None
) -> List[dict]:
    """
    Generate funnel pattern transactions.

    Every account in account_ids becomes a funnel account.
    Each funnel receives many small payments from random senders,
    then sends a large payment to a small number of destinations.

    Args:
        account_ids:     Accounts flagged as "funnel" typology
        all_account_ids: All account IDs in the simulation
                         (used to pick random senders for the fan-in phase)
        simulation_start: Earliest date for transactions
        simulation_end:   Latest date for transactions
        rng:              Seeded random number generator

    Returns:
        List of transaction dicts
    """
    if rng is None:
        rng = random

    all_transactions = []

    # Get accounts that are NOT funnel accounts to use as senders
    # (real funnel patterns receive from many unrelated accounts)
    non_funnel_accounts = [a for a in all_account_ids if a not in account_ids]

    for funnel_account_id in account_ids:

        # ── Choose timing ────────────────────────────────────────────────────
        collection_days = rng.randint(COLLECTION_DAYS_MIN, COLLECTION_DAYS_MAX)
        max_start = (simulation_end - simulation_start).days - collection_days - 7
        if max_start <= 0:
            continue

        start_offset = rng.randint(0, max_start)
        collection_start = simulation_start + timedelta(days=start_offset)
        collection_end   = collection_start + timedelta(days=collection_days)

        # ── Fan-in phase: receive many small payments ─────────────────────────
        fan_in_count = rng.randint(FAN_IN_MIN, FAN_IN_MAX)

        # Pick random senders from the non-funnel pool
        if len(non_funnel_accounts) < fan_in_count:
            # If not enough unique accounts, allow repeats
            senders = rng.choices(non_funnel_accounts, k=fan_in_count)
        else:
            # Prefer unique senders (more realistic — many different people paying)
            senders = rng.sample(non_funnel_accounts, k=fan_in_count)

        total_collected = 0.0

        for sender_id in senders:
            # Random date within collection window
            day_offset = rng.randint(0, collection_days)
            tx_date = collection_start + timedelta(days=day_offset)
            tx_datetime = random_business_hours_datetime(tx_date, rng)

            amount = rng.uniform(INCOMING_AMOUNT_MIN, INCOMING_AMOUNT_MAX)
            total_collected += amount

            # Descriptions suggest legitimate-looking small payments
            descriptions = [
                "payment", "transfer", "invoice payment", "fee",
                "service", "contribution", "dues", "membership"
            ]

            tx = make_transaction(
                sender_id=sender_id,
                receiver_id=funnel_account_id,
                amount=amount,
                transaction_date=tx_datetime,
                transaction_type=rng.choice(["ach", "wire_transfer"]),
                description=rng.choice(descriptions),
                is_suspicious=True,
                typology="funnel",
            )
            all_transactions.append(tx)

        # ── Fan-out phase: send a large payment to 1-3 destinations ──────────
        outflow_count = rng.randint(OUTFLOW_COUNT_MIN, OUTFLOW_COUNT_MAX)

        # Pick random destinations (different from senders — another layer)
        destinations = rng.choices(non_funnel_accounts, k=outflow_count)

        # Total to send out
        total_to_send = total_collected * rng.uniform(
            OUTFLOW_FRACTION_MIN, OUTFLOW_FRACTION_MAX
        )

        # Split total_to_send across the outflow count
        # Use Dirichlet-like split: random fractions that sum to 1
        if outflow_count == 1:
            fractions = [1.0]
        else:
            # Simple split: random numbers normalized to sum to 1
            raw = [rng.random() for _ in range(outflow_count)]
            total_raw = sum(raw)
            fractions = [r / total_raw for r in raw]

        # Outflows happen shortly AFTER the collection period ends
        for i, (destination_id, fraction) in enumerate(zip(destinations, fractions)):
            outflow_amount = total_to_send * fraction

            # Outflow happens 1-5 days after collection ends
            outflow_offset = rng.randint(1, 5)
            outflow_date = collection_end + timedelta(days=outflow_offset)

            if outflow_date > simulation_end:
                outflow_date = simulation_end

            outflow_datetime = random_business_hours_datetime(outflow_date, rng)

            # Outflows look like large wire transfers
            outflow_descriptions = [
                "wire transfer", "investment", "capital transfer",
                "business payment", "distribution"
            ]

            tx = make_transaction(
                sender_id=funnel_account_id,
                receiver_id=destination_id,
                amount=outflow_amount,
                transaction_date=outflow_datetime,
                transaction_type="wire_transfer",
                description=rng.choice(outflow_descriptions),
                is_suspicious=True,
                typology="funnel",
            )
            all_transactions.append(tx)

    return all_transactions
