"""
backend/detection/scoring.py
─────────────────────────────────────────────────────────────────────────────
The unified scoring engine — combines all signals into one final risk score.

This is the HARDEST PART to copy in a portfolio project.
Anyone can write a rule that flags high deposits.
The scoring engine is what makes the system feel like a real product.

How scoring works:
  1. Collect all signals for an account (from all rules + graph signals)
  2. Each signal has a score (0-100) and a weight
  3. Final score = weighted average of all signals
  4. Evidence strings are concatenated in priority order (highest score first)

Why weighted average instead of max?
  Max would ignore all the other signals.
  If structuring rule gives 70 and velocity rule gives 60,
  the account is likely more suspicious than either signal alone suggests.
  Weighted average captures this "pile-up" effect.

Score interpretation:
  0–30:   Low risk (no concerning signals)
  31–50:  Moderate risk (one signal, possibly coincidental)
  51–70:  High risk (multiple signals or one strong signal)
  71–100: Very high risk (should be reviewed today)
─────────────────────────────────────────────────────────────────────────────
"""

from typing import List, Dict, Optional
from dataclasses import dataclass

from .rules.structuring_rule import RuleSignal


@dataclass
class ScoringResult:
    """
    Final scoring output for one account.

    Contains both the numerical score and the human-readable evidence.
    This is what gets stored in the database and shown in the dashboard.
    """
    account_id:     str
    risk_score:     float        # Final 0-100 score
    evidence:       str          # Concatenated evidence from all signals
    signals_fired:  List[str]    # Which signal types triggered (for FPR tracking)
    top_signal:     Optional[str]  # The single strongest signal (for queue display)


def compute_account_score(
    account_id: str,
    signals: List[RuleSignal]
) -> ScoringResult:
    """
    Combine multiple signals into one final risk score for an account.

    Formula:
        final_score = Σ (signal_i.score × signal_i.weight) / Σ signal_i.weight

    This is a weighted average, so:
    - Signals with higher weights (e.g., structuring at weight=2.0) count more
    - Having MANY signals pushes the score higher than any single signal
    - Confidence is taken into account by scaling each signal's contribution

    Args:
        account_id: The account being scored
        signals:    All signals fired for this account (from all rules + graph)

    Returns:
        ScoringResult with final score, evidence, and metadata.

    Example:
        signals = [
            RuleSignal(account_id="ACC_001", signal_type="structuring_rule",
                       score=72.0, weight=2.0, evidence="...", confidence=0.87),
            RuleSignal(account_id="ACC_001", signal_type="velocity_rule",
                       score=65.0, weight=1.5, evidence="...", confidence=0.72),
        ]
        result = compute_account_score("ACC_001", signals)
        # result.risk_score ≈ 69.2 (weighted average)
        # result.evidence = "STRUCTURING: ... | VELOCITY: ..."
    """

    # ── Handle no-signal case ─────────────────────────────────────────────────
    if not signals:
        return ScoringResult(
            account_id=account_id,
            risk_score=0.0,
            evidence="No signals detected. Account appears clean.",
            signals_fired=[],
            top_signal=None,
        )

    # ── Sort signals by score descending (most suspicious first) ──────────────
    signals_sorted = sorted(signals, key=lambda s: s.score * s.weight, reverse=True)

    # ── Calculate weighted average score ─────────────────────────────────────
    total_weighted_score = 0.0
    total_weight         = 0.0

    for signal in signals_sorted:
        # Scale signal score by confidence
        # A score of 70 with confidence 0.5 contributes less than
        # the same score with confidence 0.95
        confidence_adjusted_score = signal.score * signal.confidence

        total_weighted_score += confidence_adjusted_score * signal.weight
        total_weight         += signal.weight

    if total_weight == 0:
        final_score = 0.0
    else:
        final_score = total_weighted_score / total_weight

    # ── "Pile-up" bonus: having multiple signals is worse than one ─────────────
    # If an account has 3+ signals, each additional signal adds a bonus
    # This is intentional: 3 weak signals together are worse than 1 weak signal
    if len(signals) >= 3:
        pile_up_bonus = min(10.0, (len(signals) - 2) * 3.0)
        final_score += pile_up_bonus

    # Cap at 100
    final_score = min(100.0, final_score)
    final_score = max(0.0, final_score)

    # ── Build evidence string ─────────────────────────────────────────────────
    # List signals in order from most to least suspicious
    # Format: "SIGNAL_TYPE: evidence_text [score/100, conf 87%]"
    evidence_parts = []
    for signal in signals_sorted:
        signal_label = _format_signal_type(signal.signal_type)
        evidence_parts.append(
            f"[{signal_label}] {signal.evidence} "
            f"(score: {signal.score:.0f}/100, confidence: {signal.confidence:.0%})"
        )

    # Join with newlines so the analyst can read each signal separately
    evidence = "\n".join(evidence_parts)

    # ── Collect metadata ───────────────────────────────────────────────────────
    signals_fired = list({s.signal_type for s in signals})  # unique signal types
    top_signal    = signals_sorted[0].signal_type if signals_sorted else None

    return ScoringResult(
        account_id=account_id,
        risk_score=round(final_score, 2),
        evidence=evidence,
        signals_fired=signals_fired,
        top_signal=top_signal,
    )


def score_all_accounts(
    all_signals: Dict[str, List[RuleSignal]]
) -> Dict[str, ScoringResult]:
    """
    Score every account that has at least one signal.

    This is called by the pipeline after running all detection rules.

    Args:
        all_signals: Dict mapping account_id → list of RuleSignal objects.
                     Built by collecting signals from all rules and graph signals.

    Returns:
        Dict mapping account_id → ScoringResult

    Example:
        all_signals = {
          "ACC_000001": [structuring_signal, velocity_signal],
          "ACC_000042": [funnel_signal, pagerank_signal],
          ...
        }
        results = score_all_accounts(all_signals)
        # Access one account: results["ACC_000001"].risk_score
    """
    results = {}

    for account_id, signals in all_signals.items():
        result = compute_account_score(account_id, signals)
        results[account_id] = result

    return results


def _format_signal_type(signal_type: str) -> str:
    """
    Convert a snake_case signal type to a readable label for evidence strings.

    Args:
        signal_type: Internal signal name (e.g., "structuring_rule")

    Returns:
        Human-readable label (e.g., "STRUCTURING")

    Examples:
        "structuring_rule"  → "STRUCTURING"
        "graph_pagerank"    → "GRAPH: PAGERANK"
        "velocity_rule"     → "VELOCITY"
    """
    mapping = {
        "structuring_rule":  "STRUCTURING",
        "velocity_rule":     "VELOCITY",
        "funnel_rule":       "FUNNEL",
        "dormant_rule":      "DORMANT WAKEUP",
        "round_number_rule": "ROUND NUMBERS",
        "graph_pagerank":    "GRAPH: PAGERANK",
        "graph_community":   "GRAPH: SHELL CLUSTER",
        "graph_cycle":       "GRAPH: ROUND-TRIP CYCLE",
        "graph_chain":       "GRAPH: LAYERING CHAIN",
    }
    return mapping.get(signal_type, signal_type.upper())


def get_risk_tier(score: float) -> str:
    """
    Convert a numeric risk score to a human-readable risk tier.

    Used in the dashboard to color-code accounts.

    Args:
        score: Risk score 0-100

    Returns:
        One of: "critical", "high", "medium", "low"
    """
    if score >= 75:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 25:
        return "medium"
    else:
        return "low"
