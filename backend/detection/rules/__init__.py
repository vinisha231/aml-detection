"""
backend/detection/rules/__init__.py
─────────────────────────────────────
The rules package — 5 detection rules, each in its own file.

How rules work:
  Each rule is a function that takes account data and transactions,
  and returns a list of Signal objects (or an empty list if nothing found).

  Signal = {
    account_id:  which account is suspicious,
    signal_type: which rule fired,
    score:       how suspicious (0-100),
    weight:      importance of this rule in final score,
    evidence:    human-readable explanation,
    confidence:  0.0 to 1.0
  }
"""

from .structuring_rule  import check_structuring
from .velocity_rule     import check_velocity
from .funnel_rule       import check_funnel
from .dormant_rule      import check_dormant_wakeup
from .round_number_rule import check_round_numbers
