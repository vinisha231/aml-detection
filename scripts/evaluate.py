"""
scripts/evaluate.py
─────────────────────────────────────────────────────────────────────────────
Evaluates detection performance against ground truth.

Because WE generated the data, WE know which accounts are actually dirty.
This lets us calculate real precision and recall — metrics that show
whether our detection system actually works.

Metrics computed:
  1. Precision@20:  Of the top-20 scored accounts, what fraction are truly dirty?
  2. Precision@50:  Of the top-50, what fraction are dirty?
  3. Recall@100:    Of all dirty accounts, what fraction appear in the top-100?
  4. AUC-ROC:       Overall discrimination ability (0.5 = random, 1.0 = perfect)
  5. Per-typology recall: Which typologies are we best at detecting?

Run after the detection pipeline:
    python scripts/run_detection.py
    python scripts/evaluate.py

Interpreting results:
  Precision@20 > 0.80 = good (80%+ of top-20 are genuinely suspicious)
  Recall@100 > 0.50   = good (catching half the dirty accounts in top-100)
  AUC > 0.85          = very good overall discrimination
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score
from collections import defaultdict

from backend.database.schema import get_engine, get_session_factory, Account


def compute_precision_at_k(ranked_account_ids: list, true_positives: set, k: int) -> float:
    """
    Compute Precision@K: of the top-K accounts, what fraction are truly suspicious?

    Args:
        ranked_account_ids: Accounts sorted by risk score descending
        true_positives:     Set of account IDs we know are dirty (ground truth)
        k:                  Cutoff (look at the top-K accounts)

    Returns:
        Float between 0 and 1.

    Example:
        If top-20 has 16 dirty accounts → Precision@20 = 0.80
    """
    top_k = ranked_account_ids[:k]
    hits  = sum(1 for acc_id in top_k if acc_id in true_positives)
    return hits / k if k > 0 else 0.0


def compute_recall_at_k(ranked_account_ids: list, true_positives: set, k: int) -> float:
    """
    Compute Recall@K: of all dirty accounts, what fraction appear in top-K?

    Args:
        ranked_account_ids: Accounts sorted by risk score descending
        true_positives:     Set of all truly dirty account IDs
        k:                  Cutoff

    Returns:
        Float between 0 and 1.

    Example:
        If there are 500 dirty accounts and 200 appear in top-100 → Recall@100 = 0.40
    """
    top_k = set(ranked_account_ids[:k])
    hits  = sum(1 for acc_id in true_positives if acc_id in top_k)
    return hits / len(true_positives) if true_positives else 0.0


def main():
    parser = argparse.ArgumentParser(description="Evaluate AML detection performance.")
    parser.add_argument("--db", default="data/aml.db", help="Database path")
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(f"{'AML DETECTION EVALUATION':^65}")
    print(f"{'='*65}\n")

    # ── Load all accounts with scores from database ────────────────────────────
    engine  = get_engine(args.db)
    Session = get_session_factory(engine)

    with Session() as session:
        all_accounts = session.query(Account).filter(
            Account.risk_score.isnot(None),
            ~Account.account_id.like("ACC_%BANK%"),
            ~Account.account_id.like("ACC_%PAYROLL%"),
            ~Account.account_id.like("ACC_%LANDLORD%"),
            ~Account.account_id.like("ACC_%RETAIL%"),
            ~Account.account_id.like("ACC_%UTILITY%"),
        ).all()

    print(f"Loaded {len(all_accounts):,} scored accounts from database.\n")

    if not all_accounts:
        print("ERROR: No scored accounts found. Run run_detection.py first.")
        return

    # ── Build arrays for metric computation ───────────────────────────────────
    # Ground truth: True = dirty, False = benign
    y_true = np.array([1 if acc.is_suspicious else 0 for acc in all_accounts])

    # Predicted scores (0-100, normalized to 0-1 for sklearn)
    y_score = np.array([(acc.risk_score or 0.0) / 100.0 for acc in all_accounts])

    # Sort accounts by risk score descending (highest risk first)
    sorted_accounts = sorted(all_accounts, key=lambda a: a.risk_score or 0.0, reverse=True)
    ranked_ids      = [acc.account_id for acc in sorted_accounts]

    # Set of truly dirty account IDs
    true_positives = {acc.account_id for acc in all_accounts if acc.is_suspicious}
    total_dirty    = len(true_positives)
    total_accounts = len(all_accounts)

    print(f"Ground truth:")
    print(f"  Total accounts:  {total_accounts:,}")
    print(f"  Dirty accounts:  {total_dirty:,} ({total_dirty/total_accounts:.1%})")
    print(f"  Benign accounts: {total_accounts - total_dirty:,}\n")

    # ── Precision @ K ─────────────────────────────────────────────────────────
    print("Precision@K (what fraction of top-K are truly suspicious?):")
    for k in [10, 20, 50, 100, 200]:
        p = compute_precision_at_k(ranked_ids, true_positives, k)
        bar = "█" * int(p * 20)
        print(f"  P@{k:<4}: {p:.3f}  {bar}")

    print()

    # ── Recall @ K ────────────────────────────────────────────────────────────
    print("Recall@K (what fraction of dirty accounts appear in top-K?):")
    for k in [50, 100, 200, 500]:
        r = compute_recall_at_k(ranked_ids, true_positives, k)
        bar = "█" * int(r * 20)
        print(f"  R@{k:<4}: {r:.3f}  {bar}")

    print()

    # ── AUC-ROC ───────────────────────────────────────────────────────────────
    if len(set(y_true)) > 1:  # need both classes present
        auc_roc = roc_auc_score(y_true, y_score)
        auc_pr  = average_precision_score(y_true, y_score)
        print(f"AUC-ROC:          {auc_roc:.4f}  (0.5=random, 1.0=perfect)")
        print(f"AUC-PR (Average Precision): {auc_pr:.4f}\n")

    # ── Per-typology recall ────────────────────────────────────────────────────
    print("Per-typology recall (are we catching each pattern?):")
    typologies    = set(acc.typology for acc in all_accounts if acc.is_suspicious)
    top_100_set   = set(ranked_ids[:100])
    top_200_set   = set(ranked_ids[:200])

    for typology in sorted(typologies):
        typology_accounts = {acc.account_id for acc in all_accounts if acc.typology == typology}
        count = len(typology_accounts)
        if count == 0:
            continue

        # What fraction of this typology's accounts appear in the top-100 and top-200?
        r100 = len(typology_accounts & top_100_set) / count
        r200 = len(typology_accounts & top_200_set) / count

        # Average risk score for this typology
        avg_score = np.mean([
            acc.risk_score for acc in all_accounts
            if acc.typology == typology and acc.risk_score is not None
        ])

        print(f"  {typology:<20}: {count:>3} accounts | "
              f"avg score: {avg_score:>5.1f} | "
              f"R@100: {r100:.2f} | R@200: {r200:.2f}")

    # ── Score distribution by class ────────────────────────────────────────────
    print("\nScore distribution:")
    dirty_scores  = [acc.risk_score for acc in all_accounts if acc.is_suspicious and acc.risk_score]
    benign_scores = [acc.risk_score for acc in all_accounts if not acc.is_suspicious and acc.risk_score]

    if dirty_scores:
        print(f"  Dirty  — mean: {np.mean(dirty_scores):.1f}, "
              f"median: {np.median(dirty_scores):.1f}, "
              f"max: {np.max(dirty_scores):.1f}")
    if benign_scores:
        print(f"  Benign — mean: {np.mean(benign_scores):.1f}, "
              f"median: {np.median(benign_scores):.1f}, "
              f"max: {np.max(benign_scores):.1f}")

    print(f"\n{'='*65}")
    print("Evaluation complete.")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
