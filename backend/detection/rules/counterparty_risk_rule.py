"""
backend/detection/rules/counterparty_risk_rule.py
─────────────────────────────────────────────────────────────────────────────
Detection rule for accounts that transact heavily with other high-risk accounts.

Counterparty risk — why it matters:
  Even if an account's own behaviour looks clean (no structuring, normal velocity),
  it may still be part of a laundering network by transacting with known bad actors.

  This is the "guilt by association" principle used in AML:
    - If you frequently wire money to an account that was flagged for structuring,
      you are likely part of the same scheme.
    - If your primary counterparty is a shell company cluster, you may be a node
      in that cluster that wasn't directly detected by individual rules.

  This rule is a "second-order" signal: it uses the scores of other accounts
  (computed in a previous pipeline pass) to evaluate the current account.

How we implement it:
  For each account, look at its transaction counterparties and check if those
  counterparties have high risk scores in the database. If the account's
  counterparties collectively have high average risk, flag the account.

  This is similar to how PageRank works (a node's importance depends on
  its neighbours' importance), but simpler and more interpretable.

Note on pipeline ordering:
  This rule must run AFTER other accounts have been scored. It cannot be
  part of the first-pass pipeline — it needs the risk_score column populated.
  In practice, you'd run the full pipeline, then run counterparty_risk as
  a second pass to catch accounts missed in the first pass.
─────────────────────────────────────────────────────────────────────────────
"""

from backend.detection.rules.base_rule import RuleSignal

# ─── Thresholds ──────────────────────────────────────────────────────────────

# Average counterparty risk score that triggers this rule
MIN_AVG_COUNTERPARTY_SCORE = 60.0

# Minimum number of high-risk counterparties to flag
MIN_HIGH_RISK_COUNTERPARTIES = 2

# A counterparty is "high risk" if their score exceeds this
COUNTERPARTY_HIGH_RISK_THRESHOLD = 70.0

SIGNAL_WEIGHT = 1.5
BASE_SCORE    = 40.0


def check_counterparty_risk(
    account_id:          str,
    counterparty_scores: dict[str, float],
) -> RuleSignal | None:
    """
    Detect if this account's transaction counterparties have high risk scores.

    Args:
        account_id:           The account being evaluated.
        counterparty_scores:  Dict mapping counterparty account_id → risk_score.
                              Only include counterparties that have been scored.

    Returns:
        RuleSignal if counterparty risk pattern detected, None otherwise.
    """
    if not counterparty_scores:
        return None

    scores = list(counterparty_scores.values())
    avg_score = sum(scores) / len(scores)

    # Count how many counterparties are individually high risk
    high_risk_counterparties = {
        acc_id: score
        for acc_id, score in counterparty_scores.items()
        if score >= COUNTERPARTY_HIGH_RISK_THRESHOLD
    }
    n_high_risk = len(high_risk_counterparties)

    # Check if either condition triggers
    avg_trigger  = avg_score >= MIN_AVG_COUNTERPARTY_SCORE
    count_trigger = n_high_risk >= MIN_HIGH_RISK_COUNTERPARTIES

    if not (avg_trigger or count_trigger):
        return None

    # ── Score ─────────────────────────────────────────────────────────────────
    # Base score + bonus for higher avg score and more high-risk counterparties
    avg_bonus   = min(25.0, max(0.0, avg_score - MIN_AVG_COUNTERPARTY_SCORE) * 0.8)
    count_bonus = min(20.0, n_high_risk * 5)
    score       = min(88.0, BASE_SCORE + avg_bonus + count_bonus)

    confidence  = min(0.85, 0.45 + (n_high_risk / max(len(scores), 1)) * 0.35)

    # Format the top high-risk counterparties for the evidence string
    top_risky = sorted(high_risk_counterparties.items(), key=lambda x: x[1], reverse=True)[:3]
    risky_str = ', '.join(f'{acc} ({sc:.0f})' for acc, sc in top_risky)

    evidence = (
        f"Counterparty risk: {n_high_risk} high-risk counterparties "
        f"(score ≥ {COUNTERPARTY_HIGH_RISK_THRESHOLD}). "
        f"Avg counterparty score: {avg_score:.1f}. "
        f"Top risky counterparties: {risky_str}."
    )

    return RuleSignal(
        account_id  = account_id,
        signal_type = 'counterparty_risk',
        score       = round(score, 1),
        weight      = SIGNAL_WEIGHT,
        evidence    = evidence,
        confidence  = round(confidence, 2),
    )
