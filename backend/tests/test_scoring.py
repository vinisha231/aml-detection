"""
backend/tests/test_scoring.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the unified scoring engine.

Tests cover:
- Empty signals → score 0
- Single signal → score equals signal score × confidence
- Multiple signals → weighted average with pile-up bonus
- Score capped at 100
- Evidence string format
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.detection.rules.structuring_rule import RuleSignal
from backend.detection.scoring import compute_account_score, get_risk_tier, score_all_accounts


def make_signal(signal_type: str, score: float, weight: float, confidence: float) -> RuleSignal:
    """Helper: create a RuleSignal for testing."""
    return RuleSignal(
        account_id="ACC_TEST",
        signal_type=signal_type,
        score=score,
        weight=weight,
        evidence=f"Test evidence for {signal_type}",
        confidence=confidence,
    )


class TestComputeAccountScore:

    def test_empty_signals_returns_zero(self):
        """No signals → risk score should be 0."""
        result = compute_account_score("ACC_TEST", [])
        assert result.risk_score == 0.0
        assert result.signals_fired == []
        assert result.top_signal is None

    def test_single_signal_score(self):
        """One signal: score should be approximately signal.score × confidence."""
        signal = make_signal("structuring_rule", score=80.0, weight=1.0, confidence=1.0)
        result = compute_account_score("ACC_TEST", [signal])
        # With weight=1, confidence=1: weighted average = 80 * 1.0 * 1.0 / 1.0 = 80
        assert abs(result.risk_score - 80.0) < 2.0, f"Expected ~80, got {result.risk_score}"

    def test_score_capped_at_100(self):
        """Score should never exceed 100 regardless of signal values."""
        signals = [
            make_signal("structuring_rule",  score=100.0, weight=5.0, confidence=1.0),
            make_signal("velocity_rule",      score=100.0, weight=5.0, confidence=1.0),
            make_signal("funnel_rule",        score=100.0, weight=5.0, confidence=1.0),
        ]
        result = compute_account_score("ACC_TEST", signals)
        assert result.risk_score <= 100.0, f"Score {result.risk_score} exceeded 100"

    def test_multiple_signals_pile_up(self):
        """3+ signals should score higher than a single signal with same score."""
        single = [make_signal("structuring_rule", score=60.0, weight=1.0, confidence=1.0)]
        multi  = [
            make_signal("structuring_rule", score=60.0, weight=1.0, confidence=1.0),
            make_signal("velocity_rule",    score=60.0, weight=1.0, confidence=1.0),
            make_signal("funnel_rule",      score=60.0, weight=1.0, confidence=1.0),
        ]

        single_result = compute_account_score("ACC_A", single)
        multi_result  = compute_account_score("ACC_B", multi)

        assert multi_result.risk_score > single_result.risk_score, (
            f"Multi-signal ({multi_result.risk_score}) should beat single ({single_result.risk_score})"
        )

    def test_signals_fired_contains_unique_types(self):
        """signals_fired should list unique signal types (no duplicates)."""
        signals = [
            make_signal("structuring_rule", score=70.0, weight=1.0, confidence=0.8),
            make_signal("structuring_rule", score=60.0, weight=1.0, confidence=0.7),  # duplicate type
            make_signal("velocity_rule",    score=50.0, weight=1.0, confidence=0.6),
        ]
        result = compute_account_score("ACC_TEST", signals)
        assert len(result.signals_fired) == len(set(result.signals_fired)), "Duplicates in signals_fired"

    def test_top_signal_is_highest_scorer(self):
        """top_signal should be the signal type with the highest weighted score."""
        signals = [
            make_signal("velocity_rule",    score=40.0, weight=1.0, confidence=0.9),
            make_signal("structuring_rule", score=90.0, weight=1.0, confidence=0.9),  # highest
        ]
        result = compute_account_score("ACC_TEST", signals)
        assert result.top_signal == "structuring_rule", f"Expected structuring_rule, got {result.top_signal}"

    def test_evidence_contains_all_signals(self):
        """Evidence string should mention each signal type."""
        signals = [
            make_signal("structuring_rule", score=70.0, weight=1.0, confidence=0.8),
            make_signal("velocity_rule",    score=60.0, weight=1.0, confidence=0.7),
        ]
        result = compute_account_score("ACC_TEST", signals)
        # Evidence should contain BOTH signal type labels
        assert "STRUCTURING" in result.evidence.upper()
        assert "VELOCITY" in result.evidence.upper()

    def test_confidence_scales_score_down(self):
        """Lower confidence should produce a lower final score."""
        high_conf = [make_signal("structuring_rule", score=80.0, weight=1.0, confidence=1.0)]
        low_conf  = [make_signal("structuring_rule", score=80.0, weight=1.0, confidence=0.3)]

        high_result = compute_account_score("ACC_HIGH", high_conf)
        low_result  = compute_account_score("ACC_LOW",  low_conf)

        assert high_result.risk_score > low_result.risk_score, (
            "Higher confidence should produce higher score for same raw score"
        )


class TestGetRiskTier:

    def test_critical_tier(self):
        assert get_risk_tier(80.0) == "critical"
        assert get_risk_tier(75.0) == "critical"
        assert get_risk_tier(100.0) == "critical"

    def test_high_tier(self):
        assert get_risk_tier(60.0) == "high"
        assert get_risk_tier(50.0) == "high"
        assert get_risk_tier(74.9) == "high"

    def test_medium_tier(self):
        assert get_risk_tier(40.0) == "medium"
        assert get_risk_tier(25.0) == "medium"

    def test_low_tier(self):
        assert get_risk_tier(10.0) == "low"
        assert get_risk_tier(0.0)  == "low"
        assert get_risk_tier(24.9) == "low"


class TestScoreAllAccounts:

    def test_scores_multiple_accounts(self):
        """score_all_accounts should return a result for every account in input."""
        all_signals = {
            "ACC_001": [make_signal("structuring_rule", 70.0, 1.0, 0.8)],
            "ACC_002": [make_signal("velocity_rule",    50.0, 1.0, 0.7)],
            "ACC_003": [],
        }
        results = score_all_accounts(all_signals)
        assert "ACC_001" in results
        assert "ACC_002" in results
        assert "ACC_003" in results
        assert results["ACC_003"].risk_score == 0.0
