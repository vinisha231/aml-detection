"""
backend/detection/scoring_explainer.py
─────────────────────────────────────────────────────────────────────────────
Human-readable explanation generator for risk scores.

Why do we need an explainer?
  The scoring engine produces a number (e.g., 78.5). But an AML analyst
  needs to know WHY the score is 78.5 before they can decide whether to
  escalate or dismiss.

  Explainability is also a regulatory requirement:
    - BSA regulations require banks to document the basis for SAR filings
    - Examiners ask "how did you decide to file this SAR?"
    - Banks must be able to demonstrate their AML program is risk-based,
      not arbitrary

  This module converts the list of signals that contributed to a score
  into a natural-language paragraph that an analyst can read and evaluate.

Output format:
  "Account scored 78.5 (HIGH risk) based on 3 signals:
   Primary driver: Structuring pattern detected — 8 cash deposits of
   $9,200–$9,800 over 10 days ($76,400 total). Supporting: High PageRank
   centrality (top 5% of network); Round numbers in 65% of transactions.
   Score reflects weighted combination with pile-up bonus for 3 signals."
─────────────────────────────────────────────────────────────────────────────
"""

from backend.detection.rules.base_rule import RuleSignal
from backend.detection.scoring import get_risk_tier


# ─── Signal label mapping ─────────────────────────────────────────────────────

SIGNAL_LABELS = {
    'structuring':       'Structuring (sub-threshold deposits)',
    'velocity':          'Velocity anomaly',
    'funnel':            'Funnel account pattern',
    'dormant_wakeup':    'Dormant account wakeup',
    'round_number':      'Round number transactions',
    'layering':          'Layering (wire pass-through)',
    'smurfing':          'Smurfing (coordinated deposits)',
    'high_value':        'High-value transaction alert',
    'cash_intensive':    'Cash-intensive activity',
    'geographic':        'Geographic anomaly',
    'graph_pagerank':    'High network centrality (PageRank)',
    'graph_community':   'Isolated community cluster',
    'graph_cycle':       'Round-trip cycle',
    'graph_chain':       'Layering chain (betweenness)',
    'graph_betweenness': 'Bridge node (betweenness centrality)',
    'graph_hub_spoke':   'Hub-and-spoke distribution',
}


def generate_explanation(
    account_id: str,
    final_score: float,
    signals: list[RuleSignal],
) -> str:
    """
    Generate a human-readable explanation for an account's risk score.

    The explanation is structured as:
      1. Score summary (score, tier, number of signals)
      2. Primary driver (highest-weight signal)
      3. Supporting signals (remaining signals)
      4. Scoring methodology note

    Args:
        account_id:  The account ID for personalisation.
        final_score: The final weighted risk score (0–100).
        signals:     All signals that contributed to the score.

    Returns:
        A multi-sentence explanation string suitable for display to analysts.
    """
    if not signals:
        return (
            f"Account {account_id} scored {final_score:.1f} "
            f"({get_risk_tier(final_score).upper()} risk). "
            f"No specific signals detected — score reflects baseline assessment."
        )

    tier = get_risk_tier(final_score).upper()

    # Sort signals by effective contribution: score × weight × confidence
    def contribution(sig: RuleSignal) -> float:
        return sig.score * sig.weight * sig.confidence

    sorted_signals = sorted(signals, key=contribution, reverse=True)
    primary        = sorted_signals[0]
    supporting     = sorted_signals[1:]

    # ── Build the explanation ─────────────────────────────────────────────────
    parts: list[str] = []

    # Score header
    signal_count = len(signals)
    parts.append(
        f"Account {account_id} scored {final_score:.1f} ({tier} risk) "
        f"based on {signal_count} detection signal{'s' if signal_count != 1 else ''}."
    )

    # Primary driver
    primary_label = SIGNAL_LABELS.get(primary.signal_type, primary.signal_type)
    parts.append(
        f"Primary driver: {primary_label} "
        f"(score {primary.score:.0f}/100, confidence {primary.confidence:.0%}). "
        f"{primary.evidence}"
    )

    # Supporting signals
    if supporting:
        supporting_parts = []
        for sig in supporting[:3]:  # limit to top 3 supporting signals for readability
            label = SIGNAL_LABELS.get(sig.signal_type, sig.signal_type)
            supporting_parts.append(
                f"{label} (score {sig.score:.0f})"
            )
        parts.append(
            "Supporting signals: " + "; ".join(supporting_parts) + "."
        )

    # Pile-up note
    if signal_count >= 3:
        parts.append(
            f"Multi-signal convergence: {signal_count} signals firing together "
            f"increases confidence — accounts with multiple independent indicators "
            f"are significantly more likely to be suspicious."
        )

    return " ".join(parts)


def format_signal_summary(signals: list[RuleSignal]) -> str:
    """
    One-line summary of all signals for use in table views.

    Example: "structuring (85), graph_cycle (72), velocity (65)"

    Args:
        signals: List of RuleSignal objects.

    Returns:
        Comma-separated signal names with scores, sorted by score desc.
    """
    sorted_sigs = sorted(signals, key=lambda s: s.score, reverse=True)
    parts = [
        f"{SIGNAL_LABELS.get(s.signal_type, s.signal_type)} ({s.score:.0f})"
        for s in sorted_sigs[:5]  # cap at 5 for readability
    ]
    if len(signals) > 5:
        parts.append(f"+{len(signals) - 5} more")
    return ", ".join(parts)
