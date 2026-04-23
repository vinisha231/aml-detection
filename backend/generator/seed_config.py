"""
backend/generator/seed_config.py
─────────────────────────────────────────────────────────────────────────────
Centralized seed and simulation parameters for data generation.

Keeping these in one place ensures:
  1. Reproducibility: the same seed always produces the same data
  2. Easy experimentation: change one file to try different scenarios
  3. Documentation: why did we choose these parameters?
─────────────────────────────────────────────────────────────────────────────
"""

# Random seed used for all data generation.
# Using a fixed seed means every run produces exactly the same accounts
# and transactions — important for evaluation and debugging.
# Change this to generate a different dataset.
DEFAULT_SEED = 42

# Total number of accounts in the simulation.
# 5,000 is large enough to be realistic but small enough to generate quickly.
# For a "production scale" demo, increase to 50,000+.
TOTAL_ACCOUNTS = 5_000

# What fraction of accounts are "dirty" (involved in money laundering).
# 10% is optimistic vs. real banks (which see 0.1% or less).
# We use 10% to have enough examples to evaluate detection meaningfully.
DIRTY_FRACTION = 0.10

# Simulation time period.
# One year of transactions gives enough history for all detection rules.
SIMULATION_START = "2024-01-01"
SIMULATION_END   = "2024-12-31"

# Distribution of accounts across typologies (must sum to 1.0)
# Shell company gets a larger fraction because each "cluster" needs 3-6 accounts.
TYPOLOGY_DISTRIBUTION = {
    "structuring":   0.20,
    "layering":      0.20,
    "funnel":        0.15,
    "round_trip":    0.15,
    "shell_company": 0.20,
    "velocity":      0.10,
}

# Benign transaction target: approximately this many benign txs per account.
# This sets the noise level — higher ratio = harder detection problem.
BENIGN_TX_PER_ACCOUNT_PER_YEAR = 200   # realistic: salary + rent + groceries + utilities
