"""
backend/tests/test_amount_utils_extra.py
─────────────────────────────────────────────────────────────────────────────
Additional edge-case tests for amount_utils — boundary values and
the is_just_below_threshold helper.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.utils.amount_utils import (
    is_just_below_threshold,
    roundness_score,
    amount_z_score,
)


class TestIsJustBelowThreshold:

    def test_exactly_at_threshold_not_below(self):
        """Exactly at the threshold itself is not 'just below'."""
        assert is_just_below_threshold(10_000.0, threshold=10_000.0) is False

    def test_within_margin_is_flagged(self):
        """$9,600 is within $400 of $10,000 (margin=500) — flagged."""
        assert is_just_below_threshold(9_600.0, threshold=10_000.0, margin=500) is True

    def test_outside_margin_not_flagged(self):
        """$8,000 is $2,000 below threshold — outside the $500 margin."""
        assert is_just_below_threshold(8_000.0, threshold=10_000.0, margin=500) is False

    def test_sar_threshold(self):
        """Test against the $5,000 SAR threshold."""
        assert is_just_below_threshold(4_800.0, threshold=5_000.0, margin=300) is True
        assert is_just_below_threshold(4_600.0, threshold=5_000.0, margin=300) is False


class TestRoundnessScoreEdgeCases:

    def test_exactly_10000_is_max_round(self):
        assert roundness_score(10_000.0) == 1.0

    def test_25000_is_max_round(self):
        assert roundness_score(25_000.0) == 1.0

    def test_99999_not_round(self):
        assert roundness_score(99_999.0) == 0.0

    def test_negative_not_round(self):
        assert roundness_score(-500.0) == 0.0


class TestAmountZScoreEdgeCases:

    def test_one_item_returns_none(self):
        assert amount_z_score(1_000.0, [500.0]) is None

    def test_exactly_at_mean_z_is_zero(self):
        amounts = [100.0, 200.0, 300.0]  # mean = 200
        z = amount_z_score(200.0, amounts)
        assert z == pytest.approx(0.0, abs=1e-6)

    def test_negative_amount_below_mean(self):
        amounts = [100.0, 200.0, 300.0]
        z = amount_z_score(50.0, amounts)
        assert z < 0  # 50 is below the mean of 200
