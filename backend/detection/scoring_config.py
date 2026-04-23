"""
backend/detection/scoring_config.py
─────────────────────────────────────────────────────────────────────────────
Centralized scoring configuration.

Why a config module?
  Previously, weights were scattered across individual rule files.
  Centralizing them here means a compliance officer can tune the scoring
  by changing ONE file, without touching any detection logic.

  This is a real-world pattern: "business rules" separated from "detection logic."
  In production, these weights would be stored in a database so they can be
  changed without redeploying code.
─────────────────────────────────────────────────────────────────────────────
"""

# ── Signal weights ─────────────────────────────────────────────────────────────
# Higher weight = signal counts more in the final score.
# These are calibrated based on:
#   1. Signal precision (low FPR → higher weight)
#   2. Regulatory importance (structuring is a federal crime → higher weight)
#   3. Evidence quality (rule with strong evidence → higher weight)

SIGNAL_WEIGHTS: dict[str, float] = {
    # Rules-based signals
    "structuring_rule":  2.0,   # Very high precision, federal crime
    "funnel_rule":       1.8,   # Distinctive pattern, low false positive rate
    "dormant_rule":      1.5,   # Good signal but can be seasonal
    "velocity_rule":     1.5,   # Higher FPR than structuring — weight reflects this
    "round_number_rule": 0.5,   # Supporting signal only — high FPR alone

    # Graph-based signals
    "graph_cycle":       2.0,   # Round-tripping is always suspicious
    "graph_community":   1.8,   # Shell clusters are very suspicious
    "graph_chain":       1.6,   # Layering intermediaries
    "graph_pagerank":    1.5,   # Useful but fires on legitimate high-volume accounts
}

# ── Score thresholds ──────────────────────────────────────────────────────────
# Used to determine risk tier (displayed in the dashboard as colors)

TIER_THRESHOLDS: dict[str, float] = {
    "critical": 75.0,   # Score 75-100 → RED — review immediately
    "high":     50.0,   # Score 50-74 → ORANGE — review today
    "medium":   25.0,   # Score 25-49 → YELLOW — review this week
    "low":       0.0,   # Score 0-24  → GREEN — low priority
}

# ── Pile-up bonus parameters ──────────────────────────────────────────────────
# When multiple signals fire, we add a bonus (accounts triggering multiple
# patterns are more suspicious than accounts triggering just one).

PILE_UP_THRESHOLD  = 2    # pile-up kicks in after this many signals
PILE_UP_POINTS_PER = 3.0  # points added per additional signal
PILE_UP_MAX        = 10.0 # maximum total pile-up bonus

# ── Score ceiling for individual signals ──────────────────────────────────────
# No single rule can score above 95 (reserves 95-100 for combined signals only)
SINGLE_SIGNAL_CEILING = 95.0

# ── Confidence floor ──────────────────────────────────────────────────────────
# If a signal fires with confidence below this, we still count it but at
# reduced impact. We never completely ignore a signal.
MIN_CONFIDENCE = 0.10
