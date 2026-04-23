"""
backend/generator/typologies/layering.py
─────────────────────────────────────────────────────────────────────────────
Generates the LAYERING money laundering pattern.

What is layering?
  Moving funds through a chain of 3+ accounts in rapid succession,
  with each transfer slightly reducing the amount (as if taking a "fee").
  The goal is to create enough hops that tracing the original source
  becomes very difficult.

Example real pattern (FATF typology #2):
  Source account: $100,000 at 9:00am
  Account B:      $98,000 at 11:30am (2% fee taken)
  Account C:      $96,040 at 2:15pm  (2% fee taken)
  Destination:    $94,119 at 4:50pm  (2% fee taken)

Why does each hop reduce the amount?
  Because in the real world, each intermediary takes a cut for their
  participation (knowingly or through fake "consulting fees").

Our simulation:
  - Chain of 3–6 accounts
  - Transfers happen within 6–48 hours of each other
  - Each transfer: 95–99% of previous amount (1–5% "fee")
  - Starting amount: $50,000–$500,000

Detection in our graph engine:
  backend/detection/graph/chain_signal.py
  Looks for: directed chains of 3+ hops with amounts decreasing consistently
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from typing import List

from ..transactions import make_transaction

# Chain length: how many accounts money passes through
CHAIN_LENGTH_MIN = 3
CHAIN_LENGTH_MAX = 6

# Starting amount: how much money enters the layering chain
STARTING_AMOUNT_MIN = 50_000.00
STARTING_AMOUNT_MAX = 500_000.00

# Fee per hop: each transfer loses this much (as a fraction of amount)
# 0.01 = 1% fee, 0.05 = 5% fee
FEE_MIN = 0.01
FEE_MAX = 0.05

# Time between hops (in hours)
HOP_DELAY_MIN_HOURS = 1
HOP_DELAY_MAX_HOURS = 24


def generate_layering_transactions(
    account_ids: List[str],
    simulation_start: datetime,
    simulation_end: datetime,
    rng: random.Random = None
) -> List[dict]:
    """
    Generate layering transactions by chaining accounts together.

    We take the list of layering accounts and group them into chains.
    Each chain starts with a source, passes through intermediaries,
    and ends at a destination.

    Args:
        account_ids:      Accounts flagged as "layering" typology.
                          These become the chain members.
        simulation_start: Earliest date any transaction can occur
        simulation_end:   Latest date any transaction can occur
        rng:              Seeded random number generator

    Returns:
        List of transaction dicts representing the chain transfers

    Example for a chain [A, B, C, D]:
        A → B: $100,000 at T+0
        B → C: $98,000  at T+4h
        C → D: $96,040  at T+9h
    """
    if rng is None:
        rng = random

    all_transactions = []

    # Make a mutable copy so we can group accounts into chains
    available_accounts = list(account_ids)
    rng.shuffle(available_accounts)  # randomize so chains aren't always the same accounts

    # Group accounts into chains of CHAIN_LENGTH_MIN to CHAIN_LENGTH_MAX
    chains = []
    idx = 0
    while idx < len(available_accounts):
        # Pick a random chain length
        chain_length = rng.randint(CHAIN_LENGTH_MIN, CHAIN_LENGTH_MAX)
        chain = available_accounts[idx:idx + chain_length]

        # Only use chains that have at least 3 accounts (minimum for meaningful layering)
        if len(chain) >= 3:
            chains.append(chain)

        idx += chain_length

    # Generate transactions for each chain
    for chain in chains:

        # ── Pick when this chain runs ─────────────────────────────────────────
        max_start_offset = (simulation_end - simulation_start).days - 3
        if max_start_offset <= 0:
            continue

        start_offset = rng.randint(0, max_start_offset)
        chain_start = simulation_start + timedelta(days=start_offset)

        # ── Starting amount ───────────────────────────────────────────────────
        amount = rng.uniform(STARTING_AMOUNT_MIN, STARTING_AMOUNT_MAX)

        # ── Current timestamp (advances with each hop) ────────────────────────
        current_time = chain_start

        # ── Walk through the chain ────────────────────────────────────────────
        for hop_index in range(len(chain) - 1):

            sender_id   = chain[hop_index]      # current account in chain
            receiver_id = chain[hop_index + 1]  # next account in chain

            # Each hop takes a fee
            fee_rate = rng.uniform(FEE_MIN, FEE_MAX)
            amount_after_fee = amount * (1 - fee_rate)

            # Time advances by a random delay per hop
            hop_delay_hours = rng.uniform(HOP_DELAY_MIN_HOURS, HOP_DELAY_MAX_HOURS)
            current_time += timedelta(hours=hop_delay_hours)

            # Don't go past the simulation end
            if current_time > simulation_end:
                break

            # Layering uses wire transfers (that's how real layering works)
            descriptions = [
                "consulting fee",
                "management fee",
                "investment transfer",
                "service payment",
                "business transfer",
                "inter-company transfer",
            ]

            tx = make_transaction(
                sender_id=sender_id,
                receiver_id=receiver_id,
                amount=amount_after_fee,
                transaction_date=current_time,
                transaction_type="wire_transfer",
                description=rng.choice(descriptions),
                is_suspicious=True,
                typology="layering",
            )
            all_transactions.append(tx)

            # Amount for the next hop is whatever was received this hop
            amount = amount_after_fee

    return all_transactions
