"""
backend/pipeline.py
─────────────────────────────────────────────────────────────────────────────
The master detection pipeline.

This is the "glue" script that connects all the pieces:
  1. Load transactions from the database
  2. Run all 5 rules-based detection rules
  3. Build the transaction graph
  4. Run all 4 graph-based signals
  5. Combine signals per account
  6. Score every account (0-100)
  7. Save scores back to the database
  8. Print a summary report

Run this script daily (or on-demand) to refresh all risk scores.

Usage:
    python pipeline.py                    # score all accounts
    python pipeline.py --top 20           # print top 20 risky accounts
    python pipeline.py --account ACC_000001  # score one account only

The pipeline is designed to be IDEMPOTENT:
  Running it twice gives the same result (old scores are overwritten).
─────────────────────────────────────────────────────────────────────────────
"""

import argparse
import sys
import os
from datetime import datetime
from collections import defaultdict
from typing import List, Dict

# Add the parent directory to Python's path so we can import our modules
# This is needed because we run this file directly as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.schema import (
    get_engine,
    create_all_tables,
    get_session_factory,
)
from backend.database.queries import (
    update_account_score,
    delete_account_signals,
    save_signal,
    get_risk_queue,
)
from backend.database.schema import Signal, Transaction, Account

# Rules-based detection
from backend.detection.rules import (
    check_structuring,
    check_velocity,
    check_funnel,
    check_dormant_wakeup,
    check_round_numbers,
)

# Graph-based detection
from backend.detection.graph import (
    build_transaction_graph,
    compute_pagerank_signals,
    compute_community_signals,
    compute_cycle_signals,
    compute_chain_signals,
)

# Scoring
from backend.detection.scoring import score_all_accounts, get_risk_tier


def run_pipeline(
    db_path: str = "data/aml.db",
    lookback_days: int = 90,
    verbose: bool = True
) -> Dict[str, float]:
    """
    Run the complete AML detection pipeline.

    This function:
      1. Loads all transactions from the database
      2. Runs rules-based detection on every account
      3. Runs graph-based detection on the full transaction graph
      4. Scores every account
      5. Saves results to the database

    Args:
        db_path:       Path to the SQLite database file
        lookback_days: How many days of history to analyze
        verbose:       Whether to print progress messages

    Returns:
        Dict mapping account_id → final risk score
    """

    def log(msg):
        if verbose:
            print(f"[Pipeline {datetime.now().strftime('%H:%M:%S')}] {msg}")

    log("Starting AML detection pipeline...")

    # ── Step 1: Connect to database ───────────────────────────────────────────
    engine = get_engine(db_path)
    Session = get_session_factory(engine)

    with Session() as session:

        # ── Step 2: Load all transactions from database ───────────────────────
        log("Loading transactions from database...")

        all_transactions_raw = session.query(Transaction).all()
        all_accounts_raw     = session.query(Account).all()

        # Convert SQLAlchemy objects to plain dicts
        # (easier to pass around and don't require an open session)
        all_transactions = [
            {
                "transaction_id":      tx.transaction_id,
                "sender_account_id":   tx.sender_account_id,
                "receiver_account_id": tx.receiver_account_id,
                "amount":              tx.amount,
                "transaction_type":    tx.transaction_type,
                "description":         tx.description,
                "transaction_date":    tx.transaction_date,
                "is_suspicious":       tx.is_suspicious,
                "typology":            tx.typology,
            }
            for tx in all_transactions_raw
        ]

        all_account_ids = [acc.account_id for acc in all_accounts_raw]

        log(f"Loaded {len(all_transactions):,} transactions for {len(all_account_ids):,} accounts.")

        # ── Step 3: Group transactions by account ──────────────────────────────
        # For rules-based detection, we need fast per-account lookups.
        # Instead of querying the DB once per account (would be 5,000 queries!),
        # we load everything into memory and group it here.
        log("Grouping transactions by account...")

        transactions_by_account: Dict[str, List[dict]] = defaultdict(list)

        for tx in all_transactions:
            # Include transaction in sender's list AND receiver's list
            # (both accounts are "involved" in the transaction)
            transactions_by_account[tx["sender_account_id"]].append(tx)
            transactions_by_account[tx["receiver_account_id"]].append(tx)

        # ── Step 4: Run rules-based detection ─────────────────────────────────
        log("Running rules-based detection...")

        # all_signals maps account_id → list of RuleSignal objects
        all_signals: Dict[str, list] = defaultdict(list)

        rule_fire_counts = {
            "structuring_rule":  0,
            "velocity_rule":     0,
            "funnel_rule":       0,
            "dormant_rule":      0,
            "round_number_rule": 0,
        }

        for i, account_id in enumerate(all_account_ids):
            if verbose and i % 500 == 0:
                log(f"  Rules: {i}/{len(all_account_ids)} accounts processed...")

            account_txs = transactions_by_account.get(account_id, [])

            # Run each rule and collect signals
            for rule_func, rule_name in [
                (check_structuring,   "structuring_rule"),
                (check_velocity,      "velocity_rule"),
                (check_funnel,        "funnel_rule"),
                (check_dormant_wakeup, "dormant_rule"),
                (check_round_numbers, "round_number_rule"),
            ]:
                try:
                    signals = rule_func(account_id, account_txs)
                    if signals:
                        all_signals[account_id].extend(signals)
                        rule_fire_counts[rule_name] += len(signals)
                except Exception as e:
                    # Don't let one bad account crash the whole pipeline
                    if verbose:
                        print(f"    Warning: rule {rule_name} failed on {account_id}: {e}")

        log(f"Rules fired: {dict(rule_fire_counts)}")

        # ── Step 5: Build transaction graph ────────────────────────────────────
        log("Building transaction graph...")

        G = build_transaction_graph(
            all_transactions,
            lookback_days=lookback_days,
        )

        # ── Step 6: Run graph-based detection ─────────────────────────────────
        log("Running graph-based detection (PageRank, community, cycles, chains)...")

        graph_signal_functions = [
            ("pagerank",   compute_pagerank_signals,  lambda: [G]),
            ("community",  compute_community_signals, lambda: [G]),
            ("cycles",     compute_cycle_signals,     lambda: [G]),
            ("chains",     compute_chain_signals,     lambda: [G]),
        ]

        graph_fire_counts = {}

        for signal_name, signal_func, args_fn in graph_signal_functions:
            try:
                log(f"  Running graph signal: {signal_name}...")
                graph_signals = signal_func(*args_fn())
                graph_fire_counts[signal_name] = len(graph_signals)

                # Add graph signals to the all_signals dict
                for sig in graph_signals:
                    all_signals[sig.account_id].append(sig)

            except Exception as e:
                log(f"  Warning: graph signal {signal_name} failed: {e}")
                import traceback
                traceback.print_exc()

        log(f"Graph signals fired: {graph_fire_counts}")

        # ── Step 7: Score all accounts ─────────────────────────────────────────
        log("Computing final risk scores...")

        scoring_results = score_all_accounts(all_signals)

        log(f"Scored {len(scoring_results):,} accounts with at least one signal.")

        # ── Step 8: Save results to database ──────────────────────────────────
        log("Saving scores to database...")

        saved_count = 0

        for account_id, result in scoring_results.items():

            # Clear old signals for this account (prevent duplicates on re-runs)
            delete_account_signals(session, account_id)

            # Save the final score and evidence to the account record
            update_account_score(
                session,
                account_id,
                result.risk_score,
                result.evidence,
            )

            # Save individual signals for FPR tracking and audit trail
            for signal in all_signals[account_id]:
                db_signal = Signal(
                    account_id=account_id,
                    signal_type=signal.signal_type,
                    score=signal.score,
                    weight=signal.weight,
                    evidence=signal.evidence,
                    confidence=signal.confidence,
                    created_at=datetime.utcnow(),
                )
                save_signal(session, db_signal)

            saved_count += 1

        # Commit all changes in one transaction (much faster than per-account commits)
        session.commit()
        log(f"Saved {saved_count:,} account scores to database.")

        # ── Step 9: Return final scores ────────────────────────────────────────
        return {acc_id: result.risk_score for acc_id, result in scoring_results.items()}


