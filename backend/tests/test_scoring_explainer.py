"""
backend/tests/test_scoring_explainer.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the scoring explainer module.

Tests verify:
  - Empty signals produce a sensible explanation
  - Primary driver is the highest-contribution signal
  - Multi-signal convergence note appears for 3+ signals
  - format_signal_summary returns a non-empty string
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from backend.detection.rules.base_rule import RuleSignal
from backend.detection.scoring_explainer import generate_explanation, format_signal_summary


def make_sig(signal_type: str, score: float, weight: float = 1.0, confidence: float = 0.9) -> RuleSignal:
    return RuleSignal(
        account_id  = 'TEST',
        signal_type = signal_type,
        score       = score,
        weight      = weight,
        evidence    = f'Evidence for {signal_type}.',
        confidence  = confidence,
    )


class TestGenerateExplanation:

    def test_empty_signals_returns_string(self):
        result = generate_explanation('ACC_001', 0.0, [])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_account_id(self):
        result = generate_explanation('ACC_XYZ', 75.0, [make_sig('structuring', 80.0)])
        assert 'ACC_XYZ' in result

    def test_contains_score(self):
        result = generate_explanation('ACC_001', 75.0, [make_sig('structuring', 80.0)])
        assert '75.0' in result

    def test_single_signal_shows_as_primary(self):
        result = generate_explanation('ACC_001', 70.0, [make_sig('graph_cycle', 85.0)])
        assert 'Primary driver' in result

    def test_three_signals_includes_convergence_note(self):
        signals = [
            make_sig('structuring', 85.0, weight=2.0),
            make_sig('velocity',    65.0, weight=1.5),
            make_sig('graph_cycle', 75.0, weight=2.0),
        ]
        result = generate_explanation('ACC_001', 78.0, signals)
        assert 'convergence' in result.lower() or '3 signal' in result.lower()

    def test_two_signals_no_convergence_note(self):
        signals = [
            make_sig('structuring', 85.0),
            make_sig('velocity',    60.0),
        ]
        result = generate_explanation('ACC_001', 72.0, signals)
        # 2 signals → no pile-up note
        assert 'convergence' not in result.lower()


class TestFormatSignalSummary:

    def test_returns_string(self):
        signals = [make_sig('structuring', 85.0), make_sig('velocity', 65.0)]
        result = format_signal_summary(signals)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_signals(self):
        result = format_signal_summary([])
        assert result == ''

    def test_sorted_by_score(self):
        signals = [make_sig('velocity', 40.0), make_sig('structuring', 90.0)]
        result = format_signal_summary(signals)
        # structuring (90) should appear before velocity (40)
        assert result.index('Structuring') < result.index('Velocity')
