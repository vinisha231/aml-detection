"""
backend/tests/test_scoring_engine.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the weighted scoring engine.

Tests verify:
  - Basic weighted average formula is correct
  - Pile-up bonus applies for 3+ signals
  - Score is capped at 100
  - Score is 0 for empty signals
  - Single signal: score equals that signal's weighted contribution
  - get_risk_tier() classifies correctly
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.detection.rules.base_rule import RuleSignal
from backend.detection.scoring import compute_account_score, get_risk_tier


def make_signal(
    signal_type: str,
    score: float,
    weight: float = 1.0,
    confidence: float = 1.0,
) -> RuleSignal:
    return RuleSignal(
        account_id  = 'TEST_ACC',
        signal_type = signal_type,
        score       = score,
        weight      = weight,
        evidence    = 'test',
        confidence  = confidence,
    )


class TestComputeAccountScore:

    def test_single_signal_returns_its_score(self):
        """Single signal with confidence=1 should return exactly that score."""
        signals = [make_signal('structuring', 80.0, weight=1.0, confidence=1.0)]
        result  = compute_account_score('TEST_ACC', signals)
        assert abs(result.final_score - 80.0) < 0.5

    def test_empty_signals_returns_zero(self):
        """No signals → score 0."""
        result = compute_account_score('TEST_ACC', [])
        assert result.final_score == 0.0

    def test_weighted_average_formula(self):
        """
        Manual calculation:
          signal_a: score=80, weight=2.0, confidence=1.0 → contribution = 80 * 2.0 * 1.0 = 160
          signal_b: score=40, weight=1.0, confidence=1.0 → contribution = 40 * 1.0 * 1.0 = 40
          weighted_sum = 160 + 40 = 200
          weight_sum   = 2.0 * 1.0 + 1.0 * 1.0 = 3.0
          base_score   = 200 / 3.0 ≈ 66.67
        """
        signals = [
            make_signal('structuring', 80.0, weight=2.0, confidence=1.0),
            make_signal('velocity',    40.0, weight=1.0, confidence=1.0),
        ]
        result = compute_account_score('TEST_ACC', signals)
        expected = (80 * 2.0 + 40 * 1.0) / (2.0 + 1.0)
        assert abs(result.final_score - expected) < 1.0  # within 1 point

    def test_pile_up_bonus_for_3_signals(self):
        """3 signals → pile-up bonus applied → score higher than 2 signals."""
        two_sigs   = [make_signal('a', 60.0), make_signal('b', 60.0)]
        three_sigs = [make_signal('a', 60.0), make_signal('b', 60.0), make_signal('c', 60.0)]

        score_two   = compute_account_score('TEST', two_sigs).final_score
        score_three = compute_account_score('TEST', three_sigs).final_score

        assert score_three > score_two, "3 signals should score higher due to pile-up bonus"

    def test_score_capped_at_100(self):
        """Score cannot exceed 100 even with very high input signals."""
        signals = [make_signal(f'sig_{i}', 100.0, weight=2.0) for i in range(10)]
        result = compute_account_score('TEST_ACC', signals)
        assert result.final_score <= 100.0

    def test_score_non_negative(self):
        """Score should never be negative."""
        signals = [make_signal('low_signal', 0.0, weight=0.5, confidence=0.1)]
        result = compute_account_score('TEST_ACC', signals)
        assert result.final_score >= 0.0

    def test_confidence_scales_contribution(self):
        """Low-confidence signal should contribute less than high-confidence signal."""
        high_conf = compute_account_score('TEST', [make_signal('a', 80.0, confidence=1.0)])
        low_conf  = compute_account_score('TEST', [make_signal('a', 80.0, confidence=0.3)])
        assert high_conf.final_score > low_conf.final_score


class TestGetRiskTier:

    def test_critical_tier(self):
        assert get_risk_tier(90.0) == 'critical'
        assert get_risk_tier(99.9) == 'critical'

    def test_high_tier(self):
        assert get_risk_tier(70.0) == 'high'
        assert get_risk_tier(89.9) == 'high'

    def test_medium_tier(self):
        assert get_risk_tier(40.0) == 'medium'
        assert get_risk_tier(69.9) == 'medium'

    def test_low_tier(self):
        assert get_risk_tier(0.0)  == 'low'
        assert get_risk_tier(39.9) == 'low'
