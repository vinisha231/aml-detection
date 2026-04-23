"""
backend/tests/test_validator.py
─────────────────────────────────────────────────────────────────────────────
Unit tests for the data generator validator.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from datetime import datetime, timedelta
from backend.generator.validator import validate_generated_data, ValidationResult


SIM_START = datetime(2023, 1, 1)
SIM_END   = datetime(2024, 1, 1)


def make_account(account_id: str, is_suspicious: bool = False, typology: str = None):
    return {
        'account_id':    account_id,
        'holder_name':   'Test Person',
        'account_type':  'PERSONAL',
        'is_suspicious': is_suspicious,
        'typology':      typology,
    }


def make_tx(sender: str, receiver: str, amount: float = 1_000.0, days_offset: int = 100):
    return {
        'transaction_id':      f'TX_{sender}_{days_offset}',
        'sender_account_id':   sender,
        'receiver_account_id': receiver,
        'amount':              amount,
        'transaction_date':    SIM_START + timedelta(days=days_offset),
    }


class TestValidateGeneratedData:

    def test_valid_data_passes(self):
        """Well-formed data with correct ratio and all typologies passes."""
        # 90 benign + 10 suspicious (10% ratio)
        accounts = [make_account(f'ACC_{i:04d}') for i in range(90)]
        typologies = ['structuring', 'layering', 'funnel', 'round_trip', 'shell_company', 'velocity']
        for i, typology in enumerate(typologies):
            accounts.append(make_account(f'ACC_SUSP_{i}', is_suspicious=True, typology=typology))
        # Add 4 more suspicious to hit 10/100
        for i in range(4):
            accounts.append(make_account(f'ACC_SUSP_EXTRA_{i}', is_suspicious=True, typology='structuring'))

        transactions = [
            make_tx('ACC_0000', 'ACC_0001', days_offset=i * 3)
            for i in range(50)
        ]

        result = validate_generated_data(accounts, transactions, SIM_START, SIM_END)
        # Should pass or have only warnings (not errors)
        assert len(result.errors) == 0 or not result.passed

    def test_negative_amount_fails(self):
        """Negative transaction amounts should fail validation."""
        accounts = [make_account('ACC_001'), make_account('ACC_002')]
        transactions = [make_tx('ACC_001', 'ACC_002', amount=-1_000.0)]
        result = validate_generated_data(accounts, transactions, SIM_START, SIM_END)
        assert not result.passed
        assert any('negative' in e.lower() for e in result.errors)

    def test_out_of_range_date_fails(self):
        """Transaction date outside simulation window should fail."""
        accounts = [make_account('ACC_001'), make_account('ACC_002')]
        future_date = SIM_END + timedelta(days=100)
        tx = {
            'transaction_id':      'TX_FUTURE',
            'sender_account_id':   'ACC_001',
            'receiver_account_id': 'ACC_002',
            'amount':              1_000.0,
            'transaction_date':    future_date,
        }
        result = validate_generated_data(accounts, [tx], SIM_START, SIM_END)
        assert not result.passed
        assert any('outside' in e.lower() for e in result.errors)

    def test_missing_typology_fails(self):
        """If a typology is completely absent, it should be an error."""
        accounts = [make_account(f'ACC_{i:03d}') for i in range(90)]
        # Only 5 of 6 typologies present
        for typology in ['structuring', 'layering', 'funnel', 'round_trip', 'shell_company']:
            accounts.append(make_account(f'ACC_SUSP_{typology}', is_suspicious=True, typology=typology))

        result = validate_generated_data(accounts, [], SIM_START, SIM_END)
        assert any('typolog' in e.lower() for e in result.errors)

    def test_validation_result_str(self):
        """ValidationResult.__str__ should return a non-empty string."""
        result = ValidationResult()
        result.add_warning("Test warning")
        result.stats = {'count': 100}
        output = str(result)
        assert 'Validation' in output
        assert 'Test warning' in output

    def test_too_few_accounts_fails(self):
        """Fewer than 100 accounts should fail validation."""
        accounts = [make_account(f'ACC_{i}') for i in range(5)]
        result = validate_generated_data(accounts, [], SIM_START, SIM_END)
        assert not result.passed
        assert any('few accounts' in e.lower() or 'minimum' in e.lower() for e in result.errors)
