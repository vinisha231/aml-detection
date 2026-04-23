"""
backend/database/queries.py
─────────────────────────────────────────────────────────────────────────────
Common database query functions.

Instead of writing SQL queries scattered throughout the codebase,
we collect all database interactions here. This makes the code:
  - Easier to test (mock one file instead of many)
  - Easier to read (business logic separate from data access)
  - Easier to optimize (tune queries in one place)

This pattern is called the "Repository Pattern" in software engineering.
─────────────────────────────────────────────────────────────────────────────
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import Optional
from datetime import datetime

# Import our table classes from schema.py
from .schema import Account, Transaction, Signal, Disposition


# ─── ACCOUNT QUERIES ─────────────────────────────────────────────────────────

def get_account(session: Session, account_id: str) -> Optional[Account]:
    """
    Fetch a single account by its ID.

    Args:
        session: Active database session
        account_id: Account ID string (e.g., "ACC_000001")

    Returns:
        Account object if found, None if not found

    Example:
        with Session() as db:
            account = get_account(db, "ACC_000001")
            if account:
                print(account.holder_name)
    """
    return session.get(Account, account_id)


def get_risk_queue(
    session: Session,
    limit: int = 50,
    min_score: float = 0.0,
    disposition_filter: Optional[str] = "unreviewed"
) -> list[Account]:
    """
    Get accounts sorted by risk score descending — this is the analyst's queue.

    Args:
        session:            Active database session
        limit:              How many accounts to return (default: 50)
        min_score:          Only return accounts with risk_score >= this value
        disposition_filter: "unreviewed" = only show undisposed accounts
                            "all" = show everything
                            "escalated" / "dismissed" = show specific disposition

    Returns:
        List of Account objects, sorted by risk_score descending

    Example:
        accounts = get_risk_queue(session, limit=20)
        for acc in accounts:
            print(f"{acc.account_id}: {acc.risk_score:.0f}/100 — {acc.holder_name}")
    """

    # Start building the query
    query = session.query(Account)

    # Only include accounts that have been scored
    query = query.filter(Account.risk_score.isnot(None))

    # Apply minimum score filter
    if min_score > 0:
        query = query.filter(Account.risk_score >= min_score)

    # Apply disposition filter
    if disposition_filter == "unreviewed":
        query = query.filter(Account.disposition.is_(None))
    elif disposition_filter in ("escalated", "dismissed"):
        query = query.filter(Account.disposition == disposition_filter)
    # If "all", no filter applied

    # Sort by risk score (highest first) and limit results
    query = query.order_by(desc(Account.risk_score))
    query = query.limit(limit)

    return query.all()


def update_account_score(
    session: Session,
    account_id: str,
    risk_score: float,
    evidence: str
) -> None:
    """
    Update an account's risk score after the detection pipeline runs.

    Args:
        session:    Active database session
        account_id: Which account to update
        risk_score: New risk score (0–100)
        evidence:   Human-readable explanation of the score
    """
    account = session.get(Account, account_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found in database")

    account.risk_score = round(risk_score, 2)
    account.evidence = evidence
    account.scored_at = datetime.utcnow()

    # session.commit() is called by the caller (they control the transaction)


def record_disposition(
    session: Session,
    account_id: str,
    decision: str,
    note: Optional[str] = None
) -> None:
    """
    Record an analyst's decision on an account.

    Args:
        session:    Active database session
        account_id: Which account was reviewed
        decision:   "escalated" or "dismissed"
        note:       Optional analyst note explaining reasoning

    Raises:
        ValueError: if decision is not valid
    """
    if decision not in ("escalated", "dismissed"):
        raise ValueError(f"Invalid decision: {decision}. Must be 'escalated' or 'dismissed'.")

    # Update the account record
    account = session.get(Account, account_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found")

    account.disposition = decision
    account.disposition_note = note
    account.disposition_at = datetime.utcnow()

    # Also insert into the dispositions history table
    history_entry = Disposition(
        account_id=account_id,
        decision=decision,
        risk_score_at_decision=account.risk_score or 0.0,
        note=note,
        decided_at=datetime.utcnow()
    )
    session.add(history_entry)


# ─── TRANSACTION QUERIES ─────────────────────────────────────────────────────

def get_account_transactions(
    session: Session,
    account_id: str,
    limit: int = 100
) -> list[Transaction]:
    """
    Get all transactions for a given account (sent or received).

    Args:
        session:    Active database session
        account_id: Account to look up
        limit:      Maximum number of transactions to return

    Returns:
        List of Transaction objects, sorted by date descending (newest first)
    """
    # Transactions where this account is either sender or receiver
    return (
        session.query(Transaction)
        .filter(
            (Transaction.sender_account_id == account_id) |
            (Transaction.receiver_account_id == account_id)
        )
        .order_by(desc(Transaction.transaction_date))
        .limit(limit)
        .all()
    )


def get_transaction_count_by_account(session: Session) -> dict[str, int]:
    """
    Get the total number of transactions for each account.

    Used in the pipeline to calculate transaction velocity.

    Returns:
        Dict mapping account_id → transaction count

    Example:
        counts = get_transaction_count_by_account(session)
        # {"ACC_000001": 245, "ACC_000002": 12, ...}
    """
    # SQL equivalent: SELECT sender_account_id, COUNT(*) FROM transactions GROUP BY ...
    sent_counts = (
        session.query(Transaction.sender_account_id, func.count(Transaction.transaction_id))
        .group_by(Transaction.sender_account_id)
        .all()
    )

    # Build dictionary {account_id: count}
    result = {}
    for account_id, count in sent_counts:
        result[account_id] = result.get(account_id, 0) + count

    return result


# ─── SIGNAL QUERIES ──────────────────────────────────────────────────────────

def get_account_signals(session: Session, account_id: str) -> list[Signal]:
    """
    Get all detection signals for a given account.

    Args:
        session:    Active database session
        account_id: Which account

    Returns:
        List of Signal objects, sorted by score descending
    """
    return (
        session.query(Signal)
        .filter(Signal.account_id == account_id)
        .order_by(desc(Signal.score))
        .all()
    )


def save_signal(session: Session, signal: Signal) -> None:
    """
    Save a detection signal to the database.

    Args:
        session: Active database session
        signal:  Signal object to save
    """
    session.add(signal)


def delete_account_signals(session: Session, account_id: str) -> None:
    """
    Delete all signals for an account before re-scoring it.

    Call this before re-running detection to avoid duplicate signals.

    Args:
        session:    Active database session
        account_id: Account whose signals should be cleared
    """
    session.query(Signal).filter(Signal.account_id == account_id).delete()


# ─── STATISTICS QUERIES ───────────────────────────────────────────────────────

def get_summary_stats(session: Session) -> dict:
    """
    Get summary statistics for the monitoring dashboard header.

    Returns:
        Dict with counts and score distributions

    Example output:
        {
          "total_accounts": 5000,
          "scored_accounts": 4998,
          "high_risk_accounts": 142,   # score >= 70
          "escalated_today": 12,
          "avg_score": 23.4
        }
    """
    total = session.query(func.count(Account.account_id)).scalar()

    scored = session.query(func.count(Account.account_id)).filter(
        Account.risk_score.isnot(None)
    ).scalar()

    high_risk = session.query(func.count(Account.account_id)).filter(
        Account.risk_score >= 70
    ).scalar()

    escalated = session.query(func.count(Account.account_id)).filter(
        Account.disposition == "escalated"
    ).scalar()

    avg_score = session.query(func.avg(Account.risk_score)).filter(
        Account.risk_score.isnot(None)
    ).scalar()

    return {
        "total_accounts":  total,
        "scored_accounts": scored,
        "high_risk_accounts": high_risk,
        "escalated": escalated,
        "avg_score": round(avg_score or 0.0, 1),
    }


def get_false_positive_rate_by_rule(session: Session) -> list[dict]:
    """
    Calculate false positive rate per detection rule.

    A false positive = the rule fired, but the analyst dismissed the account.
    This is the key operational metric for tuning detection.

    Returns:
        List of dicts with signal_type, total_fires, dismissed_count, fpr

    Example:
        [
          {"signal_type": "structuring_rule", "total": 50, "dismissed": 12, "fpr": 0.24},
          {"signal_type": "velocity_rule",    "total": 80, "dismissed": 62, "fpr": 0.78},
        ]
    """
    # Get all signals that have a corresponding account disposition
    results = (
        session.query(
            Signal.signal_type,
            func.count(Signal.signal_id).label("total"),
            func.sum(
                # Count 1 if account was dismissed, 0 otherwise
                (Account.disposition == "dismissed").cast(Integer)
            ).label("dismissed")
        )
        .join(Account, Signal.account_id == Account.account_id)
        .filter(Account.disposition.isnot(None))  # only decided accounts
        .group_by(Signal.signal_type)
        .all()
    )

    output = []
    for signal_type, total, dismissed in results:
        fpr = (dismissed or 0) / total if total > 0 else 0.0
        output.append({
            "signal_type": signal_type,
            "total_fires": total,
            "dismissed": dismissed or 0,
            "false_positive_rate": round(fpr, 3),
        })

    # Sort by false positive rate descending (worst rules first)
    return sorted(output, key=lambda x: x["false_positive_rate"], reverse=True)
