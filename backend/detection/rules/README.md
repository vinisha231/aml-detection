# Detection Rules — Developer Notes

Each rule is a Python function that takes account data + transactions
and returns a list of `RuleSignal` objects (or empty list if nothing found).

## Rule interface

```python
def check_my_rule(
    account_id: str,
    transactions: List[dict],
    as_of_date: Optional[datetime] = None,
) -> List[RuleSignal]:
```

## Rule design checklist

- [ ] Never raises exceptions (wrap logic in try/except)
- [ ] Returns empty list if no suspicious activity found
- [ ] Score 0-100 (never negative, never > 95 for a single rule)
- [ ] Weight reflects quality: high-precision rules get weight 2.0, noisy rules 0.5
- [ ] Confidence 0-1 (reflects how certain this specific firing is)
- [ ] Evidence string is specific: includes actual numbers, dates, amounts
- [ ] Has unit tests in `backend/tests/test_<rule_name>.py`

## Score calibration guide

| Certainty | Score range | Example |
|-----------|-------------|---------|
| Possible  | 20-40       | 5 deposits near threshold (coincidence possible) |
| Likely    | 41-65       | 10 deposits near threshold with consistent amounts |
| Probable  | 66-80       | 15 deposits near threshold, all same branch |
| Near certain | 81-95   | 20+ deposits, sweet spot ($9k-$9.9k), high velocity |

## Evidence string format

Good:
  "12 cash deposits avg $9,640 in 14 days (total $115,680; all under $10k CTR threshold)"

Bad:
  "Multiple deposits detected"

The evidence string is what the analyst reads. Make it actionable.
