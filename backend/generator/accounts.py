"""
backend/generator/accounts.py
─────────────────────────────────────────────────────────────────────────────
Generates synthetic bank accounts for our AML simulation.

This module creates 5,000 fake accounts with realistic attributes.
Some are marked as "dirty" (involved in money laundering typologies),
most are "benign" (normal customers).

Why do we need realistic fake accounts?
  - If account names are clearly fake ("Suspicious McMoneylaunderer"),
    it's not a useful test of our detection system.
  - Real AML detection works on data where the BEHAVIOR is suspicious,
    not the name. Our generator makes names and demographics realistic
    while controlling the transaction behavior.
─────────────────────────────────────────────────────────────────────────────
"""

import random
from datetime import datetime, timedelta
from faker import Faker  # generates realistic fake names, addresses, etc.

# Faker with a seed makes results reproducible
# seed=42 means every run generates THE SAME data (important for comparing results)
fake = Faker()

# Account types found in real banks
ACCOUNT_TYPES = [
    "checking",   # everyday spending account (most common)
    "savings",    # interest-bearing savings
    "business",   # for business accounts (used heavily in shell company typology)
]

# Account type weights: most people have checking accounts
# These probabilities must sum to 1.0
ACCOUNT_TYPE_WEIGHTS = [0.60, 0.25, 0.15]

# Example US bank branches
BRANCHES = [
    "Main Street Branch",
    "Downtown Financial Center",
    "Westside Branch",
    "Airport Road Branch",
    "University District Branch",
    "Harbor View Branch",
    "Midtown Branch",
    "South Side Branch",
]


def generate_account_id(index: int) -> str:
    """
    Generate a unique, formatted account ID.

    We use a fixed-width format so IDs sort correctly as strings.
    ACC_000001, ACC_000002, ..., ACC_005000

    Args:
        index: Sequential number (1-based)

    Returns:
        String like "ACC_000001"

    Example:
        generate_account_id(42)  → "ACC_000042"
    """
    # :06d formats the number as 6 digits, zero-padded
    return f"ACC_{index:06d}"


def generate_account(
    index: int,
    typology: str = "benign",
    rng: random.Random = None
) -> dict:
    """
    Generate one fake bank account with all its attributes.

    Args:
        index:    Sequential account number (used to create account_id)
        typology: One of "benign", "structuring", "layering", "funnel",
                  "round_trip", "shell_company", "velocity"
        rng:      Random number generator (for reproducibility).
                  If None, uses module-level random.

    Returns:
        Dictionary with all account fields matching our schema.Account model.

    Example output:
        {
          "account_id":   "ACC_000042",
          "holder_name":  "Patricia Chen",
          "account_type": "checking",
          "branch":       "Downtown Financial Center",
          "opened_date":  datetime(2021, 3, 15, 0, 0),
          "balance":      12500.00,
          "is_suspicious": False,
          "typology":     "benign"
        }
    """
    if rng is None:
        rng = random

    # Shell company accounts always use "business" account type
    # This is realistic — real shell companies set up business accounts
    if typology == "shell_company":
        account_type = "business"
    else:
        # For all other typologies and benign, pick randomly with realistic weights
        account_type = rng.choices(ACCOUNT_TYPES, weights=ACCOUNT_TYPE_WEIGHTS, k=1)[0]

    # Generate a realistic opening date
    # Accounts can be 1 month to 10 years old
    days_old = rng.randint(30, 3650)
    opened_date = datetime.now() - timedelta(days=days_old)

    # Starting balance depends on account type
    # Business accounts tend to have higher balances
    if account_type == "business":
        balance = round(rng.uniform(10_000, 500_000), 2)
    elif account_type == "savings":
        balance = round(rng.uniform(1_000, 50_000), 2)
    else:  # checking
        balance = round(rng.uniform(500, 25_000), 2)

    # Generate a realistic name using Faker
    # Shell companies get corporate-sounding names
    if typology == "shell_company":
        holder_name = fake.company()  # e.g., "Apex Consulting LLC"
    else:
        holder_name = fake.name()     # e.g., "Patricia Chen"

    return {
        "account_id":    generate_account_id(index),
        "holder_name":   holder_name,
        "account_type":  account_type,
        "branch":        rng.choice(BRANCHES),
        "opened_date":   opened_date,
        "balance":       balance,
        "is_suspicious": typology != "benign",
        "typology":      typology,
        # Risk scores start as None — the detection pipeline fills these in
        "risk_score":    None,
        "evidence":      None,
        "scored_at":     None,
        "disposition":   None,
        "disposition_note": None,
        "disposition_at":   None,
    }


