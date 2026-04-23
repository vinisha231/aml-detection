"""
backend/generator/typologies/mule_network.py
─────────────────────────────────────────────────────────────────────────────
Generates synthetic money mule network transactions.

What is a money mule?
  A money mule is a person (sometimes unwitting) who receives dirty money
  into their account and then transfers it onward at the direction of a
  criminal. They are the "last mile" of the money laundering chain.

  Recruitment methods:
    - Job scams ("work from home, receive and forward payments")
    - Romance scams ("my friend needs to send money, can you help?")
    - Knowingly recruited: in-person criminal networks

  Why launderers use mules:
    - Adds distance between the criminal and the funds
    - Each mule provides plausible deniability
    - Mule accounts look legitimate (real people with real histories)
    - Hard to trace the full network when each mule only knows one hop

Network structure simulated:
  Criminal pool → [Hub mule] → [5–15 spoke mules] → Cash withdrawal or final account

  Hub mule: receives large amount, immediately fans out to spoke mules
  Spoke mules: receive smaller amounts, transfer onward within 24–48h
  Final step: withdrawal to cash (simulated as ACC_CASH_OUT)
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import timedelta
from backend.generator.transactions import make_transaction, random_datetime_in_range


def generate_mule_network_transactions(
    hub_account_id:  str,
    spoke_account_ids: list[str],
    simulation_start,
    simulation_end,
    rng: random.Random,
) -> list[dict]:
    """
    Generate transactions for a money mule hub-and-spoke network.

    Args:
        hub_account_id:    The central hub mule account.
        spoke_account_ids: List of spoke mule accounts (5–15).
        simulation_start:  Start of simulation window.
        simulation_end:    End of simulation window.
        rng:               Seeded RNG for reproducibility.

    Returns:
        List of transaction dicts for hub and all spokes.
    """
    transactions = []

    # Initial funding: a criminal pool sends money to the hub
    n_funding = rng.randint(2, 5)
    activation_date = random_datetime_in_range(
        simulation_start,
        simulation_end - timedelta(days=14),
        rng
    )

    total_received = 0.0

    for i in range(n_funding):
        fund_date = activation_date + timedelta(hours=rng.randint(1, 48) * i)
        amount    = rng.uniform(10_000.0, 50_000.0)
        total_received += amount

        # Criminal pool account (simulated)
        criminal_pool = f'ACC_POOL_{rng.randint(100, 999)}'

        transactions.append(make_transaction(
            sender_id        = criminal_pool,
            receiver_id      = hub_account_id,
            amount           = amount,
            transaction_date = fund_date,
            transaction_type = rng.choice(['ACH', 'WIRE', 'P2P']),
            description      = rng.choice([
                'Payment for services',
                'Freelance work',
                'Invoice settlement',
                'Contract payment',
            ]),
            is_suspicious    = True,
            typology         = 'mule_network',
        ))

    # Hub fans out: distributes funds to spoke accounts within 24–48h
    fan_out_date = activation_date + timedelta(hours=rng.randint(12, 48))

    # Each spoke gets a proportional share, minus the hub's cut (5–15%)
    hub_cut      = rng.uniform(0.05, 0.15)
    distributable = total_received * (1 - hub_cut)
    n_spokes      = len(spoke_account_ids)

    for i, spoke_id in enumerate(spoke_account_ids):
        # Each spoke gets roughly equal share with some variance
        base_share = distributable / n_spokes
        spoke_amount = base_share * rng.uniform(0.80, 1.20)
        spoke_date   = fan_out_date + timedelta(hours=rng.randint(0, 6) * i)

        transactions.append(make_transaction(
            sender_id        = hub_account_id,
            receiver_id      = spoke_id,
            amount           = spoke_amount,
            transaction_date = spoke_date,
            transaction_type = rng.choice(['ACH', 'P2P', 'WIRE']),
            description      = rng.choice([
                'Commission payment',
                'Work payment',
                'Transfer',
                'Compensation',
            ]),
            is_suspicious    = True,
            typology         = 'mule_network',
        ))

        # Spoke immediately withdraws most of their share (within 24h)
        withdrawal_date   = spoke_date + timedelta(hours=rng.randint(2, 24))
        withdrawal_amount = spoke_amount * rng.uniform(0.85, 0.98)

        transactions.append(make_transaction(
            sender_id        = spoke_id,
            receiver_id      = 'ACC_CASH_OUT',
            amount           = withdrawal_amount,
            transaction_date = withdrawal_date,
            transaction_type = 'CASH_WITHDRAWAL',
            description      = 'ATM withdrawal',
            is_suspicious    = True,
            typology         = 'mule_network',
        ))

    return transactions
