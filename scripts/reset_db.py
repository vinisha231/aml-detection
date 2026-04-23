"""
scripts/reset_db.py
─────────────────────────────────────────────────────────────────────────────
Utility script to reset the database to a clean state.

When would you use this?
  - After changing the schema in a breaking way (easier than writing a migration)
  - Starting a fresh experiment with different generation parameters
  - Clearing development data before a demo

⚠️ WARNING: This deletes ALL data. Use with caution.

Usage:
  python scripts/reset_db.py                    # interactive confirmation
  python scripts/reset_db.py --confirm          # skip confirmation (for CI)
  python scripts/reset_db.py --db data/test.db  # target a specific database

What it does:
  1. Drops all tables (loses all data)
  2. Recreates all tables (fresh schema)
  3. Seeds system accounts
  4. Reports what was reset
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import argparse
from pathlib import Path

# Add project root to Python path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.schema import get_engine, create_all_tables, get_session_factory, Base
from backend.database.seed import seed_all


def reset_database(db_path: str, confirm: bool = False) -> None:
    """
    Drop and recreate all tables, then seed system data.

    Args:
        db_path: Path to the SQLite database file.
        confirm: If True, skip the interactive confirmation prompt.
    """
    # ── Safety confirmation ────────────────────────────────────────────────────
    if not confirm:
        print(f"\n⚠️  WARNING: This will DELETE ALL DATA in {db_path}")
        print("    All accounts, transactions, signals, and dispositions will be lost.")
        answer = input("\n    Type 'RESET' to confirm: ").strip()
        if answer != 'RESET':
            print("    Aborted.")
            return

    # ── Drop and recreate tables ───────────────────────────────────────────────
    print(f"\n  Resetting database: {db_path}")
    engine = get_engine(db_path)

    print("  Dropping all tables…")
    Base.metadata.drop_all(engine)

    print("  Recreating all tables…")
    create_all_tables(engine)

    # ── Seed system accounts ───────────────────────────────────────────────────
    print("  Seeding system accounts…")
    factory = get_session_factory(engine)
    session = factory()
    try:
        result = seed_all(session)
        print(f"  Seeded: {result}")
    finally:
        session.close()

    print(f"\n  ✓ Database reset complete: {db_path}")
    print("    Next step: python scripts/generate_data.py")


def main():
    parser = argparse.ArgumentParser(
        description='Reset the AML database to a clean state.'
    )
    parser.add_argument(
        '--db',
        default='data/aml.db',
        help='Path to the SQLite database (default: data/aml.db)',
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt (for automated/CI use)',
    )

    args = parser.parse_args()
    reset_database(args.db, args.confirm)


if __name__ == '__main__':
    main()