def print_top_accounts(session, limit: int = 20) -> None:
    """
    Print the top-N highest-risk accounts to the console.

    This is the CLI output — a quick sanity check that detection is working.

    Args:
        session: Active database session
        limit:   How many accounts to show
    """
    accounts = get_risk_queue(session, limit=limit, disposition_filter="all")

    if not accounts:
        print("No scored accounts found. Run the pipeline first.")
        return

    print(f"\n{'='*70}")
    print(f"{'TOP AML RISK QUEUE':^70}")
    print(f"{'='*70}")
    print(f"{'Rank':<5} {'Account ID':<15} {'Score':>7} {'Tier':<10} {'Typology':<15} {'Name':<20}")
    print(f"{'-'*70}")

    for rank, acc in enumerate(accounts, 1):
        tier = get_risk_tier(acc.risk_score or 0)
        print(
            f"{rank:<5} {acc.account_id:<15} "
            f"{acc.risk_score or 0:>6.1f}/100 "
            f"{tier:<10} "
            f"{acc.typology:<15} "
            f"{acc.holder_name[:18]:<20}"
        )

    print(f"{'='*70}\n")


# ─── Entry point when run as a script ────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AML Detection Pipeline — scores all accounts for money laundering risk."
    )
    parser.add_argument(
        "--db", default="data/aml.db",
        help="Path to SQLite database (default: data/aml.db)"
    )
    parser.add_argument(
        "--top", type=int, default=20,
        help="Print top N risky accounts after running (default: 20)"
    )
    parser.add_argument(
        "--lookback", type=int, default=90,
        help="Days of transaction history to analyze (default: 90)"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress progress messages"
    )
    args = parser.parse_args()

    # Run the pipeline
    scores = run_pipeline(
        db_path=args.db,
        lookback_days=args.lookback,
        verbose=not args.quiet,
    )

    # Print the top accounts
    if args.top > 0:
        engine = get_engine(args.db)
        Session = get_session_factory(engine)
        with Session() as session:
            print_top_accounts(session, limit=args.top)

    print(f"Pipeline complete. {len(scores):,} accounts scored.")
