"""
backend/utils/logging_utils.py
─────────────────────────────────────────────────────────────────────────────
Centralised logging configuration for the AML backend.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import logging
import sys
import os

LOG_FORMAT = '%(asctime)s | %(name)-40s | %(levelname)-8s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def _get_log_level() -> int:
    level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
    level = logging.getLevelName(level_name)
    return level if isinstance(level, int) else logging.INFO


def configure_logging() -> None:
    """Configure the root logger once at application startup."""
    root_logger = logging.getLogger()
    root_logger.setLevel(_get_log_level())

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Suppress noisy library loggers
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module. Always call as get_logger(__name__).

    Args:
        name: Module name (__name__) — appears in every log line.

    Returns:
        Logger instance that inherits from root logger configuration.
    """
    return logging.getLogger(name)


def get_audit_logger() -> logging.Logger:
    """
    Get the audit logger for regulatory-significant events.

    Audit logs cover dispositions, exports, and SAR-relevant decisions.
    They can be separately filtered with: grep "aml.audit" app.log

    Returns:
        Logger named 'aml.audit'.
    """
    return logging.getLogger('aml.audit')


def log_detection_result(
    logger:     logging.Logger,
    account_id: str,
    score:      float,
    tier:       str,
    n_signals:  int,
) -> None:
    """
    Log a detection result in structured, grep-friendly format.

    Args:
        logger:     Module logger from get_logger(__name__).
        account_id: Account that was scored.
        score:      Final risk score 0–100.
        tier:       Risk tier string (low/medium/high/critical).
        n_signals:  Number of rule signals that fired.
    """
    level = logging.WARNING if score >= 70 else logging.INFO
    logger.log(
        level,
        "detection | account=%s | score=%.1f | tier=%s | signals=%d",
        account_id, score, tier, n_signals,
    )


def log_rule_error(
    logger:     logging.Logger,
    rule_name:  str,
    account_id: str,
    exc:        Exception,
) -> None:
    """
    Log a rule engine failure with full stack trace.

    Args:
        logger:     Calling module's logger.
        rule_name:  Name of the rule that failed.
        account_id: Account being processed when the error occurred.
        exc:        The exception that was raised.
    """
    logger.error(
        "rule_error | rule=%s | account=%s | error=%s",
        rule_name, account_id, str(exc),
        exc_info=True,
    )
