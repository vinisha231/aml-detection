"""
backend/generator/typologies/round_trip.py
─────────────────────────────────────────────────────────────────────────────
Generates the ROUND-TRIPPING (circular flow) money laundering pattern.

What is round-tripping?
  Money leaves Account A, passes through intermediaries, and eventually
  returns to Account A — appearing to come from a "different source."

The criminal claims the returning money is:
  - Investment returns
  - Business income
  - Loan repayment

But it's the SAME money that left, now appearing to be legitimately earned.

Example from FATF:
  A corrupt official receives $200k in bribe money
  → Sends to Company B (offshore shell)
  → Company B sends to Company C (another jurisdiction)
  → Company C wires back to the official as "investment returns"
  → Official reports this as legitimate business income

Our simulation:
  - Cycle of 3–5 accounts
  - Full cycle completes within 3–21 days
  - Each hop reduces amount by 2–8% (to simulate fees/conversion)
  - The SAME money returns to the originating account

Detection in our graph engine:
  backend/detection/graph/cycle_signal.py
  Uses NetworkX simple_cycles() to find accounts that appear in cycles
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from typing import List

from ..transactions import make_transaction

# How many accounts are in each cycle
CYCLE_LENGTH_MIN = 3
CYCLE_LENGTH_MAX = 5

# Total days for the money to complete the full round trip
CYCLE_DURATION_MIN_DAYS = 3
CYCLE_DURATION_MAX_DAYS = 21

# Starting amount for the round trip
ROUND_TRIP_AMOUNT_MIN = 10_000.00
ROUND_TRIP_AMOUNT_MAX = 200_000.00

# Fee per hop (fraction of amount taken as "fee")
HOP_FEE_MIN = 0.02  # 2%
HOP_FEE_MAX = 0.08  # 8%


def generate_round_trip_transactions(
    account_ids: List[str],
    simulation_start: datetime,
    simulation_end: datetime,
    rng: random.Random = None
) -> List[dict]:
    """
    Generate round-trip (circular flow) transactions.

    Takes the list of accounts and forms them into cycles.
    For a cycle [A, B, C], generates:
      A → B: large transfer
      B → C: slightly less (fee taken)
      C → A: slightly less again (fee taken)

    The key: A is both the SENDER of the first transaction AND the
    RECEIVER of the last transaction. This creates a graph cycle.

    Args:
        account_ids:      Accounts flagged as "round_trip" typology
        simulation_start: Earliest transaction date
        simulation_end:   Latest transaction date
        rng:              Seeded random number generator

    Returns:
        List of transaction dicts forming cycles
    """
    if rng is None:
        rng = random

    all_transactions = []

    # Make a copy to group into cycles
    available = list(account_ids)
    rng.shuffle(available)

    # Group into cycles
    cycles = []
    idx = 0
    while idx < len(available):
        cycle_length = rng.randint(CYCLE_LENGTH_MIN, CYCLE_LENGTH_MAX)
        cycle = available[idx:idx + cycle_length]

        if len(cycle) >= 3:
            cycles.append(cycle)
        elif len(cycle) >= 2:
            # Too short for a meaningful cycle — add to last cycle if possible
            if cycles:
                cycles[-1].extend(cycle)

        idx += cycle_length

    for cycle in cycles:

        # ── Choose timing for this cycle ──────────────────────────────────────
        cycle_duration = rng.randint(CYCLE_DURATION_MIN_DAYS, CYCLE_DURATION_MAX_DAYS)
        max_start = (simulation_end - simulation_start).days - cycle_duration
        if max_start <= 0:
            continue

        start_offset = rng.randint(0, max_start)
        cycle_start = simulation_start + timedelta(days=start_offset)

        # ── Starting amount ────────────────────────────────────────────────────
        amount = rng.uniform(ROUND_TRIP_AMOUNT_MIN, ROUND_TRIP_AMOUNT_MAX)

        # ── Time step between each hop in the cycle ───────────────────────────
        # Divide the total cycle duration among the hops
        hops = len(cycle)  # number of transfers (including the return hop)
        # Time between hops in seconds
        cycle_total_seconds = cycle_duration * 24 * 3600
        hop_time_seconds = cycle_total_seconds / hops

        current_time = cycle_start

        # ── Generate transfers around the cycle ───────────────────────────────
        # Cycle: [A, B, C] → transfers: A→B, B→C, C→A
        for hop_index in range(len(cycle)):

            # Sender: current account in cycle
            sender_id = cycle[hop_index]

            # Receiver: next account in cycle (wraps around at the end)
            receiver_id = cycle[(hop_index + 1) % len(cycle)]

            # Apply fee
            fee_rate = rng.uniform(HOP_FEE_MIN, HOP_FEE_MAX)
            transfer_amount = amount * (1 - fee_rate)

            # Advance time
            time_jitter_seconds = int(hop_time_seconds * rng.uniform(0.8, 1.2))
            current_time += timedelta(seconds=time_jitter_seconds)

            if current_time > simulation_end:
                break

            # Round-trip transfers look like legitimate business payments
            descriptions = [
                "investment return",
                "loan repayment",
                "dividend payment",
                "consulting payment",
                "profit distribution",
                "capital return",
            ]

            tx = make_transaction(
                sender_id=sender_id,
                receiver_id=receiver_id,
                amount=transfer_amount,
                transaction_date=current_time,
                transaction_type="wire_transfer",
                description=rng.choice(descriptions),
                is_suspicious=True,
                typology="round_trip",
            )
            all_transactions.append(tx)

            # Amount for next hop
            amount = transfer_amount

    return all_transactions
