"""
scripts/export_ground_truth.py
─────────────────────────────────────────────────────────────────────────────
Export ground truth labels for model evaluation.

What is "ground truth"?
  During data generation, we KNOW which accounts were generated as suspicious
  (the `is_suspicious` flag in the Account table). This is our ground truth —
  the correct answers.

  The detection pipeline's job is to REDISCOVER these suspicious accounts
  by looking only at transaction patterns, without using `is_suspicious`.

  By comparing the model's risk scores against ground truth labels, we can
  compute evaluation metrics:
    - Precision: of accounts the model flagged, what % are truly suspicious?
    - Recall: of all truly suspicious accounts, what % did the model catch?
    - AUC-ROC: how well does the score separate suspicious from benign?

Output:
  Creates a CSV file: data/ground_truth.csv

  Columns:
    account_id, is_suspicious (1/0), typology, risk_score, risk_tier

  This CSV can then be used with scripts/evaluate.py to compute all metrics.

Usage:
  python scripts/export_ground_truth.py
  python scripts/export_ground_truth.py --db data/aml.db --out data/ground_truth.csv
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import csv
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database.schema import get_engine, get_session_factory, Account
from backend.detection.scoring import get_risk_tier


def export_ground_truth(db_path: str, output_path: str) -> None:
    """
    Export all accounts with their ground truth labels and current scores.

    Args:
        db_path:     Path to the SQLite database.
        output_path: Where to write the output CSV.
    """
    engine  = get_engine(db_path)
    factory = get_session_factory(engine)
    session = factory()

    try:
        accounts = (
            session.query(Account)
            .order_by(Account.risk_score.desc().nullslast())
            .all()
        )

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path_obj, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'account_id', 'is_suspicious', 'typology',
                'risk_score', 'risk_tier', 'disposition',
            ])

            for acc in accounts:
                tier = get_risk_tier(acc.risk_score) if acc.risk_score else 'unscored'
                writer.writerow([
                    acc.account_id,
                    1 if acc.is_suspicious else 0,
                    acc.typology or '',
                    f'{acc.risk_score:.2f}' if acc.risk_score else '',
                    tier,
                    acc.disposition or '',
                ])

        # Summary statistics
        total       = len(accounts)
        suspicious  = sum(1 for a in accounts if a.is_suspicious)
        scored      = sum(1 for a in accounts if a.risk_score is not None)
        high_risk   = sum(1 for a in accounts if a.risk_score and a.risk_score >= 70)

        print(f"\n  Ground truth export: {output_path}")
        print(f"  Total accounts:      {total:,}")
        print(f"  Suspicious (true):   {suspicious:,} ({suspicious/total*100:.1f}%)")
        print(f"  Scored by pipeline:  {scored:,} ({scored/total*100:.1f}%)")
        print(f"  High risk (score≥70):{high_risk:,}")

        # Quick precision estimate
        if high_risk > 0:
            true_in_high_risk = sum(
                1 for a in accounts
                if a.is_suspicious and a.risk_score and a.risk_score >= 70
            )
            est_precision = true_in_high_risk / high_risk
            print(f"  Est. precision@70:   {est_precision:.1%}")

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description='Export ground truth labels for evaluation.')
    parser.add_argument('--db',  default='data/aml.db',          help='Database path')
    parser.add_argument('--out', default='data/ground_truth.csv', help='Output CSV path')
    args = parser.parse_args()

    export_ground_truth(args.db, args.out)


if __name__ == '__main__':
    main()
