"""
backend/generator/typologies/shell_company.py
─────────────────────────────────────────────────────────────────────────────
Generates the SHELL COMPANY CLUSTER money laundering pattern.

What is a shell company cluster?
  A group of 3–6 business accounts that ONLY transact with each other.
  They create fake invoices for fake services ("consulting," "management fees")
  and circulate money among themselves to create a paper trail that looks
  like legitimate business activity.

Key characteristics:
  - All transactions are INTERNAL to the cluster (no outside connections)
  - Regular, round-number transaction amounts (suggesting fake invoices)
  - Low variety in transaction descriptions (same "consulting" memo repeated)
  - Business accounts (not personal)

Real-world example (Cyprus, 2016):
  12 shelf companies, all registered by the same law firm.
  Over 3 years, $490M circulated through the cluster in fake consulting fees.
  None of the companies had any real employees, offices, or clients outside the cluster.

Our simulation:
  - Groups of 3–6 accounts
  - Transactions ONLY within the group (enforced by our generator)
  - Regular timing (e.g., monthly invoice cycles)
  - Round amounts: $5,000, $10,000, $25,000, $50,000

Detection in our graph engine:
  backend/detection/graph/community_signal.py
  Louvain community detection finds isolated clusters with no external edges
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from typing import List

from ..transactions import make_transaction

# Cluster size range
CLUSTER_SIZE_MIN = 3
CLUSTER_SIZE_MAX = 6

# Round amounts typical of fake invoicing (look like real invoice amounts)
INVOICE_AMOUNTS = [
    5_000.00,
    7_500.00,
    10_000.00,
    15_000.00,
    20_000.00,
    25_000.00,
    50_000.00,
    75_000.00,
    100_000.00,
]

# How often invoices are paid (every N days)
INVOICE_CYCLE_MIN_DAYS = 7   # weekly
INVOICE_CYCLE_MAX_DAYS = 30  # monthly

# How many invoice cycles run during the simulation
INVOICE_CYCLES_MIN = 3
INVOICE_CYCLES_MAX = 12


def generate_shell_company_transactions(
    account_ids: List[str],
    simulation_start: datetime,
    simulation_end: datetime,
    rng: random.Random = None
) -> List[dict]:
    """
    Generate shell company cluster transactions.

    Takes the list of accounts, groups them into clusters,
    and generates internal-only transactions between cluster members.

    Key property: NO transaction from a cluster member goes to an
    account OUTSIDE the cluster. This isolation is what the graph
    algorithm detects.

    Args:
        account_ids:      Accounts flagged as "shell_company" typology
        simulation_start: Earliest transaction date
        simulation_end:   Latest transaction date
        rng:              Seeded random number generator

    Returns:
        List of transaction dicts — all within cluster groups
    """
    if rng is None:
        rng = random

    all_transactions = []

    # ── Group accounts into clusters ──────────────────────────────────────────
    available = list(account_ids)
    rng.shuffle(available)

    clusters = []
    idx = 0
    while idx < len(available):
        cluster_size = rng.randint(CLUSTER_SIZE_MIN, CLUSTER_SIZE_MAX)
        cluster = available[idx:idx + cluster_size]
        if len(cluster) >= 3:
            clusters.append(cluster)
        idx += cluster_size

    # ── Generate transactions for each cluster ────────────────────────────────
    for cluster in clusters:

        # Determine invoice cycle timing
        cycle_days = rng.randint(INVOICE_CYCLE_MIN_DAYS, INVOICE_CYCLE_MAX_DAYS)
        num_cycles = rng.randint(INVOICE_CYCLES_MIN, INVOICE_CYCLES_MAX)

        # How many days this cluster operates
        operation_days = cycle_days * num_cycles
        if operation_days > (simulation_end - simulation_start).days:
            operation_days = (simulation_end - simulation_start).days

        # Random start within simulation window
        max_start = (simulation_end - simulation_start).days - operation_days
        start_offset = rng.randint(0, max(0, max_start))
        cluster_start = simulation_start + timedelta(days=start_offset)

        # For each invoice cycle, generate transactions within the cluster
        for cycle_num in range(num_cycles):

            # When does this invoice cycle happen?
            cycle_date = cluster_start + timedelta(days=cycle_num * cycle_days)
            if cycle_date > simulation_end:
                break

            # Add small jitter so not every payment is on exactly the same day
            jitter_hours = rng.randint(-12, 12)
            cycle_datetime = cycle_date + timedelta(hours=jitter_hours)

            # In each cycle, several transfers happen within the cluster
            # Number of transfers per cycle: approximately (cluster_size × 1.5) transfers
            tx_per_cycle = rng.randint(len(cluster), len(cluster) * 2)

            for _ in range(tx_per_cycle):
                # Pick a random sender and receiver WITHIN the cluster
                sender_id   = rng.choice(cluster)
                receiver_id = rng.choice(cluster)

                # Don't send to yourself
                while receiver_id == sender_id and len(cluster) > 1:
                    receiver_id = rng.choice(cluster)

                # Round invoice amount
                amount = rng.choice(INVOICE_AMOUNTS)

                # Shell company transaction descriptions (fake invoices)
                descriptions = [
                    "consulting fees",
                    "management fees",
                    "advisory services",
                    "professional services",
                    "service fee",
                    "licensing fee",
                    "administrative fee",
                ]

                # Small time variation within the cycle day
                tx_time = cycle_datetime + timedelta(
                    hours=rng.randint(0, 8),
                    minutes=rng.randint(0, 59)
                )

                tx = make_transaction(
                    sender_id=sender_id,
                    receiver_id=receiver_id,
                    amount=amount,
                    transaction_date=tx_time,
                    transaction_type="wire_transfer",
                    description=rng.choice(descriptions),
                    is_suspicious=True,
                    typology="shell_company",
                )
                all_transactions.append(tx)

    return all_transactions
