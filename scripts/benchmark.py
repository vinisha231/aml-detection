"""
scripts/benchmark.py
─────────────────────────────────────────────────────────────────────────────
Performance benchmark for the detection pipeline.

Measures:
  - Time to load transactions from DB
  - Time to run all rules (per account, total)
  - Time to build the graph
  - Time to run graph signals
  - Time to score all accounts
  - Memory usage throughout

Why benchmarking matters:
  In a real AML system, the detection pipeline runs nightly on millions
  of transactions. If it takes too long, the queue isn't ready when
  analysts arrive in the morning. Banks have hard SLA requirements like
  "the queue must be populated by 7am."

  Benchmarking also reveals WHERE time is spent:
    - If graph building dominates → optimise edge aggregation
    - If cycle detection dominates → use simple_cycles() with limits
    - If scoring dominates → vectorise with numpy

Usage:
  python scripts/benchmark.py
  python scripts/benchmark.py --accounts 1000  # smaller subset
  python scripts/benchmark.py --db data/aml.db
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import time
import argparse
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def timed(label: str):
    """Context manager that prints elapsed time for a code block."""
    class Timer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args):
            elapsed = (time.perf_counter() - self.start) * 1000
            print(f"  {label:40s} {elapsed:8.1f} ms")

    return Timer()


def run_benchmark(db_path: str, account_limit: int) -> None:
    print(f"\n{'='*60}")
    print(f"  AML Detection Pipeline Benchmark")
    print(f"  Database: {db_path}")
    print(f"  Account limit: {account_limit}")
    print(f"{'='*60}\n")

    from backend.database.schema import get_engine, get_session_factory
    from backend.database.schema import Account, Transaction

    engine  = get_engine(db_path)
    factory = get_session_factory(engine)
    session = factory()

    # Start memory tracking
    tracemalloc.start()

    try:
        # ── Step 1: Load accounts ─────────────────────────────────────────────
        with timed("Load accounts from DB"):
            accounts = (
                session.query(Account.account_id)
                .limit(account_limit)
                .all()
            )
            account_ids = [a.account_id for a in accounts]

        print(f"  → {len(account_ids)} accounts loaded\n")

        # ── Step 2: Load transactions ─────────────────────────────────────────
        with timed("Load transactions from DB"):
            txs = (
                session.query(Transaction)
                .filter(Transaction.sender_account_id.in_(account_ids) |
                        Transaction.receiver_account_id.in_(account_ids))
                .all()
            )
            tx_count = len(txs)

        print(f"  → {tx_count:,} transactions loaded\n")

        # ── Step 3: Group transactions by account ─────────────────────────────
        with timed("Group transactions by account"):
            from collections import defaultdict
            tx_by_account = defaultdict(list)
            for tx in txs:
                tx_dict = {
                    'transaction_id':      tx.transaction_id,
                    'sender_account_id':   tx.sender_account_id,
                    'receiver_account_id': tx.receiver_account_id,
                    'amount':              tx.amount,
                    'transaction_type':    tx.transaction_type,
                    'transaction_date':    tx.transaction_date,
                    'is_suspicious':       tx.is_suspicious,
                }
                tx_by_account[tx.sender_account_id].append(tx_dict)
                tx_by_account[tx.receiver_account_id].append(tx_dict)

        # ── Step 4: Run rules (sample 100 accounts for speed) ─────────────────
        sample_ids = account_ids[:100]
        with timed("Run all rules (100 accounts)"):
            from backend.detection.ensemble import run_all_rules
            all_rule_signals = []
            for acc_id in sample_ids:
                sigs = run_all_rules(acc_id, tx_by_account.get(acc_id, []))
                all_rule_signals.extend(sigs)

        signals_per_account = len(all_rule_signals) / max(len(sample_ids), 1)
        print(f"  → {len(all_rule_signals)} signals from 100 accounts "
              f"({signals_per_account:.1f} avg per account)\n")

        # ── Step 5: Build transaction graph ───────────────────────────────────
        with timed("Build transaction graph"):
            from backend.detection.graph.builder import build_transaction_graph
            G = build_transaction_graph(txs_as_dicts=[tx_dict for tx_dict in
                                                      [{'transaction_id': t.transaction_id,
                                                        'sender_account_id': t.sender_account_id,
                                                        'receiver_account_id': t.receiver_account_id,
                                                        'amount': t.amount,
                                                        'transaction_type': t.transaction_type,
                                                        'transaction_date': t.transaction_date,
                                                        'is_suspicious': t.is_suspicious}
                                                       for t in txs]])

        print(f"  → Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

        # ── Step 6: Run graph signals ─────────────────────────────────────────
        with timed("Run graph signals (PageRank)"):
            from backend.detection.graph.pagerank_signal import compute_pagerank_signals
            pr_sigs = compute_pagerank_signals(G)

        with timed("Run graph signals (Cycle detection)"):
            from backend.detection.graph.cycle_signal import compute_cycle_signals
            cycle_sigs = compute_cycle_signals(G)

        with timed("Run graph signals (Community)"):
            from backend.detection.graph.community_signal import compute_community_signals
            comm_sigs = compute_community_signals(G)

        print()

        # ── Memory report ─────────────────────────────────────────────────────
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"  {'Memory (current)':40s} {current / 1024 / 1024:8.1f} MB")
        print(f"  {'Memory (peak)':40s} {peak / 1024 / 1024:8.1f} MB")

    finally:
        session.close()

    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Benchmark the AML detection pipeline.')
    parser.add_argument('--db',       default='data/aml.db', help='Database path')
    parser.add_argument('--accounts', type=int, default=500,  help='Number of accounts to include')
    args = parser.parse_args()

    run_benchmark(args.db, args.accounts)


if __name__ == '__main__':
    main()
