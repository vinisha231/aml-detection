"""
backend/generator/typologies/trade_based.py
─────────────────────────────────────────────────────────────────────────────
Generates synthetic Trade-Based Money Laundering (TBML) transactions.

What is Trade-Based Money Laundering?
  TBML is one of the most sophisticated AML typologies. It exploits
  international trade transactions to disguise money flows.

  Common techniques:
    1. Over/under-invoicing: An importer pays $100,000 for goods worth $30,000.
       The extra $70,000 is the money laundering payment.

    2. Multiple invoicing: Same goods are invoiced multiple times across
       different jurisdictions.

    3. Phantom shipments: Invoices are created for goods that don't exist.
       The payment transfers money internationally under the guise of trade.

  Why it's hard to detect:
    - Banks see only the financial transaction, not the underlying goods
    - Trade finance (letters of credit) involves many legitimate parties
    - International nature makes it hard for any single regulator to see the full picture

How we simulate it:
  - Creates wire transfers described as "TRADE_PAYMENT" or "IMPORT_INVOICE"
  - Amounts are round numbers (invoiced amounts tend to be round)
  - Transactions pair with a foreign account (simulated as 'INT_' prefix)
  - The amount is inconsistent with the account's normal transaction history
    (e.g., a retail account suddenly doing $500k wire transfers)
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import timedelta
from backend.generator.transactions import make_transaction, random_datetime_in_range


def generate_trade_based_transactions(
    account_id:      str,
    all_account_ids: list[str],
    simulation_start,
    simulation_end,
    rng: random.Random,
) -> list[dict]:
    """
    Generate trade-based money laundering transactions for one account.

    Pattern:
      - 3–8 large wire transfers described as international trade payments
      - Paired with fictitious import/export counter-parties ('INT_' prefix)
      - Round or near-round USD amounts ($50k–$500k)
      - Sent within a compressed timeframe (2–8 weeks)
      - May also receive an 'overpayment refund' to simulate over-invoicing

    Args:
        account_id:      The account committing the TBML.
        all_account_ids: All accounts in the simulation (to pick some counterparties).
        simulation_start: Start of simulation period.
        simulation_end:   End of simulation period.
        rng:             Seeded random number generator for reproducibility.

    Returns:
        List of transaction dicts.
    """
    transactions = []

    # Number of trade payment transactions
    n_payments = rng.randint(3, 8)

    # Each trade payment is a round amount (invoices are typically round sums)
    amounts = [
        rng.choice([50_000, 75_000, 100_000, 150_000, 200_000, 250_000, 500_000])
        for _ in range(n_payments)
    ]

    # TBML happens in a burst (all transactions within a few weeks)
    burst_start = random_datetime_in_range(
        simulation_start,
        simulation_end - timedelta(weeks=8),
        rng
    )

    for i, amount in enumerate(amounts):
        # Each payment is 2–7 days after the last (urgent trade cycle)
        tx_date = burst_start + timedelta(days=rng.randint(2, 7) * (i + 1))
        if tx_date > simulation_end:
            tx_date = simulation_end - timedelta(days=rng.randint(1, 5))

        # International counterparty (simulated with INT_ prefix)
        foreign_account = f'INT_{rng.randint(1000, 9999)}'

        # Outbound: account pays the 'importer' for fake goods
        transactions.append(make_transaction(
            sender_id        = account_id,
            receiver_id      = foreign_account,
            amount           = amount,
            transaction_date = tx_date,
            transaction_type = 'WIRE',
            description      = rng.choice([
                f'TRADE_PAYMENT Invoice #{rng.randint(10000, 99999)}',
                f'IMPORT_INVOICE #{rng.randint(1000, 9999)}-{rng.randint(10, 99)}',
                'INTERNATIONAL TRADE SETTLEMENT',
                f'EXPORT PROCEEDS REF/{rng.randint(100000, 999999)}',
            ]),
            is_suspicious    = True,
            typology         = 'trade_based',
        ))

        # Simulate over-invoicing: occasionally receive a partial 'refund'
        # (the overpaid portion laundered back)
        if rng.random() < 0.35:  # 35% of trade payments have a refund
            refund_amount = amount * rng.uniform(0.10, 0.30)  # 10–30% refund
            refund_date   = tx_date + timedelta(days=rng.randint(3, 14))

            transactions.append(make_transaction(
                sender_id        = foreign_account,
                receiver_id      = account_id,
                amount           = refund_amount,
                transaction_date = refund_date,
                transaction_type = 'WIRE',
                description      = f'REFUND OVERPAYMENT INV#{rng.randint(10000, 99999)}',
                is_suspicious    = True,
                typology         = 'trade_based',
            ))

    return transactions
