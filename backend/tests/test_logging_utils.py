"""
backend/tests/test_logging_utils.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for backend/utils/logging_utils.py
─────────────────────────────────────────────────────────────────────────────
"""

import logging
import pytest
from backend.utils.logging_utils import (
    get_logger,
    get_audit_logger,
    configure_logging,
    log_detection_result,
    log_rule_error,
)


class TestGetLogger:

    def test_returns_logger_instance(self):
        logger = get_logger('test.module')
        assert isinstance(logger, logging.Logger)

    def test_logger_name_matches(self):
        logger = get_logger('backend.detection.rules')
        assert logger.name == 'backend.detection.rules'

    def test_same_name_returns_same_instance(self):
        """logging.getLogger() is idempotent."""
        a = get_logger('same.name')
        b = get_logger('same.name')
        assert a is b


class TestGetAuditLogger:

    def test_returns_audit_logger(self):
        logger = get_audit_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'aml.audit'


class TestConfigureLogging:

    def test_does_not_crash(self):
        """configure_logging() should run without errors."""
        configure_logging()

    def test_idempotent(self):
        """Calling configure_logging() twice should not add duplicate handlers."""
        configure_logging()
        root = logging.getLogger()
        handler_count_after_first = len(root.handlers)
        configure_logging()
        # Handler count should not have increased
        assert len(root.handlers) == handler_count_after_first


class TestLogDetectionResult:

    def test_does_not_raise(self):
        """log_detection_result should not raise for any input."""
        logger = get_logger('test')
        log_detection_result(logger, 'ACC_001', 75.0, 'high', 3)

    def test_high_score_uses_warning_level(self, caplog):
        """Score >= 70 should log at WARNING level."""
        logger = get_logger('test.detection')
        with caplog.at_level(logging.WARNING, logger='test.detection'):
            log_detection_result(logger, 'ACC_999', 85.0, 'critical', 5)
        assert any(r.levelname == 'WARNING' for r in caplog.records)


class TestLogRuleError:

    def test_does_not_raise(self):
        """log_rule_error should not raise."""
        logger = get_logger('test')
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            log_rule_error(logger, 'structuring_rule', 'ACC_001', e)
