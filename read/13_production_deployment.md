# 13 — Production Deployment Guide

## Architecture: Development vs. Production

### Development (what we have)
```
Browser (localhost:5173) → Vite proxy → FastAPI (localhost:8000) → SQLite (data/aml.db)
```

### Production (what you'd build next)
```
Browser → CloudFront/CDN → Load Balancer → FastAPI cluster → PostgreSQL RDS
                                        ↘ Redis (cache/rate limit)
                                        ↘ S3 (CSV exports)
```

---

## Database: SQLite → PostgreSQL

SQLite works perfectly for development but has limitations in production:
- No concurrent writes (only one writer at a time)
- File-based (can't distribute across servers)
- No row-level locking

**Migration to PostgreSQL:**

```bash
# Install PostgreSQL driver
pip install psycopg2-binary asyncpg

# Change one line in schema.py:
# Before:
DATABASE_URL = f"sqlite:///{db_path}"
# After:
DATABASE_URL = os.environ['DATABASE_URL']  # postgresql://user:pass@host:5432/aml_db
```

SQLAlchemy ORM code is identical for both databases — that's the whole point of the ORM abstraction.

**Recommended: AWS RDS PostgreSQL**
- Automated backups (point-in-time recovery)
- Read replicas for analytics queries
- Automatic failover with Multi-AZ deployment

---

## API: Uvicorn → Gunicorn + Uvicorn Workers

```dockerfile
# Dockerfile.backend — production version
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Gunicorn manages multiple Uvicorn worker processes
# --workers 4: 4 processes (rule of thumb: 2 * CPU_count + 1)
# -k uvicorn.workers.UvicornWorker: use async Uvicorn workers
CMD ["gunicorn", "backend.api.main:app",
     "--workers", "4",
     "-k", "uvicorn.workers.UvicornWorker",
     "--bind", "0.0.0.0:8000",
     "--timeout", "60",
     "--access-logfile", "-"]
```

---

## Frontend: Vite Dev → Static Build

```bash
# Build production bundle (runs TypeScript compiler + minifier + tree shaker)
cd frontend && npm run build
# Output: frontend/dist/ (index.html + hashed JS/CSS chunks)
```

Deploy `frontend/dist/` to:
- **AWS CloudFront + S3**: global CDN, automatic HTTPS, ~$5/month
- **Vercel**: zero-config deployment from GitHub, free tier available
- **Nginx static serving**: if deploying to a VPS

---

## Environment Variables

Never hardcode secrets. Use environment variables for:

```bash
# .env (never commit this file!)
DATABASE_URL=postgresql://aml_user:secret@rds.example.com:5432/aml_db
SECRET_KEY=random-64-char-string-for-jwt-signing
REDIS_URL=redis://redis-cluster.example.com:6379
SENTRY_DSN=https://abc123@sentry.io/12345
ALLOWED_ORIGINS=https://aml.yourcompany.com
```

In FastAPI, load with `pydantic_settings`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url:    str
    secret_key:      str
    allowed_origins: list[str] = ['http://localhost:5173']
    
    class Config:
        env_file = '.env'
```

---

## Authentication and Authorization

Our current system has NO authentication — anyone who can reach the API can access all data.

For production, add:

**Option 1: JWT Tokens (stateless)**
```python
from fastapi_jwt_auth import AuthJWT

@router.get('/queue')
def get_queue(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    # Log who made this request for audit trail
    audit_log(current_user, 'GET /queue')
    return ...
```

**Option 2: API Keys (simpler)**
```python
API_KEY_HEADER = 'X-API-Key'

async def verify_api_key(request: Request):
    key = request.headers.get(API_KEY_HEADER)
    if key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Role-Based Access Control:**
- `analyst` role: read queue, submit dispositions
- `senior_analyst` role: + access analytics, approve SARs
- `admin` role: + manage users, configure alert thresholds

---

## Monitoring and Alerting

### Application Monitoring (Sentry)
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10% of requests for performance tracing
)
```

### Metrics (Prometheus + Grafana)
Track:
- Request latency per endpoint (alert if P99 > 2s)
- Error rate (alert if 5xx > 1%)
- Queue size (alert if > 5000 unreviewed high-risk accounts)
- Detection pipeline runtime (alert if > 2 hours)

### AML-Specific Alerts
- SAR filings per day > 2x historical average (sudden fraud campaign?)
- False positive rate > 80% for any rule (rule needs retuning)
- Detection pipeline hasn't run in > 26 hours (infrastructure failure)

---

## Compliance and Audit Trail

All analyst actions must be logged for BSA compliance:

```python
class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id          = Column(Integer, primary_key=True)
    user_id     = Column(String, nullable=False)
    action      = Column(String, nullable=False)   # 'view_account', 'escalate', 'dismiss'
    account_id  = Column(String, nullable=True)    # which account was viewed/acted on
    ip_address  = Column(String, nullable=False)
    timestamp   = Column(DateTime, default=datetime.utcnow)
    details     = Column(JSON, nullable=True)      # additional context
```

Regulators can request these logs during an exam. Retention period: minimum 5 years (BSA requirement).

---

## Disaster Recovery

| Scenario | Recovery Strategy |
|----------|-----------------|
| Database corruption | Restore from RDS automated backup (RPO: 1 hour) |
| API server failure | Load balancer routes to healthy instances (RTO: < 1 minute) |
| Detection pipeline failure | Alert fires, analysts work from previous scores |
| Frontend CDN outage | Deploy static files to backup CDN |
| Ransomware | Air-gapped backups to separate AWS account |

Document your RTO (Recovery Time Objective) and RPO (Recovery Point Objective) in a Business Continuity Plan before going to production.
