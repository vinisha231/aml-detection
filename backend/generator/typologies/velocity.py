"""
backend/generator/typologies/velocity.py
─────────────────────────────────────────────────────────────────────────────
Generates the VELOCITY ANOMALY (dormant account activation) pattern.

What is a velocity anomaly?
  An account that was INACTIVE for an extended period suddenly
  conducts many transactions in a short time burst.

This pattern appears in:
  1. Account takeover fraud: criminal gains access to a dormant account
     and rapidly drains it through many small transfers
  2. Money mule activation: a "mule" account sits dormant, then is
     suddenly used to receive and forward criminal funds
  3. Compromised account schemes: bulk-purchased account credentials
     all activated at once

Our simulation:
  - Account has 0–2 transactions/month for at least 60 days (dormancy period)
  - Then: 30–100 transactions in 24–72 hours (the burst)
  - Burst transactions: small amounts ($150–$800) to 1–3 destinations
  - Then: returns to dormancy (or stays active — we don't continue)

Detection in our rules engine:
  backend/detection/rules/velocity_rule.py
  Compares transaction rate in last 7 days vs. previous 30-day baseline
  Flags accounts where ratio > 10x (30x is typical for real cases)
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from typing import List

from ..transactions import make_transaction

# How long the account must be dormant before the burst
DORMANCY_DAYS_MIN = 60
DORMANCY_DAYS_MAX = 365  # can be dormant for up to a year

# How many transactions in the burst
BURST_TX_MIN = 30
BURST_TX_MAX = 100

# Duration of the burst (in hours)
BURST_DURATION_HOURS_MIN = 6
BURST_DURATION_HOURS_MAX = 72

# Individual burst transaction amount
BURST_AMOUNT_MIN = 150.00
BURST_AMOUNT_MAX = 800.00

# Number of destination accounts during burst (few destinations = suspicious)
BURST_DESTINATIONS_MIN = 1
BURST_DESTINATIONS_MAX = 3


def generate_velocity_transactions(
    account_ids: List[str],
    all_account_ids: List[str],
    simulation_start: datetime,
    simulation_end: datetime,
    rng: random.Random = None
) -> List[dict]:
    """
    Generate velocity anomaly transactions.

    For each velocity account:
    1. Generate a sparse dormancy period (0-2 random transactions)
    2. Generate a dense burst of 30-100 transactions over 24-72 hours
    3. All burst transactions go to 1-3 random destination accounts

    Args:
        account_ids:     Accounts flagged as "velocity" typology
        all_account_ids: All account IDs (to pick burst destinations from)
        simulation_start: Earliest transaction date
        simulation_end:   Latest transaction date
        rng:              Seeded random number generator

    Returns:
        List of transaction dicts
    """
    if rng is None:
        rng = random

    all_transactions = []

    # Accounts that can be burst destinations (not the velocity accounts themselves)
    potential_destinations = [a for a in all_account_ids if a not in account_ids]

    for account_id in account_ids:

        # ── 1. Determine the dormancy period ──────────────────────────────────
        dormancy_days = rng.randint(DORMANCY_DAYS_MIN, DORMANCY_DAYS_MAX)

        # Make sure we have enough room in the simulation for dormancy + burst
        total_needed_days = dormancy_days + 3  # 3 extra for the burst
        max_start = (simulation_end - simulation_start).days - total_needed_days

        if max_start <= 0:
            # Simulation window too short
            continue

        dormancy_start = simulation_start
        dormancy_end   = dormancy_start + timedelta(days=dormancy_days)
        burst_start    = dormancy_end

        # ── 2. Generate sparse dormancy transactions (looks legitimate) ────────
        # 0 to 2 transactions during the dormancy period
        dormant_tx_count = rng.randint(0, 2)

        for _ in range(dormant_tx_count):
            # Random date during dormancy
            dormant_offset = rng.randint(0, dormancy_days)
            dormant_date = dormancy_start + timedelta(days=dormant_offset)
            dormant_datetime = dormant_date.replace(
                hour=rng.randint(9, 17),
                minute=rng.randint(0, 59),
                second=0
            )

            # Small, routine transaction (looks like a utility bill or subscription)
            dormant_descriptions = [
                "subscription", "utility payment", "insurance", "membership"
            ]

            # Random counterparty
            if potential_destinations:
                counterparty = rng.choice(potential_destinations)
                tx = make_transaction(
                    sender_id=account_id,
                    receiver_id=counterparty,
                    amount=rng.uniform(10.00, 200.00),
                    transaction_date=dormant_datetime,
                    transaction_type="ach",
                    description=rng.choice(dormant_descriptions),
                    is_suspicious=False,  # dormancy period is NOT suspicious
                    typology="benign",    # marked benign (this is normal activity)
                )
                all_transactions.append(tx)

        # ── 3. Generate the burst ─────────────────────────────────────────────
        burst_tx_count = rng.randint(BURST_TX_MIN, BURST_TX_MAX)
        burst_duration_hours = rng.uniform(
            BURST_DURATION_HOURS_MIN, BURST_DURATION_HOURS_MAX
        )
        burst_end = burst_start + timedelta(hours=burst_duration_hours)

        if burst_end > simulation_end:
            burst_end = simulation_end

        # Pick 1-3 destination accounts for the burst
        # Few destinations is a key red flag — criminal sends to specific mules
        num_destinations = rng.randint(BURST_DESTINATIONS_MIN, BURST_DESTINATIONS_MAX)
        if len(potential_destinations) >= num_destinations:
            destinations = rng.sample(potential_destinations, k=num_destinations)
        else:
            destinations = potential_destinations or [account_id]

        # Distribute burst transactions evenly over the burst window
        burst_window_seconds = (burst_end - burst_start).total_seconds()
        if burst_window_seconds <= 0:
            continue

        for tx_num in range(burst_tx_count):
            # Spread transactions over the burst window
            tx_offset_seconds = rng.uniform(0, burst_window_seconds)
            tx_datetime = burst_start + timedelta(seconds=tx_offset_seconds)

            if tx_datetime > simulation_end:
                break

            amount = rng.uniform(BURST_AMOUNT_MIN, BURST_AMOUNT_MAX)
            destination = rng.choice(destinations)

            burst_descriptions = [
                "transfer", "payment", "send", "remittance",
                "account transfer", "ach transfer"
            ]

            tx = make_transaction(
                sender_id=account_id,
                receiver_id=destination,
                amount=amount,
                transaction_date=tx_datetime,
                transaction_type=rng.choice(["ach", "wire_transfer"]),
                description=rng.choice(burst_descriptions),
                is_suspicious=True,
                typology="velocity",
            )
            all_transactions.append(tx)

    return all_transactions
