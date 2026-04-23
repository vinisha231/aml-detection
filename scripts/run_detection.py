"""
scripts/run_detection.py
─────────────────────────────────────────────────────────────────────────────
Convenience script to run the full detection pipeline.

This is just a thin wrapper around backend/pipeline.py.
It exists so you can run: python scripts/run_detection.py
without needing to remember the full module path.

Usage:
    python scripts/run_detection.py
    python scripts/run_detection.py --top 50
    python scripts/run_detection.py --lookback 30   # only analyze last 30 days
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import argparse

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline import run_pipeline, print_top_accounts
from backend.database.schema import get_engine, get_session_factory


def main():
    parser = argparse.ArgumentParser(description="Run AML detection pipeline.")
    parser.add_argument("--db",       default="data/aml.db", help="Database path")
    parser.add_argument("--top",      type=int, default=20,  help="Show top N accounts after scoring")
    parser.add_argument("--lookback", type=int, default=90,  help="Days of history to analyze")
    parser.add_argument("--quiet",    action="store_true",   help="Suppress progress output")
    args = parser.parse_args()

    print(f"\nRunning detection pipeline on {args.db}...\n")

    scores = run_pipeline(
        db_path=args.db,
        lookback_days=args.lookback,
        verbose=not args.quiet,
    )

    if args.top > 0:
        engine = get_engine(args.db)
        Session = get_session_factory(engine)
        with Session() as session:
            print_top_accounts(session, limit=args.top)

    print(f"\nDone. {len(scores):,} accounts scored.\n")


if __name__ == "__main__":
    main()
