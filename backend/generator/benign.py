"""
backend/generator/benign.py
─────────────────────────────────────────────────────────────────────────────
Generates realistic BENIGN (non-suspicious) transactions.

Why do we need benign transactions?
  Without realistic noise, any detection system looks perfect.
  Real AML detection operates at a 1:1000 signal-to-noise ratio.
  We use a 1:10 ratio (10% dirty, 90% benign) to give our system
  a realistic challenge.

What makes a transaction look "benign"?
  - Regular timing (salary on the 1st and 15th, rent on the 1st)
  - Amounts that match the type of transaction (rent is $800-$3000)
  - Transaction descriptions that match real life
  - Variety in counterparties (pays many different merchants)
  - Low total amounts relative to account balance

We simulate these everyday transaction types:
  1. Salary / payroll deposits (from employer to employee)
  2. Rent / mortgage payments (from account to landlord)
  3. Grocery/retail purchases (via debit/ACH)
  4. Utility payments (electricity, internet, phone)
  5. Person-to-person transfers (splitting dinner, paying a friend)
  6. ATM withdrawals
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from typing import List

from faker import Faker
from .transactions import make_transaction, random_business_hours_datetime

fake = Faker()

# ─── Constants for benign transaction parameters ──────────────────────────────

# Salary amounts (annual, divided by 26 for biweekly)
SALARY_ANNUAL_MIN = 35_000
SALARY_ANNUAL_MAX = 150_000

# Rent amounts (monthly)
RENT_MIN = 800
RENT_MAX = 3_500

# Grocery/retail purchase amounts
GROCERY_AMOUNT_MIN = 20
GROCERY_AMOUNT_MAX = 250

# Utility payment amounts
UTILITY_AMOUNT_MIN = 50
UTILITY_AMOUNT_MAX = 400

# Person-to-person transfer amounts
P2P_AMOUNT_MIN = 20
P2P_AMOUNT_MAX = 500

# ATM withdrawal amounts (typically multiples of $20)
ATM_AMOUNTS = [20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 300, 400, 500]

# Fake merchant / payee names for variety
EMPLOYER_NAMES = [
    "Acme Corp", "TechStartup Inc", "Global Services LLC",
    "State Hospital", "City School District", "Metro Transit Authority",
    "Regional Bank", "University Medical Center", "Downtown Restaurant Group",
]

LANDLORD_NAMES = [
    "Sunrise Property Management", "City Apartments LLC",
    "Suburban Realty Group", "Prime Real Estate Holdings",
    "Main Street Properties", "Riverside Apartments",
]

UTILITY_PAYEES = [
    "City Electric Co", "Metro Water Authority", "Gas & Power Inc",
    "FastNet Internet", "Mobile Wireless Co", "Cable Vision",
]

GROCERY_PAYEES = [
    "Whole Foods", "Kroger", "Walmart", "Target", "Costco",
    "Trader Joes", "Safeway", "Publix", "Aldi", "Sprouts",
]


def generate_benign_transactions(
    account_ids: List[str],
    all_account_ids: List[str],
    simulation_start: datetime,
    simulation_end: datetime,
    rng: random.Random = None
) -> List[dict]:
    """
    Generate all benign transactions for the given accounts.

    Each account gets a realistic mix of:
    - Biweekly salary deposits
    - Monthly rent payments
    - Weekly grocery purchases
    - Monthly utility payments
    - Occasional person-to-person transfers

    The total volume target is ~10x the dirty transaction count,
    making the dirty transactions realistic to find.

    Args:
        account_ids:      Accounts to generate benign transactions for
        all_account_ids:  All account IDs (for P2P transfers)
        simulation_start: Start of simulation window
        simulation_end:   End of simulation window
        rng:              Seeded random number generator

    Returns:
        List of transaction dicts (all is_suspicious=False, typology="benign")
    """
    if rng is None:
        rng = random

    all_transactions = []
    simulation_days = (simulation_end - simulation_start).days

    for account_id in account_ids:

        # ── 1. Salary deposits (biweekly from employer) ───────────────────────
        annual_salary = rng.randint(SALARY_ANNUAL_MIN, SALARY_ANNUAL_MAX)
        biweekly_salary = annual_salary / 26  # 26 pay periods per year

        # Pick a payday (1st or 15th, or the Friday closest to those)
        # Simplified: payday every 14 days starting from a random offset
        payday_offset = rng.randint(0, 13)  # start the first payday 0-13 days in
        payday = simulation_start + timedelta(days=payday_offset)

        employer = rng.choice(EMPLOYER_NAMES)

        while payday <= simulation_end:
            # Small variation in payday amount (bonuses, overtime)
            variation = rng.uniform(0.95, 1.10)  # ±5-10% variation
            salary_amount = biweekly_salary * variation

            # Salary arrives early in the morning (bank processing)
            pay_time = payday.replace(
                hour=rng.randint(6, 9),
                minute=rng.randint(0, 59),
                second=0
            )

            if pay_time > simulation_end:
                break

            tx = make_transaction(
                sender_id="ACC_PAYROLL",  # payroll system as sender
                receiver_id=account_id,
                amount=round(salary_amount, 2),
                transaction_date=pay_time,
                transaction_type="ach",
                description=f"PAYROLL {employer}",
                is_suspicious=False,
                typology="benign",
            )
            all_transactions.append(tx)
            payday += timedelta(days=14)  # next payday

        # ── 2. Monthly rent payments ─────────────────────────────────────────
        rent_amount = rng.randint(RENT_MIN, RENT_MAX)
        landlord = rng.choice(LANDLORD_NAMES)

        # Rent is due the 1st of each month (or a few days before)
        rent_day = rng.randint(1, 5)  # between the 1st and 5th

        current_month = simulation_start.replace(day=1)
        while current_month <= simulation_end:
            rent_date = current_month.replace(
                day=min(rent_day, 28),  # avoid invalid dates like Feb 31
                hour=rng.randint(8, 12),
                minute=rng.randint(0, 59),
                second=0
            )

            if simulation_start <= rent_date <= simulation_end:
                tx = make_transaction(
                    sender_id=account_id,
                    receiver_id="ACC_LANDLORD",  # landlord is a special account
                    amount=float(rent_amount),
                    transaction_date=rent_date,
                    transaction_type="ach",
                    description=f"RENT {landlord}",
                    is_suspicious=False,
                    typology="benign",
                )
                all_transactions.append(tx)

            # Move to next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        # ── 3. Weekly grocery/retail purchases ───────────────────────────────
        # Most people shop 1-3 times per week
        grocery_trips_per_week = rng.randint(1, 3)
        grocery_trip = simulation_start + timedelta(days=rng.randint(0, 6))

        while grocery_trip <= simulation_end:
            for _ in range(grocery_trips_per_week):
                if grocery_trip > simulation_end:
                    break

                trip_time = random_business_hours_datetime(grocery_trip, rng)
                grocery_amount = rng.uniform(GROCERY_AMOUNT_MIN, GROCERY_AMOUNT_MAX)
                merchant = rng.choice(GROCERY_PAYEES)

                tx = make_transaction(
                    sender_id=account_id,
                    receiver_id="ACC_RETAIL",
                    amount=round(grocery_amount, 2),
                    transaction_date=trip_time,
                    transaction_type="ach",
                    description=f"PURCHASE {merchant}",
                    is_suspicious=False,
                    typology="benign",
                )
                all_transactions.append(tx)

            grocery_trip += timedelta(days=7)

        # ── 4. Monthly utility payments ──────────────────────────────────────
        for utility in rng.sample(UTILITY_PAYEES, k=rng.randint(2, 4)):
            utility_amount = rng.uniform(UTILITY_AMOUNT_MIN, UTILITY_AMOUNT_MAX)
            utility_day = rng.randint(1, 28)

            utility_month = simulation_start.replace(day=1)
            while utility_month <= simulation_end:
                bill_date = utility_month.replace(
                    day=min(utility_day, 28),
                    hour=rng.randint(8, 20),
                    minute=rng.randint(0, 59),
                    second=0
                )

                if simulation_start <= bill_date <= simulation_end:
                    # Bills vary slightly each month
                    bill_amount = utility_amount * rng.uniform(0.85, 1.20)
                    tx = make_transaction(
                        sender_id=account_id,
                        receiver_id="ACC_UTILITY",
                        amount=round(bill_amount, 2),
                        transaction_date=bill_date,
                        transaction_type="ach",
                        description=f"BILL {utility}",
                        is_suspicious=False,
                        typology="benign",
                    )
                    all_transactions.append(tx)

                # Next month
                if utility_month.month == 12:
                    utility_month = utility_month.replace(
                        year=utility_month.year + 1, month=1
                    )
                else:
                    utility_month = utility_month.replace(
                        month=utility_month.month + 1
                    )

        # ── 5. Occasional person-to-person transfers ──────────────────────────
        # 2-8 P2P transfers over the simulation period
        p2p_count = rng.randint(2, 8)
        other_accounts = [a for a in all_account_ids if a != account_id]

        for _ in range(p2p_count):
            p2p_offset = rng.randint(0, simulation_days)
            p2p_date = simulation_start + timedelta(days=p2p_offset)
            p2p_datetime = random_business_hours_datetime(p2p_date, rng)

            if p2p_datetime > simulation_end:
                continue

            p2p_amount = rng.uniform(P2P_AMOUNT_MIN, P2P_AMOUNT_MAX)
            recipient = rng.choice(other_accounts) if other_accounts else account_id

            p2p_descriptions = [
                "dinner split", "reimbursement", "rent split",
                "birthday gift", "vacation fund", "loan repayment"
            ]

            tx = make_transaction(
                sender_id=account_id,
                receiver_id=recipient,
                amount=round(p2p_amount, 2),
                transaction_date=p2p_datetime,
                transaction_type="internal_transfer",
                description=rng.choice(p2p_descriptions),
                is_suspicious=False,
                typology="benign",
            )
            all_transactions.append(tx)

    return all_transactions
