"""
backend/database/__init__.py
────────────────────────────
Makes the database folder a Python package.
Imports the most commonly used items so other modules can do:
    from backend.database import get_engine, Account, Transaction
instead of the longer path.
"""

from .schema import (
    Base,
    Account,
    Transaction,
    Signal,
    Disposition,
    get_engine,
    create_all_tables,
    get_session_factory,
)
