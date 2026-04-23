"""
backend/tests/test_accounts_generator.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the synthetic account generator.

Tests verify:
  - Correct total account count
  - Correct dirty/benign ratio
  - All typologies are present
  - Account IDs are unique
  - Accounts have required fields
  - Seed produces reproducible results
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.generator.accounts import generate_accounts, generate_account_id


class TestGenerateAccountId:

    def test_format(self):
        """Account ID should be formatted as ACC_NNNNNN."""
        assert generate_account_id(1)    == "ACC_000001"
        assert generate_account_id(42)   == "ACC_000042"
        assert generate_account_id(5000) == "ACC_005000"

    def test_sortable(self):
        """IDs should sort correctly as strings (zero-padded)."""
        ids = [generate_account_id(i) for i in [1, 10, 100, 1000]]
        assert ids == sorted(ids), "IDs should sort in numerical order"


class TestGenerateAccounts:

    def setup_method(self):
        """Generate accounts once for all tests in this class."""
        self.accounts, self.typology_map = generate_accounts(total_accounts=1000, seed=42)

    def test_total_count(self):
        """Total accounts should match requested count."""
        assert len(self.accounts) == 1000

    def test_dirty_fraction(self):
        """Approximately 10% of accounts should be marked suspicious."""
        dirty_count = sum(1 for a in self.accounts if a["is_suspicious"])
        dirty_fraction = dirty_count / len(self.accounts)
        # Allow ±2% tolerance for rounding
        assert 0.08 <= dirty_fraction <= 0.12, f"Dirty fraction {dirty_fraction:.2%} out of expected range"

    def test_all_typologies_present(self):
        """All 6 typologies + benign should be in the typology_map."""
        expected = {"structuring", "layering", "funnel", "round_trip", "shell_company", "velocity", "benign"}
        assert set(self.typology_map.keys()) == expected

    def test_unique_account_ids(self):
        """All account IDs must be unique."""
        ids = [a["account_id"] for a in self.accounts]
        assert len(ids) == len(set(ids)), "Duplicate account IDs found!"

    def test_required_fields_present(self):
        """Every account must have all required fields."""
        required_fields = {
            "account_id", "holder_name", "account_type",
            "branch", "opened_date", "balance",
            "is_suspicious", "typology",
        }
        for account in self.accounts:
            missing = required_fields - set(account.keys())
            assert not missing, f"Account {account.get('account_id')} missing fields: {missing}"

    def test_reproducibility_with_same_seed(self):
        """Same seed should always produce same accounts."""
        accounts_2, _ = generate_accounts(total_accounts=1000, seed=42)
        ids_1 = {a["account_id"] for a in self.accounts}
        ids_2 = {a["account_id"] for a in accounts_2}
        assert ids_1 == ids_2, "Same seed should produce same account IDs"

    def test_different_seeds_produce_different_results(self):
        """Different seeds should produce different account data."""
        accounts_99, _ = generate_accounts(total_accounts=1000, seed=99)
        # The names should differ (same IDs but different Faker-generated names)
        names_42 = {a["holder_name"] for a in self.accounts}
        names_99 = {a["holder_name"] for a in accounts_99}
        # Very unlikely to be identical with different seeds
        assert names_42 != names_99, "Different seeds should produce different names"

    def test_typology_map_matches_accounts(self):
        """typology_map should contain all dirty account IDs."""
        all_dirty_ids = {a["account_id"] for a in self.accounts if a["is_suspicious"]}
        mapped_dirty_ids = set()
        for typology, ids in self.typology_map.items():
            if typology != "benign":
                mapped_dirty_ids.update(ids)
        assert all_dirty_ids == mapped_dirty_ids, "Typology map doesn't match account records"
