"""
backend/detection/rules/account_age_rule.py
─────────────────────────────────────────────────────────────────────────────
Detection rule for suspicious patterns related to account age and activity timing.

Why account age matters:
  Launderers often create new accounts specifically for money laundering
  and abandon them quickly. This creates distinctive age-based patterns:

  1. NEW ACCOUNT SYNDROME: Account opened < 30 days ago but already doing
     large wire transfers or cash deposits. Legitimate new accounts typically
     start with small transactions.

  2. RAPID CYCLING: Account opened, used intensively for 2–8 weeks,
     then completely dormant. The transaction density is very high
     relative to the account lifetime.

  3. ANNIVERSARY PATTERN: Some shell companies reactivate exactly once
     per year around their incorporation date (for annual financial
     obligations like regulatory filings or dividend payments).

Regulatory basis:
  FinCEN Advisory: "Accounts that are newly opened and immediately used
  for large transactions, especially wire transfers, are a red flag for
  money laundering or fraud."

  FATF Typology 4.2: "Use of newly-opened accounts for immediate
  high-value or high-volume transactions."
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import timedelta
from backend.detection.rules.base_rule import RuleSignal, get_latest_date

# ─── Thresholds ──────────────────────────────────────────────────────────────

# Account opened within this many days AND has high activity
NEW_ACCOUNT_DAYS = 30

# If account is new AND has transactions exceeding this, it's suspicious
NEW_ACCOUNT_MIN_AMOUNT = 10_000.0

# Rapid cycling: account lifetime vs. active period ratio
# If 90%+ of activity happened in < 20% of account lifetime, flag it
ACTIVITY_CONCENTRATION_RATIO = 0.20

SIGNAL_WEIGHT = 1.3
BASE_SCORE    = 35.0


def check_account_age(
    account_id:    str,
    transactions:  list,
    opened_date=None,
) -> RuleSignal | None:
    """
    Detect suspicious account age / activity timing patterns.

    Args:
        account_id:   The account being analysed.
        transactions: All transactions for this account.
        opened_date:  When the account was opened (datetime object).
                      If None, only the rapid-cycling check is skipped.

    Returns:
        RuleSignal if suspicious age pattern detected, None otherwise.
    """
    if not transactions:
        return None

    findings:       list[str] = []
    score_additions: float    = 0.0
    latest_date = get_latest_date(transactions)

    # ── Check 1: New account with immediate high-value activity ───────────────
    if opened_date is not None:
        account_age_days = (latest_date - opened_date).days

        if account_age_days <= NEW_ACCOUNT_DAYS:
            # Account is very new — check if it already has large transactions
            large_txs = [
                tx for tx in transactions
                if tx['amount'] >= NEW_ACCOUNT_MIN_AMOUNT
            ]

            if large_txs:
                total_large = sum(tx['amount'] for tx in large_txs)
                score_additions += 20.0
                findings.append(
                    f"Account opened {account_age_days} days ago but already has "
                    f"{len(large_txs)} transaction(s) ≥ ${NEW_ACCOUNT_MIN_AMOUNT:,.0f} "
                    f"(total ${total_large:,.0f})"
                )

    # ── Check 2: Rapid cycling (concentrated activity) ────────────────────────
    if len(transactions) >= 5:
        # Find the date range of ALL activity
        tx_dates   = [tx['transaction_date'] for tx in transactions]
        first_tx   = min(tx_dates)
        last_tx    = max(tx_dates)
        full_range = (last_tx - first_tx).days

        if full_range > 0:
            # Find the 80% window: period when most activity happened
            # Sort transactions by date, find the window where 80% of txs occur
            sorted_txs = sorted(transactions, key=lambda t: t['transaction_date'])
            target_count = int(len(sorted_txs) * 0.80)

            # Sliding window to find minimum-width window containing 80% of txs
            min_window = full_range  # start with full range
            for i in range(len(sorted_txs) - target_count + 1):
                start = sorted_txs[i]['transaction_date']
                end   = sorted_txs[i + target_count - 1]['transaction_date']
                window_days = (end - start).days
                min_window = min(min_window, window_days)

            # If 80% of activity happened in < 20% of the full range
            concentration = min_window / full_range if full_range > 0 else 1.0
            if concentration <= ACTIVITY_CONCENTRATION_RATIO:
                score_additions += 15.0
                findings.append(
                    f"Rapid cycling: 80% of transactions occurred in "
                    f"{min_window} days out of {full_range}-day account history "
                    f"(concentration ratio: {concentration:.1%})"
                )

    if not findings:
        return None

    score      = min(80.0, BASE_SCORE + score_additions)
    confidence = min(0.80, 0.40 + len(findings) * 0.20)
    evidence   = "Account age anomaly: " + "; ".join(findings) + "."

    return RuleSignal(
        account_id  = account_id,
        signal_type = 'account_age',
        score       = round(score, 1),
        weight      = SIGNAL_WEIGHT,
        evidence    = evidence,
        confidence  = round(confidence, 2),
    )
