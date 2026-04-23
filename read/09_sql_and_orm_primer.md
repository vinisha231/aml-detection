# 09 — SQL and SQLAlchemy ORM Primer

## Why We Use SQLite + SQLAlchemy

### SQLite
- Zero-config: no server to install, database is a single `.db` file
- Perfect for local development and small-scale deployments
- Same SQL dialect as PostgreSQL for all queries we use
- Can be swapped for PostgreSQL by changing one line (`DATABASE_URL`)

### SQLAlchemy ORM
SQLAlchemy is a Python library that lets you work with the database using Python objects instead of raw SQL strings.

**Without ORM (raw SQL):**
```python
cursor.execute("SELECT * FROM accounts WHERE risk_score > 70")
rows = cursor.fetchall()
accounts = [{"account_id": row[0], "holder_name": row[1], ...} for row in rows]
```

**With SQLAlchemy ORM:**
```python
accounts = session.query(Account).filter(Account.risk_score > 70).all()
```

Benefits:
1. Python objects, not raw tuples — `acc.holder_name` is clearer than `row[1]`
2. SQL injection prevention — ORM uses parameterised queries automatically
3. Database portability — same code works with SQLite, PostgreSQL, MySQL
4. IDE autocomplete — your editor knows the column names

---

## Our Schema at a Glance

```
accounts ─────────────────────── transactions
├── account_id (PK)              ├── transaction_id (PK)
├── holder_name                  ├── sender_account_id (FK → accounts)
├── account_type                 ├── receiver_account_id (FK → accounts)
├── branch                       ├── amount
├── balance                      ├── transaction_type
├── is_suspicious                ├── transaction_date
├── typology                     └── is_suspicious
├── risk_score
├── evidence                    signals
├── disposition                 ├── signal_id (PK, autoincrement)
└── disposition_at              ├── account_id (FK → accounts)
                                ├── signal_type
dispositions                    ├── score
├── disposition_id (PK)         ├── weight
├── account_id (FK → accounts)  ├── confidence
├── decision                    └── evidence
├── risk_score_at_decision
└── decided_at
```

---

## Key SQLAlchemy Patterns Used in This Project

### 1. Defining a Table (schema.py)
```python
class Account(Base):
    __tablename__ = 'accounts'
    
    account_id   = Column(String, primary_key=True)
    holder_name  = Column(String, nullable=False)
    risk_score   = Column(Float, nullable=True)   # nullable: not scored yet
    
    # Relationship: one Account has many Transactions
    sent_transactions = relationship(
        'Transaction',
        foreign_keys='Transaction.sender_account_id',
        back_populates='sender'
    )
```

### 2. Querying (queries.py)
```python
# Get one account by ID
account = session.query(Account).filter(Account.account_id == 'ACC_001').first()

# Get top-risk accounts
queue = (
    session.query(Account)
    .filter(Account.risk_score >= 70)
    .order_by(Account.risk_score.desc())
    .limit(100)
    .all()
)

# Count by typology
from sqlalchemy import func
counts = session.query(Account.typology, func.count()).group_by(Account.typology).all()
```

### 3. Inserting / Updating
```python
# Insert new signal
signal = Signal(
    account_id  = 'ACC_001',
    signal_type = 'structuring',
    score       = 85.0,
    weight      = 2.0,
)
session.add(signal)
session.commit()

# Update account score
account = session.query(Account).filter(Account.account_id == 'ACC_001').first()
account.risk_score = 85.0
account.evidence   = "Structuring detected."
session.commit()
```

### 4. Batch Inserts (scripts/generate_data.py)
```python
# Insert 1000 accounts at once — much faster than one at a time
session.bulk_insert_mappings(Account, account_dicts)
session.commit()
```

---

## Common Pitfalls

### Forgetting to commit
```python
account.risk_score = 85.0
# ⚠️ Without session.commit(), this change is invisible to other sessions
session.commit()  # ✅
```

### N+1 query problem
```python
# ❌ BAD: issues one query per account (N+1 queries total)
accounts = session.query(Account).all()
for acc in accounts:
    signals = session.query(Signal).filter(Signal.account_id == acc.account_id).all()

# ✅ GOOD: one query with JOIN or a single bulk fetch
account_ids = [acc.account_id for acc in accounts]
all_signals = session.query(Signal).filter(Signal.account_id.in_(account_ids)).all()
```

### Keeping sessions too long
```python
# ✅ Use dependency injection and close the session after each request
def get_db():
    session = factory()
    try:
        yield session
    finally:
        session.close()  # always close, even if an error occurred
```

---

## Running Raw SQL When Needed

Sometimes the ORM query is too complex (e.g., window functions, CTEs).
SQLAlchemy lets you drop down to raw SQL:

```python
from sqlalchemy import text

result = session.execute(text("""
    SELECT signal_type, AVG(score) as avg_score
    FROM signals
    GROUP BY signal_type
    ORDER BY avg_score DESC
"""))

for row in result:
    print(row.signal_type, row.avg_score)
```

---

## Database Indexes

Indexes speed up queries on frequently-filtered columns.
From our `schema.py`:

```python
# Index on risk_score lets the queue endpoint (ORDER BY risk_score DESC) run fast
Index('idx_acc_risk', Account.risk_score)

# Index on transaction dates lets lookback window queries run fast
Index('idx_tx_date', Transaction.transaction_date)
```

Without indexes, every query scans the entire table — fine for 5,000 accounts,
but would be very slow at 500,000 accounts.
