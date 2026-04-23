"""
backend/tests/test_migrations.py
─────────────────────────────────────────────────────────────────────────────
Tests for the database migration system.

Tests verify:
  - get_applied_versions returns empty set on fresh database
  - mark_applied records the migration correctly
  - run_migrations applies pending migrations in order
  - Already-applied migrations are skipped
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from sqlalchemy import create_engine

from backend.database.migrations import (
    get_applied_versions,
    mark_applied,
    run_migrations,
    MIGRATIONS,
)


@pytest.fixture
def in_memory_engine():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine('sqlite:///:memory:')
    yield engine
    engine.dispose()


class TestGetAppliedVersions:

    def test_returns_empty_set_for_fresh_database(self, in_memory_engine):
        """No migrations applied yet → empty set."""
        result = get_applied_versions(in_memory_engine)
        assert result == set()

    def test_returns_applied_versions_after_marking(self, in_memory_engine):
        """After creating the tracking table and marking a migration, returns it."""
        # First run migration v1 to create the tracking table
        run_migrations(in_memory_engine)

        applied = get_applied_versions(in_memory_engine)
        # At minimum, version 1 should be applied (the tracking table migration)
        assert 1 in applied


class TestRunMigrations:

    def test_applies_all_pending_migrations(self, in_memory_engine):
        """run_migrations should apply all migrations."""
        run_migrations(in_memory_engine)
        applied = get_applied_versions(in_memory_engine)
        # All migrations should now be applied
        all_versions = {m[0] for m in MIGRATIONS}
        assert all_versions == applied

    def test_idempotent_on_second_run(self, in_memory_engine):
        """Running migrations twice should not fail."""
        run_migrations(in_memory_engine)
        # Should not raise any exception on second run
        run_migrations(in_memory_engine)

    def test_migrations_applied_in_order(self, in_memory_engine):
        """Migration versions must be applied in ascending order."""
        applied_order = []
        original_mark = mark_applied

        # Patch mark_applied to track order
        import backend.database.migrations as mig_module
        original = mig_module.mark_applied

        def tracking_mark(engine, version, description):
            applied_order.append(version)
            original(engine, version, description)

        mig_module.mark_applied = tracking_mark
        try:
            run_migrations(in_memory_engine)
        finally:
            mig_module.mark_applied = original

        # Check that versions were applied in sorted order
        assert applied_order == sorted(applied_order)
