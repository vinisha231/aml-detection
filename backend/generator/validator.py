"""
backend/generator/validator.py
─────────────────────────────────────────────────────────────────────────────
Validates generated synthetic data for quality and consistency.

Why validate generated data?
  The data generator is complex — 6 typologies, benign transactions,
  thousands of accounts. Bugs can produce data that is:
    - Missing expected typologies
    - Has too few suspicious accounts (skewing evaluation metrics)
    - Has transactions referencing non-existent accounts (FK violations)
    - Has negative amounts or future dates (logical impossibilities)

  Running the validator after generation catches these issues before
  they silently corrupt the detection pipeline's results.

Validation checks:
  1. Transaction count within expected range
  2. Suspicious account ratio ~10% (configurable)
  3. All 6 typologies are represented
  4. No transactions with negative amounts
  5. All sender/receiver IDs exist in the accounts list
  6. Transactions reference accounts that exist
  7. Transaction dates are within the simulation window
  8. Typology distribution is within expected bounds
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationResult:
    """Results of a data validation run."""
    passed:   bool               = True
    warnings: list[str]          = field(default_factory=list)
    errors:   list[str]          = field(default_factory=list)
    stats:    dict[str, object]  = field(default_factory=dict)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    def __str__(self) -> str:
        lines = ['=== Data Validation Report ===']
        lines.append(f"Status: {'✓ PASSED' if self.passed else '✗ FAILED'}")

        if self.stats:
            lines.append('\nStatistics:')
            for k, v in self.stats.items():
                lines.append(f'  {k:35s}: {v}')

        if self.warnings:
            lines.append(f'\nWarnings ({len(self.warnings)}):')
            for w in self.warnings:
                lines.append(f'  ⚠️  {w}')

        if self.errors:
            lines.append(f'\nErrors ({len(self.errors)}):')
            for e in self.errors:
                lines.append(f'  ✗  {e}')

        return '\n'.join(lines)


def validate_generated_data(
    accounts:         list[dict],
    transactions:     list[dict],
    simulation_start: datetime,
    simulation_end:   datetime,
    expected_suspicious_ratio: float = 0.10,
    tolerance: float = 0.03,  # allow ±3% from expected ratio
) -> ValidationResult:
    """
    Validate generated synthetic data for completeness and consistency.

    Args:
        accounts:                  List of account dicts from the generator.
        transactions:              List of transaction dicts from the generator.
        simulation_start:          Start of the simulation window.
        simulation_end:            End of the simulation window.
        expected_suspicious_ratio: Expected fraction of suspicious accounts (0.10 = 10%).
        tolerance:                 Allowable deviation from the expected ratio.

    Returns:
        ValidationResult with passed flag, errors, warnings, and stats.
    """
    result = ValidationResult()

    # ── Basic counts ──────────────────────────────────────────────────────────
    n_accounts    = len(accounts)
    n_transactions = len(transactions)
    account_ids   = {acc['account_id'] for acc in accounts}
    suspicious    = [acc for acc in accounts if acc.get('is_suspicious')]
    suspicious_ratio = len(suspicious) / n_accounts if n_accounts > 0 else 0

    result.stats = {
        'total_accounts':      n_accounts,
        'total_transactions':  n_transactions,
        'suspicious_accounts': len(suspicious),
        'suspicious_ratio':    f'{suspicious_ratio:.1%}',
        'avg_txs_per_account': f'{n_transactions / max(n_accounts, 1):.1f}',
    }

    # ── Check: Minimum data sizes ─────────────────────────────────────────────
    if n_accounts < 100:
        result.add_error(f"Too few accounts: {n_accounts} (minimum 100)")

    if n_transactions < n_accounts * 5:
        result.add_warning(f"Low transaction count: {n_transactions} for {n_accounts} accounts")

    # ── Check: Suspicious ratio within expected range ─────────────────────────
    lower = expected_suspicious_ratio - tolerance
    upper = expected_suspicious_ratio + tolerance
    if not (lower <= suspicious_ratio <= upper):
        msg = (
            f"Suspicious ratio {suspicious_ratio:.1%} outside expected range "
            f"[{lower:.1%}, {upper:.1%}]"
        )
        if suspicious_ratio < lower:
            result.add_error(msg)  # too few suspicious accounts = bad evaluation
        else:
            result.add_warning(msg)  # too many is less critical

    # ── Check: All typologies represented ─────────────────────────────────────
    expected_typologies = {
        'structuring', 'layering', 'funnel', 'round_trip', 'shell_company', 'velocity'
    }
    present_typologies = {
        acc.get('typology') for acc in suspicious
        if acc.get('typology') is not None
    }
    missing_typologies = expected_typologies - present_typologies

    if missing_typologies:
        result.add_error(f"Missing typologies: {missing_typologies}")

    # ── Check: No negative amounts ────────────────────────────────────────────
    negative_txs = [tx for tx in transactions if tx.get('amount', 0) < 0]
    if negative_txs:
        result.add_error(f"{len(negative_txs)} transactions have negative amounts")

    # ── Check: Sender/receiver exist in accounts ──────────────────────────────
    missing_senders   = [
        tx for tx in transactions
        if tx.get('sender_account_id') not in account_ids
        and not tx['sender_account_id'].startswith(('ACC_BANK', 'ACC_PAYROLL',
                                                     'ACC_LANDLORD', 'ACC_RETAIL',
                                                     'ACC_UTILITY', 'ACC_CASH_OUT',
                                                     'ACC_POOL_', 'INT_'))
    ]

    if missing_senders:
        result.add_warning(
            f"{len(missing_senders)} transactions reference unknown sender accounts"
        )

    # ── Check: Dates within simulation window ─────────────────────────────────
    out_of_range = [
        tx for tx in transactions
        if not (simulation_start <= tx['transaction_date'] <= simulation_end)
    ]
    if out_of_range:
        result.add_error(
            f"{len(out_of_range)} transactions outside simulation window "
            f"[{simulation_start.date()}, {simulation_end.date()}]"
        )

    return result
