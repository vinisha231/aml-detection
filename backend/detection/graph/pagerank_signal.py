"""
backend/detection/graph/pagerank_signal.py
─────────────────────────────────────────────────────────────────────────────
Computes PageRank-based AML signals for all accounts.

PageRank background (see read/04_graph_theory_basics.md for full explanation):
  PageRank was invented by Google to rank web pages.
  For AML: a "central" account (many others send to it) gets a high PageRank.
  Funnel accounts always appear in the top percentiles of PageRank.

How we score it:
  We convert raw PageRank values to percentile ranks (0-100).
  An account in the 99th percentile gets score ~90.
  An account in the 80th percentile gets score ~40.
  Below the 90th percentile: not flagged.
─────────────────────────────────────────────────────────────────────────────
"""

import networkx as nx
from typing import List

from ..rules.structuring_rule import RuleSignal


# Score only accounts above this PageRank percentile
PAGERANK_PERCENTILE_THRESHOLD = 90  # top 10%

SIGNAL_WEIGHT = 1.5


def compute_pagerank_signals(
    G: nx.DiGraph,
    top_percentile: float = PAGERANK_PERCENTILE_THRESHOLD,
) -> List[RuleSignal]:
    """
    Compute PageRank for all accounts and flag high-centrality accounts.

    Args:
        G:               The full transaction graph (from builder.py)
        top_percentile:  Only flag accounts above this percentile (default: top 10%)

    Returns:
        List of RuleSignal objects for flagged accounts.
        Only includes accounts in the top percentile.
    """

    if G.number_of_nodes() == 0:
        return []

    # ── Compute PageRank ──────────────────────────────────────────────────────
    # alpha=0.85 is the standard "damping factor"
    # weight='weight' means larger money flows count more than small ones
    # max_iter=100 is sufficient for convergence in most graphs
    pageranks = nx.pagerank(G, alpha=0.85, weight="weight", max_iter=100)

    # ── Convert to percentile ranks ───────────────────────────────────────────
    # Sort all accounts by PageRank value
    sorted_accounts = sorted(pageranks.items(), key=lambda x: x[1])
    total_accounts  = len(sorted_accounts)

    # Map each account to its percentile (0 = lowest, 100 = highest)
    percentile_rank = {}
    for rank_position, (account_id, pr_score) in enumerate(sorted_accounts):
        # rank_position 0 = lowest PageRank, (total-1) = highest
        percentile = (rank_position / (total_accounts - 1)) * 100 if total_accounts > 1 else 50
        percentile_rank[account_id] = (percentile, pr_score)

    # ── Generate signals for high-percentile accounts ─────────────────────────
    signals = []

    for account_id, (percentile, pr_score) in percentile_rank.items():

        # Skip accounts below the threshold
        if percentile < top_percentile:
            continue

        # Skip special system accounts (bank, payroll, utilities)
        if account_id.startswith("ACC_") and not account_id[4:].isdigit():
            continue  # skip ACC_BANK_SOURCE, ACC_PAYROLL, etc.

        # ── Score formula ─────────────────────────────────────────────────────
        # percentile 90 → score 20
        # percentile 95 → score 55
        # percentile 99 → score 85
        score = (percentile - top_percentile) / (100 - top_percentile) * 90.0
        score = min(90.0, score)

        # ── Graph metrics for evidence ─────────────────────────────────────────
        in_degree  = G.in_degree(account_id)   # number of senders
        out_degree = G.out_degree(account_id)  # number of receivers

        # Total money received
        total_received = sum(
            data.get("weight", 0)
            for _, _, data in G.in_edges(account_id, data=True)
        )

        confidence = min(0.85, 0.45 + percentile * 0.004)

        evidence = (
            f"PageRank: {pr_score:.5f} (top {100 - percentile:.1f}% of all accounts). "
            f"In-degree: {in_degree} senders → ${total_received:,.0f} received. "
            f"Out-degree: {out_degree} receivers."
        )

        signals.append(RuleSignal(
            account_id=account_id,
            signal_type="graph_pagerank",
            score=round(score, 1),
            weight=SIGNAL_WEIGHT,
            evidence=evidence,
            confidence=round(confidence, 2),
        ))

    return signals
