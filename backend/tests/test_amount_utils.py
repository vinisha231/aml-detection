"""
backend/tests/test_amount_utils.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for backend/utils/amount_utils.py
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.utils.amount_utils import (
    is_in_structuring_zone,
    is_just_below_threshold,
    roundness_score,
    amount_z_score,
    total_volume,
    largest_transaction,
)


class TestStructuringZone:

    def test_9900_in_zone(self):
        assert is_in_structuring_zone(9_900.0) is True

    def test_9500_in_zone(self):
        assert is_in_structuring_zone(9_500.0) is True

    def test_10000_not_in_zone(self):
        """Exactly at CTR threshold — not in structuring zone."""
        assert is_in_structuring_zone(10_000.0) is False

    def test_5000_not_in_zone(self):
        """Far below threshold — not in zone."""
        assert is_in_structuring_zone(5_000.0) is False

    def test_9499_not_in_zone(self):
        """Just below the zone floor."""
        assert is_in_structuring_zone(9_499.99) is False


class TestRoundnessScore:

    def test_10000_is_maximally_round(self):
        assert roundness_score(10_000.0) == 1.0

    def test_5000_is_round(self):
        assert roundness_score(5_000.0) == 0.7

    def test_500_is_somewhat_round(self):
        assert roundness_score(500.0) == 0.5

    def test_100_is_slightly_round(self):
        assert roundness_score(100.0) == 0.3

    def test_irregular_amount_not_round(self):
        assert roundness_score(9_847.23) == 0.0

    def test_zero_not_round(self):
        assert roundness_score(0.0) == 0.0


class TestAmountZScore:

    def test_z_score_above_mean(self):
        amounts = [1_000.0, 1_000.0, 1_000.0, 1_000.0]
        # An amount far above the identical baseline has Z = inf
        z = amount_z_score(50_000.0, amounts)
        assert z == float('inf')

    def test_z_score_at_mean(self):
        amounts = [100.0, 200.0, 300.0]
        mean_val = 200.0
        z = amount_z_score(mean_val, amounts)
        assert z == pytest.approx(0.0, abs=0.01)

    def test_returns_none_with_one_amount(self):
        z = amount_z_score(1_000.0, [1_000.0])
        assert z is None

    def test_high_amount_has_positive_z(self):
        amounts = [100.0, 200.0, 150.0, 120.0, 180.0]
        z = amount_z_score(10_000.0, amounts)
        assert z > 2.0


class TestVolumeHelpers:

    def test_total_volume(self):
        assert total_volume([100.0, 200.0, 300.0]) == 600.0

    def test_total_volume_empty(self):
        assert total_volume([]) == 0.0

    def test_largest_transaction(self):
        assert largest_transaction([100.0, 500.0, 200.0]) == 500.0

    def test_largest_transaction_empty(self):
        assert largest_transaction([]) == 0.0
