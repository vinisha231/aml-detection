"""
backend/api/routes/analytics.py
─────────────────────────────────────────────────────────────────────────────
Analytics API endpoints for the AML dashboard.

Endpoints:
  GET /analytics/false-positive-rates
    Returns false positive rate per signal type.
    FPR = dismissed / (escalated + dismissed) per signal type.

  GET /analytics/typology-breakdown
    Returns count and avg score for each AML typology.
    Useful for understanding which typologies are hardest to detect.

  GET /analytics/score-distribution
    Returns a histogram of risk scores in 10-point buckets (0-9, 10-19, ...).
    Useful for seeing the overall score landscape.

  GET /analytics/daily-escalations
    Returns number of SAR escalations per day for the past 30 days.
    Useful for trending the analyst workload over time.

What are analytics endpoints for?
  The detection pipeline produces thousands of scored accounts. Analytics
  endpoints let the AML team ask "how is our system performing overall?"
  rather than inspecting individual accounts. These are the metrics that
  AML managers present to regulators and compliance committees.
─────────────────────────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.schema import get_session_factory, get_engine
from backend.database.schema import Account, Signal, Disposition

router = APIRouter(prefix='/analytics', tags=['analytics'])


def get_db():
    """Dependency: provide a SQLAlchemy session, close it after the request."""
    engine   = get_engine()
    factory  = get_session_factory(engine)
    session  = factory()
    try:
        yield session
    finally:
        session.close()


@router.get('/false-positive-rates')
def get_false_positive_rates(db: Session = Depends(get_db)):
    """
    Calculate the false positive rate for each signal type.

    Method:
      For accounts with a disposition, look at which signal types fired.
      FPR = (dismissed accounts with signal X) / (all dispositioned accounts with signal X)

    A high FPR for a signal means it fires often but leads to dismissals
    (i.e., it's generating lots of false alarms). Low-FPR signals are more
    "precise" — when they fire, the account usually IS suspicious.

    Returns:
        List of {signal_type, escalated_count, dismissed_count, fpr} dicts.
    """
    # Get all dispositioned accounts (have a clear escalated/dismissed decision)
    dispositioned = (
        db.query(Account.account_id, Account.disposition)
        .filter(Account.disposition.in_(['escalated', 'dismissed']))
        .all()
    )

    if not dispositioned:
        return []

    dispositioned_dict = {row.account_id: row.disposition for row in dispositioned}
    dispositioned_ids  = list(dispositioned_dict.keys())

    # Get all signals for dispositioned accounts
    signals = (
        db.query(Signal.account_id, Signal.signal_type)
        .filter(Signal.account_id.in_(dispositioned_ids))
        .all()
    )

    # Count escalated vs dismissed per signal type
    escalated_by_signal: dict[str, int] = defaultdict(int)
    dismissed_by_signal: dict[str, int] = defaultdict(int)

    for sig in signals:
        disposition = dispositioned_dict.get(sig.account_id)
        if disposition == 'escalated':
            escalated_by_signal[sig.signal_type] += 1
        elif disposition == 'dismissed':
            dismissed_by_signal[sig.signal_type] += 1

    # Compile results
    all_signal_types = set(escalated_by_signal) | set(dismissed_by_signal)
    results = []

    for signal_type in sorted(all_signal_types):
        esc = escalated_by_signal.get(signal_type, 0)
        dis = dismissed_by_signal.get(signal_type, 0)
        total = esc + dis
        fpr   = round(dis / total, 3) if total > 0 else 0.0

        results.append({
            'signal_type':       signal_type,
            'escalated_count':   esc,
            'dismissed_count':   dis,
            'total_dispositioned': total,
            'false_positive_rate': fpr,
        })

    # Sort by FPR descending so the worst-performing signals appear first
    results.sort(key=lambda r: r['false_positive_rate'], reverse=True)
    return results


@router.get('/typology-breakdown')
def get_typology_breakdown(db: Session = Depends(get_db)):
    """
    Return count and average risk score grouped by AML typology.

    Only includes accounts where a typology was assigned during data generation
    (i.e., is_suspicious = True accounts).
    """
    accounts = (
        db.query(Account.typology, Account.risk_score)
        .filter(Account.typology.isnot(None))
        .filter(Account.risk_score.isnot(None))
        .all()
    )

    if not accounts:
        return []

    # Group by typology
    typology_scores: dict[str, list[float]] = defaultdict(list)
    for row in accounts:
        typology_scores[row.typology].append(row.risk_score)

    return [
        {
            'typology':   typology,
            'count':      len(scores),
            'avg_score':  round(sum(scores) / len(scores), 1),
            'max_score':  round(max(scores), 1),
            'min_score':  round(min(scores), 1),
        }
        for typology, scores in sorted(typology_scores.items())
    ]


@router.get('/score-distribution')
def get_score_distribution(db: Session = Depends(get_db)):
    """
    Return histogram of risk scores in 10-point buckets.

    Returns:
        List of {bucket: "0-9", count: N} for buckets 0-9 through 90-100.
    """
    scores = (
        db.query(Account.risk_score)
        .filter(Account.risk_score.isnot(None))
        .all()
    )

    if not scores:
        return []

    # Initialize 10 buckets: 0-9, 10-19, ..., 90-100
    buckets: dict[int, int] = {i: 0 for i in range(0, 100, 10)}

    for (score,) in scores:
        bucket_key = min(90, (int(score) // 10) * 10)  # 100 → bucket 90
        buckets[bucket_key] += 1

    return [
        {
            'bucket':     f'{k}–{k + 9}' if k < 90 else '90–100',
            'bucket_min': k,
            'count':      v,
        }
        for k, v in sorted(buckets.items())
    ]


@router.get('/daily-escalations')
def get_daily_escalations(db: Session = Depends(get_db)):
    """
    Return number of SAR escalations per day for the past 30 days.

    Useful for: staffing (workload trending), AML program effectiveness.
    A spike in escalations might indicate a new fraud campaign detected.
    """
    cutoff = datetime.utcnow() - timedelta(days=30)

    dispositions = (
        db.query(Disposition.decided_at)
        .filter(Disposition.decision == 'escalated')
        .filter(Disposition.decided_at >= cutoff)
        .all()
    )

    # Group by calendar date
    daily_counts: dict[str, int] = defaultdict(int)
    for (decided_at,) in dispositions:
        date_key = decided_at.strftime('%Y-%m-%d')
        daily_counts[date_key] += 1

    # Fill in days with 0 escalations (so the chart doesn't have gaps)
    result = []
    for i in range(30):
        date = (datetime.utcnow() - timedelta(days=29 - i)).strftime('%Y-%m-%d')
        result.append({'date': date, 'count': daily_counts.get(date, 0)})

    return result
