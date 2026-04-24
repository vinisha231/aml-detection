"""
scripts/validate_data.py
─────────────────────────────────────────────────────────────────────────────
Script to validate the generated synthetic dataset before running detection.

Why validate before detection?
  The detection pipeline assumes clean data. If the generator produced:
  - Accounts with missing typologies
  - Transactions referencing non-existent accounts
  - Negative amounts or out-of-range dates

  ...the detection results will be silently wrong (garbage in, garbage out).
  This script catches those issues early.

Usage:
  python -m scripts.validate_data
  python -m scripts.validate_data --strict  # exit 1 if any warnings

Output:
  Prints a detailed validation report. Exits 0 if passed, 1 if failed.
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import argparse
from datetime import datetime

# Add parent directory to path so imports work when run from project root
sys.path.insert(0, '.')

from backend.database.connection import SessionLocal
from backend.database.models import Account, Transaction
from backend.generator.validator import validate_generated_data


def main():
    parser = argparse.ArgumentParser(description='Validate the AML synthetic dataset')
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Exit with code 1 if any warnings are present (not just errors)',
    )
    args = parser.parse_args()

    print('Loading data from database...')
    db = SessionLocal()

    try:
        # Load all accounts and transactions from the database
        accounts     = [row.__dict__ for row in db.query(Account).all()]
        transactions = [row.__dict__ for row in db.query(Transaction).all()]
    finally:
        db.close()

    print(f'Loaded {len(accounts):,} accounts and {len(transactions):,} transactions.')

    if not accounts:
        print('ERROR: No accounts found. Run `make generate` first.')
        sys.exit(1)

    # Determine the simulation window from the actual data
    dates = [tx['transaction_date'] for tx in transactions if tx.get('transaction_date')]
    if dates:
        sim_start = min(dates)
        sim_end   = max(dates)
    else:
        # Default window if no transactions
        sim_start = datetime(2023, 1, 1)
        sim_end   = datetime(2024, 1, 1)

    print(f'Simulation window: {sim_start.date()} → {sim_end.date()}')
    print()

    # Run the validator
    result = validate_generated_data(accounts, transactions, sim_start, sim_end)

    # Print the full validation report
    print(result)

    # Determine exit code
    if not result.passed:
        print('\nValidation FAILED. Fix the data generator and re-run `make generate`.')
        sys.exit(1)

    if args.strict and result.warnings:
        print(f'\nStrict mode: {len(result.warnings)} warnings found. Exiting with code 1.')
        sys.exit(1)

    print('\nValidation PASSED.')
    sys.exit(0)


if __name__ == '__main__':
    main()
