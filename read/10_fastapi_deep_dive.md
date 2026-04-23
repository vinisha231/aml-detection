# 10 — FastAPI Deep Dive

## What FastAPI Does

FastAPI takes a Python function and turns it into an HTTP endpoint automatically.

```python
@router.get('/accounts/{account_id}')
def get_account(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return account
```

When a client calls `GET /accounts/ACC_001`, FastAPI:
1. Extracts `account_id = "ACC_001"` from the URL path
2. Creates a database session (via `Depends(get_db)`)
3. Runs the function body
4. Serializes the return value to JSON automatically
5. Closes the database session

---

## Dependency Injection (`Depends`)

`Depends` is FastAPI's way of sharing resources between endpoints without global variables.

```python
# Define the dependency once
def get_db():
    session = factory()
    try:
        yield session        # ← provide the session to the endpoint
    finally:
        session.close()     # ← always clean up, even if an error occurred

# Use it in any endpoint
@router.get('/queue')
def get_queue(db: Session = Depends(get_db)):
    return db.query(Account).order_by(Account.risk_score.desc()).all()
```

**Why not just use a global session?**
- Thread safety: multiple requests are handled concurrently, each needs its own session
- Resource cleanup: sessions are automatically closed after each request
- Testability: tests can inject a different session (pointing to a test database)

---

## Pydantic Validation

Pydantic models define what the request body must look like. FastAPI runs validation automatically before calling your function.

```python
class DispositionRequest(BaseModel):
    decision: str
    note:     str = Field(..., min_length=10, max_length=500)
    
    @validator('decision')
    def decision_must_be_valid(cls, v):
        if v not in ('escalated', 'dismissed'):
            raise ValueError("Must be 'escalated' or 'dismissed'")
        return v
```

If a client sends `{"decision": "maybe"}`, FastAPI returns a 422 error before your code runs. You never need to write `if decision not in valid_choices:` manually.

---

## Response Models

You can specify exactly what shape the response should have:

```python
class AccountSummary(BaseModel):
    account_id:  str
    holder_name: str
    risk_score:  float | None
    
    class Config:
        from_attributes = True  # lets Pydantic read SQLAlchemy model attributes

@router.get('/accounts/{id}', response_model=AccountSummary)
def get_account(id: str, db: Session = Depends(get_db)):
    return db.query(Account).filter(Account.account_id == id).first()
    # FastAPI only includes fields defined in AccountSummary
    # (e.g., won't accidentally expose internal fields like raw_signals)
```

---

## Routers — Organising Endpoints

Instead of putting all endpoints in one file, we use APIRouter to split them:

```
backend/api/
├── main.py                ← creates the FastAPI app, registers routers
└── routes/
    ├── queue.py           ← GET /queue, GET /queue/stats
    ├── accounts.py        ← GET /accounts/{id}, GET /accounts/{id}/graph
    ├── dispositions.py    ← POST /dispositions/{id}, DELETE /dispositions/{id}
    ├── analytics.py       ← GET /analytics/*
    ├── search.py          ← GET /search
    └── export.py          ← GET /export/*.csv
```

**In main.py:**
```python
app.include_router(queue_router)
app.include_router(accounts_router)
app.include_router(dispositions_router)
```

This keeps each file focused and manageable. Adding a new feature = creating a new file in `routes/`.

---

## Error Handling

```python
# In your endpoint
if not account:
    raise HTTPException(
        status_code=404,
        detail=f"No account with ID {account_id} found."
    )

# Global handler for unexpected errors (in exceptions.py)
async def generic_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "Check server logs."}
    )
```

Always use HTTPException for expected error conditions (not found, invalid input).
The global handler catches unexpected crashes and returns a clean 500 instead of a stack trace.

---

## CORS (Cross-Origin Resource Sharing)

Our frontend (localhost:5173) calls the backend (localhost:8000). Browsers block cross-origin requests by default for security. We explicitly allow it:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

In production, `allow_origins` would list your specific domain (`https://aml-dashboard.yourcompany.com`), NOT `*` — that would allow any website to call your API.

---

## Automatic API Documentation

FastAPI generates interactive docs automatically from your code:

- **Swagger UI**: `http://localhost:8000/docs` — try every endpoint in the browser
- **ReDoc**: `http://localhost:8000/redoc` — clean read-only docs

This is generated from your type annotations and docstrings with no extra work.

---

## Async vs. Sync Endpoints

FastAPI supports both:

```python
# Synchronous (simpler, fine for database-bound operations)
@router.get('/queue')
def get_queue(db: Session = Depends(get_db)):
    return db.query(Account).all()

# Asynchronous (better for I/O-heavy operations like external HTTP calls)
@router.get('/external-check')
async def check_external(account_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://sanctions-api.example/{account_id}")
    return response.json()
```

We use synchronous endpoints throughout because SQLAlchemy's standard ORM is synchronous. For async SQLAlchemy (production scale), use SQLAlchemy 2.0 with `asyncpg`.
