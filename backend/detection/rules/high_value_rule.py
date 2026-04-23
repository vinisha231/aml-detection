"""
backend/detection/rules/high_value_rule.py
─────────────────────────────────────────────────────────────────────────────
Detection rule for unusually large individual transactions.

Why large transactions are suspicious:
  While most people make payments of hundreds or thousands of dollars,
  money launderers often move large sums in single transactions to
  quickly move funds through the system.

  Regulatory context:
    - Banks must file Currency Transaction Reports (CTRs) for cash
      transactions over $10,000 (U.S. BSA requirement)
    - Wire transfers above $3,000 trigger enhanced due diligence
    - Unusual large ACH/wire transfers without business justification
      are a common red flag

This rule flags:
  1. Any single transaction above $50,000 (not structuring threshold)
  2. Burst of transactions totalling > $200,000 within 48 hours
  3. Sudden spike: account's largest-ever transaction is 5x its average

Important: This is a LOW-WEIGHT signal (0.8) because large transactions
  alone are not conclusive — many legitimate businesses routinely wire
  large sums. It becomes meaningful when combined with other signals
  (e.g., high_value + graph_cycle = round-tripping with large amounts).
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import timedelta
from statistics import mean, stdev

from backend.detection.rules.base_rule import RuleSignal, get_latest_date

# ─── Thresholds ──────────────────────────────────────────────────────────────

# A single transaction above this is noteworthy
LARGE_TX_THRESHOLD = 50_000.0

# Total amount within 48 hours that triggers the burst flag
BURST_TOTAL_THRESHOLD = 200_000.0
BURST_WINDOW_HOURS    = 48

# How many times larger than average must the max transaction be?
SPIKE_MULTIPLIER = 5.0

# Lookback window for calculating average transaction size
LOOKBACK_DAYS = 90

# Minimum transactions needed for spike detection (need a baseline)
MIN_TX_FOR_BASELINE = 10

# Rule configuration
SIGNAL_WEIGHT = 0.8
BASE_SCORE    = 35.0


def check_high_value(account_id: str, transactions: list) -> RuleSignal | None:
    """
    Detect unusually high-value transactions for this account.

    Three sub-checks:
      A. Single transaction exceeds $50k
      B. Multiple transactions total > $200k within 48 hours
      C. Largest transaction is 5x the account's historical average

    All three contribute to the final score additively.

    Args:
        account_id:   The account being analysed.
        transactions: All transactions for this account.

    Returns:
        RuleSignal if any high-value pattern is detected, None otherwise.
    """
    if not transactions:
        return None

    latest_date = get_latest_date(transactions)
    cutoff_date = latest_date - timedelta(days=LOOKBACK_DAYS)

    # Filter to the lookback window
    recent_txs = [
        tx for tx in transactions
        if tx['transaction_date'] >= cutoff_date
    ]

    if not recent_txs:
        return None

    amounts = [tx['amount'] for tx in recent_txs]
    max_amount = max(amounts)
    avg_amount = mean(amounts)

    findings: list[str] = []  # human-readable evidence items
    score_additions = 0.0

    # ── Check A: Single large transaction ─────────────────────────────────────
    if max_amount >= LARGE_TX_THRESHOLD:
        large_txs = [tx for tx in recent_txs if tx['amount'] >= LARGE_TX_THRESHOLD]
        count = len(large_txs)
        score_additions += min(25.0, count * 8)
        findings.append(
            f"{count} transaction(s) above $50,000 (largest: ${max_amount:,.0f})"
        )

    # ── Check B: Burst total within 48 hours ─────────────────────────────────
    # Sliding window: for each transaction, sum all transactions within 48h after it
    for i, tx in enumerate(recent_txs):
        window_end = tx['transaction_date'] + timedelta(hours=BURST_WINDOW_HOURS)
        window_total = sum(
            t['amount'] for t in recent_txs[i:]
            if t['transaction_date'] <= window_end
        )
        if window_total >= BURST_TOTAL_THRESHOLD:
            score_additions += 20.0
            findings.append(
                f"${window_total:,.0f} moved within a 48-hour window"
            )
            break  # only count once

    # ── Check C: Spike vs historical average ─────────────────────────────────
    if len(amounts) >= MIN_TX_FOR_BASELINE and avg_amount > 0:
        spike_ratio = max_amount / avg_amount
        if spike_ratio >= SPIKE_MULTIPLIER:
            score_additions += min(15.0, spike_ratio * 2)
            findings.append(
                f"Largest transaction (${max_amount:,.0f}) is "
                f"{spike_ratio:.1f}x the account average (${avg_amount:,.0f})"
            )

    if not findings:
        return None  # none of the three checks triggered

    # Final score
    score = min(90.0, BASE_SCORE + score_additions)

    # Confidence scales with number of findings triggered
    confidence = min(0.85, 0.4 + len(findings) * 0.2)

    evidence = "High-value transaction alert: " + "; ".join(findings) + "."

    return RuleSignal(
        account_id  = account_id,
        signal_type = 'high_value',
        score       = round(score, 1),
        weight      = SIGNAL_WEIGHT,
        evidence    = evidence,
        confidence  = round(confidence, 2),
    )
