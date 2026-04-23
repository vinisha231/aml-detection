"""
backend/detection/ensemble.py
─────────────────────────────────────────────────────────────────────────────
Ensemble coordinator that runs ALL detection rules and graph signals
and merges their outputs before scoring.

What is an ensemble approach?
  Instead of using one rule or one model to decide if an account is
  suspicious, we run MANY different checks:
    - 7 rule-based signals (structuring, velocity, funnel, layering, etc.)
    - 4 graph signals    (PageRank, community, cycle, chain)

  Each signal is independent — it looks for a different pattern.
  We then COMBINE all signals with a weighted scoring formula.

  Why ensemble?
    1. No single rule catches all laundering patterns
    2. Multiple signals firing together is much stronger evidence
    3. Different rules have different false positive rates — ensemble
       averaging reduces overall FPR compared to any individual rule
    4. Weights let us express "cycle detection is more reliable than
       round numbers" without hard-coding binary decisions

Architecture:
  run_all_rules(account_id, transactions)  → list[RuleSignal]
  run_graph_signals(G)                     → list[RuleSignal]
  merge_signals(rule_signals, graph_signals) → dict[account_id → list[RuleSignal]]

  Then scoring.py takes the merged signals and produces the final score.

This file owns the logic of WHICH rules to run and HOW to combine
their raw outputs before scoring.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import networkx as nx

# ── Rule-based detection imports ─────────────────────────────────────────────
from backend.detection.rules.base_rule        import RuleSignal
from backend.detection.rules.structuring_rule import check_structuring
from backend.detection.rules.velocity_rule    import check_velocity
from backend.detection.rules.funnel_rule      import check_funnel
from backend.detection.rules.dormant_rule     import check_dormant_wakeup
from backend.detection.rules.round_number_rule import check_round_numbers
from backend.detection.rules.layering_rule    import check_layering
from backend.detection.rules.smurfing_rule    import check_smurfing
from backend.detection.rules.high_value_rule  import check_high_value

# ── Graph signal imports ──────────────────────────────────────────────────────
from backend.detection.graph.pagerank_signal   import compute_pagerank_signals
from backend.detection.graph.community_signal  import compute_community_signals
from backend.detection.graph.cycle_signal      import compute_cycle_signals
from backend.detection.graph.chain_signal      import compute_chain_signals
from backend.detection.graph.betweenness_signal import compute_betweenness_signals
from backend.detection.graph.hub_spoke_signal  import compute_hub_spoke_signals


# ─── Rule runner ─────────────────────────────────────────────────────────────

def run_all_rules(
    account_id:   str,
    transactions: list,
    account_type: str = 'PERSONAL',
    account_branch: str = '',
) -> list[RuleSignal]:
    """
    Run all rule-based detectors for a single account.

    Each rule is independent — a failure in one rule does NOT prevent
    the others from running. This is achieved with try/except per rule.

    Args:
        account_id:     The account being analysed.
        transactions:   All transactions for this account.
        account_type:   Account type (e.g. PERSONAL, BUSINESS).
        account_branch: Branch code for geographic checks.

    Returns:
        List of RuleSignal objects from rules that fired.
        Empty list if no rules triggered.
    """
    signals: list[RuleSignal] = []

    # Rules to run, each as a (name, callable) tuple
    # The callable should accept (account_id, transactions) or a variant
    rule_checks = [
        ('structuring',   lambda: check_structuring(account_id, transactions)),
        ('velocity',      lambda: check_velocity(account_id, transactions)),
        ('funnel',        lambda: check_funnel(account_id, transactions)),
        ('dormant_wakeup', lambda: check_dormant_wakeup(account_id, transactions)),
        ('round_number',  lambda: check_round_numbers(account_id, transactions)),
        ('layering',      lambda: check_layering(account_id, transactions)),
        ('smurfing',      lambda: check_smurfing(account_id, transactions)),
        ('high_value',    lambda: check_high_value(account_id, transactions)),
        ('cash_intensive', lambda: check_cash_intensive_safe(account_id, transactions, account_type)),
    ]

    for rule_name, rule_fn in rule_checks:
        try:
            result = rule_fn()
            if result is not None:
                signals.append(result)
        except Exception as e:
            # Log but don't crash — one bad rule shouldn't break the whole pipeline
            import logging
            logging.getLogger('aml').warning(
                f"Rule '{rule_name}' failed for {account_id}: {e}"
            )

    return signals


def check_cash_intensive_safe(
    account_id: str, transactions: list, account_type: str
) -> RuleSignal | None:
    """Wrapper to import cash_intensive lazily (avoids circular import at module level)."""
    from backend.detection.rules.cash_intensive_rule import check_cash_intensive
    return check_cash_intensive(account_id, transactions, account_type)


# ─── Graph signal runner ──────────────────────────────────────────────────────

def run_graph_signals(G: nx.DiGraph) -> list[RuleSignal]:
    """
    Run all graph-based detectors on the full transaction graph.

    Graph signals analyse the NETWORK STRUCTURE, not individual account
    behaviour. They look for:
      - Accounts that are structurally central (PageRank, betweenness)
      - Tightly-knit isolated communities (Louvain)
      - Circular money flows (cycle detection)
      - Linear pass-through chains (chain detection)
      - Hub-and-spoke distribution patterns

    Args:
        G: The full transaction graph (built by graph/builder.py).

    Returns:
        All signals from all graph detectors combined.
    """
    signals: list[RuleSignal] = []

    graph_detectors = [
        ('pagerank',    lambda: compute_pagerank_signals(G)),
        ('community',   lambda: compute_community_signals(G)),
        ('cycle',       lambda: compute_cycle_signals(G)),
        ('chain',       lambda: compute_chain_signals(G)),
        ('betweenness', lambda: compute_betweenness_signals(G)),
        ('hub_spoke',   lambda: compute_hub_spoke_signals(G)),
    ]

    for detector_name, detector_fn in graph_detectors:
        try:
            results = detector_fn()
            signals.extend(results)
        except Exception as e:
            import logging
            logging.getLogger('aml').warning(
                f"Graph detector '{detector_name}' failed: {e}"
            )

    return signals


# ─── Signal merger ────────────────────────────────────────────────────────────

def merge_signals(
    rule_signals:  list[RuleSignal],
    graph_signals: list[RuleSignal],
) -> dict[str, list[RuleSignal]]:
    """
    Merge rule and graph signals into a dict keyed by account_id.

    This makes it easy for the scoring engine to find all signals
    for a given account without repeated filtering.

    Args:
        rule_signals:  Signals from run_all_rules() for multiple accounts.
        graph_signals: Signals from run_graph_signals().

    Returns:
        Dict mapping account_id → list of all signals for that account.
    """
    from collections import defaultdict

    result: dict[str, list[RuleSignal]] = defaultdict(list)

    for sig in rule_signals + graph_signals:
        result[sig.account_id].append(sig)

    return dict(result)
