"""
backend/database/seed.py
─────────────────────────────────────────────────────────────────────────────
Database seeder — inserts the minimum data needed for the system to work.

What is seeding?
  Seeding is the process of inserting initial/default data into the database.
  Unlike migrations (which change the schema), seeding adds ROWS.

  Examples:
    - System accounts (ACC_BANK_SOURCE, ACC_PAYROLL) — needed by the generator
    - Default configuration values
    - Demo data for development

  Seeding is idempotent: running it twice produces the same result as once.
  We check if records already exist before inserting.

System Accounts:
  The synthetic data generator sends money FROM these accounts to simulate
  real-world flows:
    ACC_BANK_SOURCE — large bank; sends structured deposits
    ACC_PAYROLL     — payroll processor; sends salary payments
    ACC_LANDLORD    — property management; receives rent
    ACC_RETAIL      — retail store; receives purchase payments
    ACC_UTILITY     — utility company; receives bill payments
─────────────────────────────────────────────────────────────────────────────
"""

from sqlalchemy.orm import Session
from backend.database.schema import Account

# ─── System accounts ──────────────────────────────────────────────────────────

SYSTEM_ACCOUNTS = [
    {
        'account_id':   'ACC_BANK_SOURCE',
        'holder_name':  'Federal Reserve Bank (Simulated)',
        'account_type': 'BANK',
        'branch':       'FED_RESERVE',
        'balance':      999_999_999.99,
        'is_suspicious': False,
        'typology':     None,
    },
    {
        'account_id':   'ACC_PAYROLL',
        'holder_name':  'National Payroll Processing Corp',
        'account_type': 'CORPORATE',
        'branch':       'NYC_MAIN',
        'balance':      10_000_000.00,
        'is_suspicious': False,
        'typology':     None,
    },
    {
        'account_id':   'ACC_LANDLORD',
        'holder_name':  'Metropolitan Property Management LLC',
        'account_type': 'BUSINESS',
        'branch':       'CHI_MAIN',
        'balance':      5_000_000.00,
        'is_suspicious': False,
        'typology':     None,
    },
    {
        'account_id':   'ACC_RETAIL',
        'holder_name':  'General Retail Holdings Inc.',
        'account_type': 'CORPORATE',
        'branch':       'LAX_MAIN',
        'balance':      2_500_000.00,
        'is_suspicious': False,
        'typology':     None,
    },
    {
        'account_id':   'ACC_UTILITY',
        'holder_name':  'National Utility Services Corp',
        'account_type': 'CORPORATE',
        'branch':       'HOU_MAIN',
        'balance':      1_000_000.00,
        'is_suspicious': False,
        'typology':     None,
    },
]


def seed_system_accounts(session: Session) -> int:
    """
    Insert system accounts if they don't already exist.

    Args:
        session: An active SQLAlchemy session.

    Returns:
        Number of accounts inserted (0 if all already existed).
    """
    inserted = 0

    for account_data in SYSTEM_ACCOUNTS:
        existing = (
            session.query(Account)
            .filter(Account.account_id == account_data['account_id'])
            .first()
        )

        if existing is None:
            account = Account(**account_data)
            session.add(account)
            inserted += 1

    if inserted > 0:
        session.commit()

    return inserted


def seed_all(session: Session) -> dict:
    """
    Run all seed operations and return a summary.

    Args:
        session: An active SQLAlchemy session.

    Returns:
        Dict with counts of each entity type inserted.
    """
    return {
        'system_accounts': seed_system_accounts(session),
    }