def generate_accounts(
    total_accounts: int = 5000,
    seed: int = 42
) -> tuple[list[dict], dict[str, list[str]]]:
    """
    Generate all accounts for the simulation.

    Account allocation:
      - 10% dirty accounts (500 accounts split across 6 typologies)
      - 90% benign accounts (4,500 normal customers)

    This 10:1 ratio is deliberately optimistic — real banks see 0.1% or less.
    We use 10% to ensure our detection system has enough examples to evaluate.

    Args:
        total_accounts: Total number of accounts to generate (default: 5000)
        seed:           Random seed for reproducibility

    Returns:
        Tuple of:
          - List of account dicts (all accounts in order)
          - Dict mapping typology name → list of account_ids in that typology
            Used by the typology generators to know which accounts to use.

    Example:
        accounts, typology_map = generate_accounts(5000, seed=42)
        print(typology_map["structuring"])
        # ["ACC_000001", "ACC_000015", "ACC_000028", ...]
    """
    rng = random.Random(seed)  # seeded random number generator
    Faker.seed(seed)            # seed Faker for reproducible names

    # ── Step 1: Decide how many accounts per typology ─────────────────────────
    # We want roughly 10% dirty accounts
    dirty_count = int(total_accounts * 0.10)  # 500 dirty accounts
    benign_count = total_accounts - dirty_count  # 4500 benign accounts

    # Distribute dirty accounts across 6 typologies
    # Some typologies need more accounts than others:
    # - shell_company: needs groups of 3-6 accounts per cluster, so more accounts
    # - layering: needs chains of 3-6 accounts, so more accounts
    # - others: can work with just 1 account per pattern
    typology_counts = {
        "structuring":   int(dirty_count * 0.20),   # 100 accounts
        "layering":      int(dirty_count * 0.20),   # 100 accounts (chain members)
        "funnel":        int(dirty_count * 0.15),   # 75 accounts
        "round_trip":    int(dirty_count * 0.15),   # 75 accounts (cycle members)
        "shell_company": int(dirty_count * 0.20),   # 100 accounts (cluster members)
        "velocity":      int(dirty_count * 0.10),   # 50 accounts
    }

    # Make sure counts add up (rounding might leave a few unassigned)
    assigned = sum(typology_counts.values())
    typology_counts["structuring"] += dirty_count - assigned  # assign remainder

    # ── Step 2: Generate accounts in order ────────────────────────────────────
    all_accounts = []
    typology_map = {t: [] for t in typology_counts}
    typology_map["benign"] = []

    # We'll use a counter to assign sequential IDs
    account_index = 1

    # Generate dirty accounts first (they get lower IDs but random behavior)
    for typology, count in typology_counts.items():
        for _ in range(count):
            account = generate_account(account_index, typology=typology, rng=rng)
            all_accounts.append(account)
            typology_map[typology].append(account["account_id"])
            account_index += 1

    # Generate benign accounts
    for _ in range(benign_count):
        account = generate_account(account_index, typology="benign", rng=rng)
        all_accounts.append(account)
        typology_map["benign"].append(account["account_id"])
        account_index += 1

    # Shuffle so dirty accounts aren't all at the start
    # (real data doesn't have all suspicious accounts conveniently grouped)
    rng.shuffle(all_accounts)

    return all_accounts, typology_map
