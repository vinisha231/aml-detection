# Typology Generators — Developer Notes

Each file in this folder generates transactions for one money laundering pattern.

## Adding a new typology

1. Create `my_typology.py` here, with a function named `generate_my_typology_transactions()`
2. The function signature must be:
   ```python
   def generate_my_typology_transactions(
       account_ids: List[str],
       simulation_start: datetime,
       simulation_end: datetime,
       rng: random.Random = None,
       # any extra args specific to this typology
   ) -> List[dict]:
   ```
3. Return a list of transaction dicts (use `make_transaction()` from `transactions.py`)
4. Set `is_suspicious=True` and `typology="my_typology"` on every transaction
5. Add the import to `__init__.py`
6. Add a `generate_accounts()` allocation for this typology in `accounts.py`
7. Call your function in `scripts/generate_data.py`

## Parameter guidance (from FATF)

Always base parameters on real FATF typology reports:
- Duration ranges should match what FATF reports as "typical"
- Amount ranges should be realistic for the pattern
- Frequency should match documented patterns

Unrealistic parameters make the detection problem too easy or too hard.
