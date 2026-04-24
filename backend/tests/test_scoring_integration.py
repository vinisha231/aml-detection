"""
backend/tests/test_scoring_integration.py
─────────────────────────────────────────────────────────────────────────────
Integration tests for the full scoring pipeline:
  Rule signals → merge_signals → score_account → ValidationResult

Tests the end-to-end flow with realistic signal combinations.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.detection.rules.base_rule import RuleSignal
from backend.detection.scoring import score_account, ScoreResult


def make_signal(
    account_id:  str,
    signal_type: str,
    score:       float,
    weight:      float = 1.0,
    confidence:  float = 0.75,
) -> RuleSignal:
    return RuleSignal(
        account_id  = account_id,
        signal_type = signal_type,
        score       = score,
        weight      = weight,
        evidence    = f"Test evidence for {signal_type}",
        confidence  = confidence,
    )


class TestScoreAccountIntegration:

    def test_no_signals_gives_zero_score(self):
        result = score_account('ACC_CLEAN', [])
        assert result.final_score == 0.0
        assert result.risk_tier == 'low'

    def test_single_high_signal(self):
        signals = [make_signal('ACC_001', 'structuring', 85.0, weight=2.0, confidence=0.90)]
        result  = score_account('ACC_001', signals)
        assert result.final_score > 0
        assert result.risk_tier in ('high', 'critical')

    def test_multiple_signals_pile_up_bonus(self):
        """Three signals should trigger the pile-up bonus, increasing the score."""
        signals = [
            make_signal('ACC_002', 'structuring',   70.0, weight=2.0),
            make_signal('ACC_002', 'velocity',      65.0, weight=1.5),
            make_signal('ACC_002', 'graph_pagerank', 60.0, weight=1.2),
        ]
        result_multi = score_account('ACC_002', signals)

        # Score with 3 signals should exceed what any single signal gives alone
        result_single = score_account('ACC_002', signals[:1])
        assert result_multi.final_score >= result_single.final_score

    def test_score_clamped_to_100(self):
        """Final score must never exceed 100."""
        signals = [
            make_signal('ACC_003', f'signal_{i}', 99.0, weight=3.0, confidence=1.0)
            for i in range(10)
        ]
        result = score_account('ACC_003', signals)
        assert result.final_score <= 100.0

    def test_score_result_has_account_id(self):
        signals = [make_signal('ACC_XYZ', 'structuring', 75.0)]
        result  = score_account('ACC_XYZ', signals)
        assert result.account_id == 'ACC_XYZ'

    def test_risk_tier_thresholds(self):
        """Test that tier assignment matches the expected thresholds."""
        low_result  = score_account('A', [make_signal('A', 'x', 20.0)])
        med_result  = score_account('B', [make_signal('B', 'x', 55.0, weight=2.0)])

        assert low_result.risk_tier  in ('low', 'medium')
        assert med_result.risk_tier  in ('medium', 'high')
