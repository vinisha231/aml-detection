"""
backend/generator/__init__.py
─────────────────────────────
Makes the generator folder a Python package.
The generator is responsible for creating ALL synthetic data.
"""

from .accounts import generate_accounts
from .transactions import generate_transaction_id
from .benign import generate_benign_transactions
