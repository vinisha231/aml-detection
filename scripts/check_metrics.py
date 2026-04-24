"""
scripts/check_metrics.py
─────────────────────────────────────────────────────────────────────────────
Script to evaluate AML detection pipeline performance metrics.

Computes:
  - AUC-ROC: Overall discriminative power (area under the ROC curve)
  - Precision@K: Of the top-K alerts, what fraction are truly suspicious?
  - Recall@K: Of all truly suspicious accounts, what fraction are in the top-K?
  - False Positive Rate by threshold

Why these metrics?
  Accuracy alone is misleading for imbalanced datasets. With 10% suspicious
  accounts, a model that labels everything "benign" achieves 90% accuracy
  but catches zero fraud.

  AUC-ROC is threshold-independent — it measures how well the model RANKS
  suspicious accounts above benign ones, regardless of where you set the cutoff.

  Precision@K and Recall@K are directly operationally relevant:
  - "If analysts review the top 50 alerts, what fraction are real?"
  - "If we review the top 100 alerts, do we catch 80% of all suspicious accounts?"

Usage:
  python -m scripts.check_metrics
  python -m scripts.check_metrics --top-k 50 100 200
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import argparse

sys.path.insert(0, '.')

from backend.database.connection import SessionLocal
from backend.database.models import Account


def compute_auc_roc(y_true: list[int], y_scores: list[float]) -> float:
    """
    Compute AUC-ROC using the trapezoidal rule.

    We implement this from scratch (without sklearn) to avoid a heavy dependency
    and to illustrate how AUC-ROC is actually computed.

    The ROC curve plots:
      X-axis: False Positive Rate (FPR) = FP / (FP + TN)
      Y-axis: True Positive Rate (TPR) = TP / (TP + FN)

    As the classification threshold decreases, more accounts are flagged.
    The curve shows the tradeoff between catching more true positives (higher TPR)
    and accepting more false positives (higher FPR).

    AUC = area under this curve. 0.5 = random, 1.0 = perfect, <0.5 = worse than random.

    Args:
        y_true:   Binary labels (1=suspicious, 0=benign).
        y_scores: Risk scores (0–100). Higher = more suspicious.

    Returns:
        AUC-ROC value between 0 and 1.
    """
    # Sort by score descending — as if lowering the threshold from 100 to 0
    pairs = sorted(zip(y_scores, y_true), reverse=True)

    n_pos = sum(y_true)           # Total positive (suspicious) accounts
    n_neg = len(y_true) - n_pos  # Total negative (benign) accounts

    if n_pos == 0 or n_neg == 0:
        return 0.5  # Undefined — return chance level

    tpr_points = [0.0]
    fpr_points = [0.0]

    tp = 0
    fp = 0

    for _, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        tpr_points.append(tp / n_pos)
        fpr_points.append(fp / n_neg)

    # Trapezoidal integration: area = sum of trapezoids under the curve
    auc = 0.0
    for i in range(1, len(fpr_points)):
        dx = fpr_points[i] - fpr_points[i - 1]
        dy = (tpr_points[i] + tpr_points[i - 1]) / 2
        auc += dx * dy

    return round(auc, 4)


def precision_at_k(y_true: list[int], y_scores: list[float], k: int) -> float:
    """
    Of the top-K accounts by score, what fraction are truly suspicious?

    Args:
        y_true:   Binary labels (1=suspicious, 0=benign).
        y_scores: Risk scores.
        k:        Number of top accounts to consider.

    Returns:
        Precision@K between 0 and 1.
    """
    k = min(k, len(y_true))
    pairs = sorted(zip(y_scores, y_true), reverse=True)
    top_k_labels = [label for _, label in pairs[:k]]
    return round(sum(top_k_labels) / k, 4) if k > 0 else 0.0


def recall_at_k(y_true: list[int], y_scores: list[float], k: int) -> float:
    """
    Of all truly suspicious accounts, what fraction appear in the top-K by score?

    Args:
        y_true:   Binary labels.
        y_scores: Risk scores.
        k:        Number of top accounts to consider.

    Returns:
        Recall@K between 0 and 1.
    """
    total_suspicious = sum(y_true)
    if total_suspicious == 0:
        return 0.0

    k = min(k, len(y_true))
    pairs = sorted(zip(y_scores, y_true), reverse=True)
    top_k_labels = [label for _, label in pairs[:k]]
    return round(sum(top_k_labels) / total_suspicious, 4)


def main():
    parser = argparse.ArgumentParser(description='Evaluate AML detection metrics')
    parser.add_argument(
        '--top-k',
        type=int,
        nargs='+',
        default=[25, 50, 100, 200],
        help='K values for Precision@K and Recall@K (default: 25 50 100 200)',
    )
    args = parser.parse_args()

    print('Loading scored accounts from database...')
    db = SessionLocal()
    try:
        accounts = db.query(Account).all()
    finally:
        db.close()

    # Build ground truth and scores
    y_true   = [1 if acc.is_suspicious else 0 for acc in accounts]
    y_scores = [float(acc.risk_score or 0) for acc in accounts]

    n_total   = len(accounts)
    n_susp    = sum(y_true)
    n_scored  = sum(1 for s in y_scores if s > 0)

    print(f'\nDataset: {n_total:,} accounts | {n_susp:,} suspicious ({n_susp/n_total:.1%})')
    print(f'Scored:  {n_scored:,} accounts with non-zero risk scores')

    if n_scored == 0:
        print('\nNo accounts have been scored yet. Run `make detect` first.')
        sys.exit(1)

    # AUC-ROC
    auc = compute_auc_roc(y_true, y_scores)
    print(f'\n{"="*50}')
    print(f'AUC-ROC:  {auc:.4f}  {"(excellent)" if auc > 0.9 else "(good)" if auc > 0.75 else "(fair)" if auc > 0.6 else "(poor)"}')
    print(f'{"="*50}')

    # Precision@K and Recall@K
    print(f'\n{"K":>6} | {"Precision@K":>12} | {"Recall@K":>10}')
    print('-' * 35)
    for k in args.top_k:
        p = precision_at_k(y_true, y_scores, k)
        r = recall_at_k(y_true, y_scores, k)
        print(f'{k:>6} | {p:>12.1%} | {r:>10.1%}')

    print()


if __name__ == '__main__':
    main()
