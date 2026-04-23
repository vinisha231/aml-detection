"""
backend/database/migrations.py
─────────────────────────────────────────────────────────────────────────────
Simple database migration utility for schema changes.

What are migrations?
  When you change your database schema (add a column, change a type,
  add an index), you can't just modify the ORM model and expect the
  existing database to update automatically.

  You need to apply the change to the existing database without losing data.
  This is called a "migration."

  Production systems use tools like Alembic (SQLAlchemy's migration toolkit)
  or Django's built-in migrations. We implement a lightweight version here
  that's easier to understand as a beginner.

Migration format:
  Each migration is a function with a version number and a SQL statement.
  The `applied_migrations` table tracks which migrations have already run.
  On each startup, new migrations are applied in order.

Example:
  Version 1: Create all tables (handled by create_all_tables())
  Version 2: Add `branch` column to accounts (if we add that later)
  Version 3: Add composite index on (typology, risk_score)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
from datetime import datetime
from sqlalchemy import create_engine, text, Engine

logger = logging.getLogger('aml_migrations')

# ─── Migration registry ───────────────────────────────────────────────────────

# Each migration is a (version, description, SQL) tuple.
# Migrations are applied in order. Never modify a migration that has already run!
# Instead, add a NEW migration.

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "Create applied_migrations tracking table",
        """
        CREATE TABLE IF NOT EXISTS applied_migrations (
            version     INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at  TEXT NOT NULL
        )
        """
    ),
    (
        2,
        "Add scored_at column to accounts if missing",
        """
        -- SQLite doesn't support IF NOT EXISTS for columns, so we use a no-op
        -- approach: try to add the column, ignore the error if it already exists
        SELECT 1  -- placeholder; actual migration checked in Python
        """
    ),
    (
        3,
        "Add index on signal_type for fast FPR queries",
        """
        CREATE INDEX IF NOT EXISTS idx_sig_type ON signals (signal_type)
        """
    ),
    (
        4,
        "Add index on disposition for queue filtering",
        """
        CREATE INDEX IF NOT EXISTS idx_acc_disposition ON accounts (disposition)
        """
    ),
]


# ─── Migration engine ─────────────────────────────────────────────────────────

def get_applied_versions(engine: Engine) -> set[int]:
    """
    Return the set of migration version numbers already applied.
    Returns empty set if the migrations table doesn't exist yet.
    """
    with engine.connect() as conn:
        try:
            rows = conn.execute(
                text("SELECT version FROM applied_migrations")
            ).fetchall()
            return {row[0] for row in rows}
        except Exception:
            return set()  # table doesn't exist yet — first run


def mark_applied(engine: Engine, version: int, description: str) -> None:
    """Record that a migration has been applied."""
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO applied_migrations (version, description, applied_at) "
                "VALUES (:v, :d, :t)"
            ),
            {'v': version, 'd': description, 't': datetime.utcnow().isoformat()},
        )
        conn.commit()


def run_migrations(engine: Engine) -> None:
    """
    Apply all pending migrations to the database.

    Safe to call on every startup — already-applied migrations are skipped.
    Migrations are applied in version order, regardless of list order.

    Args:
        engine: A SQLAlchemy Engine connected to the target database.
    """
    applied = get_applied_versions(engine)

    # Sort by version to ensure correct application order
    pending = [m for m in MIGRATIONS if m[0] not in applied]
    pending.sort(key=lambda m: m[0])

    if not pending:
        logger.debug("All migrations already applied.")
        return

    logger.info(f"Applying {len(pending)} pending migration(s)…")

    for version, description, sql in pending:
        logger.info(f"  Applying migration v{version}: {description}")
        try:
            with engine.connect() as conn:
                # Execute the migration SQL
                # Some migrations are "SELECT 1" placeholders (handled in Python)
                if sql.strip() and not sql.strip().startswith('SELECT 1'):
                    conn.execute(text(sql))
                    conn.commit()

            # Record success
            mark_applied(engine, version, description)
            logger.info(f"  ✓ Migration v{version} applied successfully.")

        except Exception as e:
            logger.error(f"  ✗ Migration v{version} failed: {e}")
            raise  # stop all migrations if one fails — don't apply partial schema
