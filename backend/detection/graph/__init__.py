"""
backend/detection/graph/__init__.py
────────────────────────────────────
Graph signal detection using NetworkX.

The graph approach treats all accounts as nodes and all transactions as edges.
This reveals patterns that are invisible when looking at accounts individually.

Signals provided:
  - builder.py:          Builds the NetworkX DiGraph from transactions
  - pagerank_signal.py:  Detects funnel accounts (high centrality)
  - community_signal.py: Detects shell company clusters (isolation)
  - cycle_signal.py:     Detects round-tripping (graph cycles)
  - chain_signal.py:     Detects layering (high-value directed chains)
"""

from .builder        import build_transaction_graph
from .pagerank_signal   import compute_pagerank_signals
from .community_signal  import compute_community_signals
from .cycle_signal      import compute_cycle_signals
from .chain_signal      import compute_chain_signals
