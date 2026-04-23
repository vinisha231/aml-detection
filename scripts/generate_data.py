"""
scripts/generate_data.py
─────────────────────────────────────────────────────────────────────────────
Generates all synthetic data and populates the SQLite database.

Run this ONCE before running the detection pipeline.
Running it again WIPES and RECREATES the database (fresh start).

What this script does:
  1. Creates (or recreates) the SQLite database at data/aml.db
  2. Generates 5,000 fake bank accounts
  3. Generates ~100,000 transactions:
     - 6 typology patterns (dirty data)
     - Benign everyday transactions (salary, rent, groceries) for all accounts
  4. Saves everything to the database
  5. Prints a summary

Usage:
    python scripts/generate_data.py
    python scripts/generate_data.py --accounts 1000 --seed 99
    python scripts/generate_data.py --accounts 5000 --seed 42 --start 2024-01-01
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# tqdm shows a progress bar — makes long operations feel less scary
from tqdm import tqdm

from backend.database.schema import (
    get_engine,
    create_all_tables,
    get_session_factory,
    Account,
    Transaction,
)
from backend.generator.accounts import generate_accounts
from backend.generator.transactions import reset_transaction_counter
from backend.generator.benign import generate_benign_transactions
from backend.generator.typologies import (
    generate_structuring_transactions,
    generate_layering_transactions,
    generate_funnel_transactions,
    generate_round_trip_transactions,
    generate_shell_company_transactions,
    generate_velocity_transactions,
)

# The bank source account — represents "cash from outside the banking system"
SYSTEM_ACCOUNTS = [
    {"account_id": "ACC_BANK_SOURCE", "holder_name": "Bank Cash Vault",        "account_type": "internal", "branch": "HQ", "opened_date": datetime(2000, 1, 1), "balance": 0.0, "is_suspicious": False, "typology": "benign", "risk_score": None, "evidence": None, "scored_at": None, "disposition": None, "disposition_note": None, "disposition_at": None},
    {"account_id": "ACC_PAYROLL",     "holder_name": "Payroll System",          "account_type": "internal", "branch": "HQ", "opened_date": datetime(2000, 1, 1), "balance": 0.0, "is_suspicious": False, "typology": "benign", "risk_score": None, "evidence": None, "scored_at": None, "disposition": None, "disposition_note": None, "disposition_at": None},
    {"account_id": "ACC_LANDLORD",    "holder_name": "Property Management LLC", "account_type": "internal", "branch": "HQ", "opened_date": datetime(2000, 1, 1), "balance": 0.0, "is_suspicious": False, "typology": "benign", "risk_score": None, "evidence": None, "scored_at": None, "disposition": None, "disposition_note": None, "disposition_at": None},
    {"account_id": "ACC_RETAIL",      "holder_name": "Retail Merchants",        "account_type": "internal", "branch": "HQ", "opened_date": datetime(2000, 1, 1), "balance": 0.0, "is_suspicious": False, "typology": "benign", "risk_score": None, "evidence": None, "scored_at": None, "disposition": None, "disposition_note": None, "disposition_at": None},
    {"account_id": "ACC_UTILITY",     "holder_name": "Utility Companies",       "account_type": "internal", "branch": "HQ", "opened_date": datetime(2000, 1, 1), "balance": 0.0, "is_suspicious": False, "typology": "benign", "risk_score": None, "evidence": None, "scored_at": None, "disposition": None, "disposition_note": None, "disposition_at": None},
]


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic AML data.")
    parser.add_argument("--accounts", type=int, default=5000, help="Number of accounts (default: 5000)")
    parser.add_argument("--seed",     type=int, default=42,   help="Random seed (default: 42)")
    parser.add_argument("--start",    type=str, default="2024-01-01", help="Simulation start date (default: 2024-01-01)")
    parser.add_argument("--end",      type=str, default="2024-12-31", help="Simulation end date (default: 2024-12-31)")
    parser.add_argument("--db",       type=str, default="data/aml.db", help="Database path (default: data/aml.db)")
    args = parser.parse_args()

    simulation_start = datetime.strptime(args.start, "%Y-%m-%d")
    simulation_end   = datetime.strptime(args.end,   "%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"AML Synthetic Data Generator")
    print(f"{'='*60}")
    print(f"  Accounts:    {args.accounts:,}")
    print(f"  Seed:        {args.seed}")
    print(f"  Period:      {args.start} to {args.end}")
    print(f"  Database:    {args.db}")
    print(f"{'='*60}\n")

    # ── Create / recreate database ────────────────────────────────────────────
    print("Setting up database...")
    os.makedirs(os.path.dirname(args.db) if os.path.dirname(args.db) else ".", exist_ok=True)

    engine = get_engine(args.db)

    # DROP and recreate all tables (fresh start)
    from backend.database.schema import Base
    Base.metadata.drop_all(engine)
    create_all_tables(engine)
    Session = get_session_factory(engine)

    print("Database tables created (fresh).\n")

    # ── Generate accounts ─────────────────────────────────────────────────────
    print("Generating accounts...")
    accounts, typology_map = generate_accounts(total_accounts=args.accounts, seed=args.seed)

    all_account_ids = [a["account_id"] for a in accounts]

    print(f"  Generated {len(accounts):,} accounts:")
    for typology, ids in typology_map.items():
        print(f"    {typology:<20}: {len(ids):>5} accounts")

    # ── Generate transactions ─────────────────────────────────────────────────
    import random
    rng = random.Random(args.seed)
    reset_transaction_counter(0)

    all_transactions = []

    print("\nGenerating typology transactions...")

    with tqdm(total=6, desc="Typologies") as pbar:
        # 1. Structuring
        txs = generate_structuring_transactions(typology_map["structuring"], simulation_start, simulation_end, rng)
        all_transactions.extend(txs)
        pbar.update(1)
        pbar.set_postfix({"structuring": len(txs)})

        # 2. Layering
        txs = generate_layering_transactions(typology_map["layering"], simulation_start, simulation_end, rng)
        all_transactions.extend(txs)
        pbar.update(1)

        # 3. Funnel
        txs = generate_funnel_transactions(typology_map["funnel"], all_account_ids, simulation_start, simulation_end, rng)
        all_transactions.extend(txs)
        pbar.update(1)

        # 4. Round-trip
        txs = generate_round_trip_transactions(typology_map["round_trip"], simulation_start, simulation_end, rng)
        all_transactions.extend(txs)
        pbar.update(1)

        # 5. Shell company
        txs = generate_shell_company_transactions(typology_map["shell_company"], simulation_start, simulation_end, rng)
        all_transactions.extend(txs)
        pbar.update(1)

        # 6. Velocity
        txs = generate_velocity_transactions(typology_map["velocity"], all_account_ids, simulation_start, simulation_end, rng)
        all_transactions.extend(txs)
        pbar.update(1)

    dirty_count = len(all_transactions)
    print(f"  Generated {dirty_count:,} suspicious transactions\n")

    print("Generating benign transactions (this takes ~30 seconds)...")
    benign_txs = generate_benign_transactions(
        account_ids=all_account_ids,
        all_account_ids=all_account_ids,
        simulation_start=simulation_start,
        simulation_end=simulation_end,
        rng=rng,
    )
    all_transactions.extend(benign_txs)
    print(f"  Generated {len(benign_txs):,} benign transactions")
    print(f"  Total: {len(all_transactions):,} transactions\n")

    # ── Save to database ──────────────────────────────────────────────────────
    print("Saving to database...")

    with Session() as session:
        # Save system accounts first
        for sys_acc in SYSTEM_ACCOUNTS:
            session.add(Account(**sys_acc))

        # Save regular accounts in batches of 500
        BATCH_SIZE = 500
        with tqdm(total=len(accounts), desc="Accounts") as pbar:
            for i in range(0, len(accounts), BATCH_SIZE):
                batch = accounts[i:i + BATCH_SIZE]
                for acc_data in batch:
                    session.add(Account(**acc_data))
                session.flush()
                pbar.update(len(batch))

        # Save transactions in batches of 1000
        with tqdm(total=len(all_transactions), desc="Transactions") as pbar:
            for i in range(0, len(all_transactions), 1000):
                batch = all_transactions[i:i + 1000]
                for tx_data in batch:
                    session.add(Transaction(**tx_data))
                session.flush()
                pbar.update(len(batch))

        session.commit()

    print(f"\n{'='*60}")
    print(f"Data generation complete!")
    print(f"  Accounts saved:     {len(accounts) + len(SYSTEM_ACCOUNTS):,}")
    print(f"  Transactions saved: {len(all_transactions):,}")
    print(f"  Dirty ratio:        {dirty_count / len(all_transactions):.1%}")
    print(f"\nNext step: python scripts/run_detection.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
