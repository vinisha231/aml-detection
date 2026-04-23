"""
backend/detection/rules/cash_intensive_rule.py
─────────────────────────────────────────────────────────────────────────────
Detection rule for accounts with disproportionately high cash activity.

What is a cash-intensive business risk?
  Some legitimate businesses (restaurants, car washes, nail salons) have
  high cash volumes. However, these businesses are also frequently used
  as fronts for money laundering — the launderer mixes dirty cash with
  legitimate cash revenue, making it impossible to distinguish the source.

  This is the "integration" phase of money laundering: the dirty money
  enters the financial system through a business that plausibly explains
  large cash deposits.

What we flag:
  1. Cash deposits make up > 80% of total deposits (normal businesses have mix)
  2. Cash deposit volume per week exceeds what most legitimate businesses do
  3. Cash deposits occur outside business hours (3am–6am is unusual for any business)

  Account types that legitimately have high cash: BUSINESS, LLC, SOLE_PROP
  A PERSONAL account with 90% cash deposits is far more suspicious.

Regulatory note:
  Banks must conduct Customer Due Diligence (CDD) for accounts with unusual
  cash activity. High cash concentration ratios are a known AML typology
  listed in FinCEN guidance on cash-intensive businesses.
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import timedelta

from backend.detection.rules.base_rule import RuleSignal, get_latest_date

# ─── Thresholds ──────────────────────────────────────────────────────────────

# Cash concentration ratio above this is suspicious
HIGH_CASH_RATIO = 0.80  # 80% of deposits are cash

# Weekly cash deposit volume that triggers review
HIGH_WEEKLY_CASH = 20_000.0

# Hours considered "suspicious" for cash deposits (3am–6am)
SUSPICIOUS_HOUR_START = 3
SUSPICIOUS_HOUR_END   = 6

# Minimum number of transactions for analysis
MIN_TX_COUNT = 5

LOOKBACK_DAYS  = 60
SIGNAL_WEIGHT  = 1.3
BASE_SCORE     = 35.0


def check_cash_intensive(
    account_id:   str,
    transactions: list,
    account_type: str = 'PERSONAL',
) -> RuleSignal | None:
    """
    Detect disproportionate cash activity for this account.

    Args:
        account_id:   The account being analysed.
        transactions: All transactions for this account.
        account_type: Account type (PERSONAL, BUSINESS, LLC, etc.)
                      Business accounts get a slightly higher threshold.

    Returns:
        RuleSignal if cash-intensive pattern detected, None otherwise.
    """
    if not transactions:
        return None

    latest_date = get_latest_date(transactions)
    cutoff      = latest_date - timedelta(days=LOOKBACK_DAYS)

    # Filter to inbound transactions (deposits) within lookback window
    deposits = [
        tx for tx in transactions
        if tx.get('receiver_account_id') == account_id
        and tx['transaction_date'] >= cutoff
    ]

    if len(deposits) < MIN_TX_COUNT:
        return None

    # Split cash vs non-cash deposits
    cash_deposits = [tx for tx in deposits if tx.get('transaction_type') == 'CASH_DEPOSIT']
    total_deposits = len(deposits)

    if not cash_deposits:
        return None

    cash_ratio     = len(cash_deposits) / total_deposits
    total_cash_amt = sum(tx['amount'] for tx in cash_deposits)
    weeks_in_window = LOOKBACK_DAYS / 7
    weekly_cash    = total_cash_amt / weeks_in_window

    findings: list[str] = []
    score_additions      = 0.0

    # ── Check 1: High cash concentration ratio ────────────────────────────────
    # Business accounts have a higher legitimate threshold
    effective_threshold = HIGH_CASH_RATIO if account_type == 'PERSONAL' else 0.90
    if cash_ratio >= effective_threshold:
        ratio_bonus = min(20.0, (cash_ratio - effective_threshold) * 100)
        score_additions += 15.0 + ratio_bonus
        findings.append(
            f"Cash concentration: {cash_ratio*100:.0f}% of deposits are cash "
            f"({'personal' if account_type=='PERSONAL' else 'business'} account)"
        )

    # ── Check 2: High weekly cash volume ─────────────────────────────────────
    if weekly_cash >= HIGH_WEEKLY_CASH:
        import math
        vol_bonus = min(15.0, math.log10(weekly_cash / HIGH_WEEKLY_CASH + 1) * 15)
        score_additions += 10.0 + vol_bonus
        findings.append(
            f"Avg weekly cash deposits: ${weekly_cash:,.0f}"
        )

    # ── Check 3: After-hours cash deposits ───────────────────────────────────
    after_hours = [
        tx for tx in cash_deposits
        if SUSPICIOUS_HOUR_START <= tx['transaction_date'].hour < SUSPICIOUS_HOUR_END
    ]
    if after_hours:
        ah_ratio = len(after_hours) / len(cash_deposits)
        if ah_ratio >= 0.15:  # > 15% of cash deposits happen in 3–6am window
            score_additions += 10.0
            findings.append(
                f"{len(after_hours)} cash deposits between 3–6am "
                f"({ah_ratio*100:.0f}% of all cash deposits)"
            )

    if not findings:
        return None

    score      = min(90.0, BASE_SCORE + score_additions)
    confidence = min(0.80, 0.40 + len(findings) * 0.15)

    evidence = "Cash-intensive activity: " + "; ".join(findings) + "."

    return RuleSignal(
        account_id  = account_id,
        signal_type = 'cash_intensive',
        score       = round(score, 1),
        weight      = SIGNAL_WEIGHT,
        evidence    = evidence,
        confidence  = round(confidence, 2),
    )
