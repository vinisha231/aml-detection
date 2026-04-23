"""
backend/detection/rules/geographic_rule.py
─────────────────────────────────────────────────────────────────────────────
Detection rule for geographic anomalies in transaction patterns.

Why geography matters in AML:
  Money launderers often route funds through jurisdictions with:
    - Weak AML enforcement (high-risk countries)
    - Bank secrecy laws (offshore havens)
    - No beneficial ownership registries (shell company hotspots)

  The FATF (Financial Action Task Force) maintains a "grey list" of
  countries with strategic AML/CFT deficiencies. Transactions flowing
  through these jurisdictions require enhanced due diligence.

What we simulate:
  Our dataset doesn't have real geographic data, but we use branch codes
  as a proxy. Branches with codes starting with "OFC" (offshore) or
  "INT" (international) simulate high-risk jurisdictions.

Detection logic:
  1. Counterparty in high-risk branch: direct exposure to risky jurisdiction
  2. Rapid multi-branch movement: funds moving through 3+ branches in 7 days
     (simulates cross-border layering)
  3. All funds concentrated to offshore branch accounts

This is a supporting signal (weight = 1.2) — geographic risk alone isn't
conclusive but amplifies other signals significantly.
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import timedelta
from collections import Counter

from backend.detection.rules.base_rule import RuleSignal, get_latest_date

# ─── High-risk branch prefixes (simulating offshore jurisdictions) ────────────
HIGH_RISK_BRANCH_PREFIXES = ('OFC', 'INT', 'SHL')  # offshore, international, shell

# Rapid multi-branch thresholds
RAPID_BRANCH_WINDOW_DAYS = 7
MIN_BRANCHES_FOR_FLAG    = 3  # involved in 3+ branches within the window

SIGNAL_WEIGHT = 1.2
BASE_SCORE    = 30.0
LOOKBACK_DAYS = 60


def check_geographic_anomaly(
    account_id: str,
    transactions: list,
    account_branch: str = '',
) -> RuleSignal | None:
    """
    Detect geographic risk factors in this account's transaction pattern.

    Args:
        account_id:     The account being analysed.
        transactions:   All transactions for this account.
        account_branch: The branch code of this account (from the Account table).

    Returns:
        RuleSignal if geographic anomalies are detected, None otherwise.
    """
    if not transactions:
        return None

    latest_date = get_latest_date(transactions)
    cutoff_date = latest_date - timedelta(days=LOOKBACK_DAYS)

    recent_txs = [
        tx for tx in transactions
        if tx['transaction_date'] >= cutoff_date
    ]

    if not recent_txs:
        return None

    findings: list[str] = []
    score_additions = 0.0

    # ── Check 1: Account itself is in a high-risk branch ─────────────────────
    if any(account_branch.upper().startswith(p) for p in HIGH_RISK_BRANCH_PREFIXES):
        score_additions += 20.0
        findings.append(f"Account registered at high-risk branch '{account_branch}'")

    # ── Check 2: Counterparty in a high-risk branch ───────────────────────────
    # In our simplified model, branch info is embedded in account IDs
    # (accounts with IDs starting with 'OFC_' or 'INT_' are offshore)
    offshore_counterparties = set()
    for tx in recent_txs:
        sender   = tx.get('sender_account_id', '')
        receiver = tx.get('receiver_account_id', '')
        counterparty = receiver if sender == account_id else sender

        if any(counterparty.upper().startswith(p) for p in HIGH_RISK_BRANCH_PREFIXES):
            offshore_counterparties.add(counterparty)

    if offshore_counterparties:
        count = len(offshore_counterparties)
        score_additions += min(25.0, count * 8)
        findings.append(
            f"Transactions with {count} offshore/high-risk counterparty account(s)"
        )

    # ── Check 3: Rapid multi-branch movement ─────────────────────────────────
    # Track unique sender branches within a rolling 7-day window
    # (In a real system, each transaction would have a branch code)
    # We approximate using counterparty account ID prefixes as branch indicators
    for i, tx in enumerate(recent_txs):
        window_end = tx['transaction_date'] + timedelta(days=RAPID_BRANCH_WINDOW_DAYS)
        window_txs = [
            t for t in recent_txs[i:]
            if t['transaction_date'] <= window_end
        ]

        # Collect unique "branch regions" from counterparty IDs (first 3 chars)
        regions = {
            (t.get('sender_account_id', '') if t.get('receiver_account_id') == account_id
             else t.get('receiver_account_id', ''))[:3]
            for t in window_txs
        }
        regions.discard(account_id[:3])  # exclude the focal account's own "branch"

        if len(regions) >= MIN_BRANCHES_FOR_FLAG:
            score_additions += 15.0
            findings.append(
                f"Funds moved across {len(regions)} branch regions within 7 days"
            )
            break

    if not findings:
        return None

    score = min(85.0, BASE_SCORE + score_additions)
    confidence = min(0.75, 0.35 + len(findings) * 0.15)

    evidence = "Geographic anomaly: " + "; ".join(findings) + "."

    return RuleSignal(
        account_id  = account_id,
        signal_type = 'geographic',
        score       = round(score, 1),
        weight      = SIGNAL_WEIGHT,
        evidence    = evidence,
        confidence  = round(confidence, 2),
    )
