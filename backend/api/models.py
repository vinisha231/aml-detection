"""
backend/api/models.py
─────────────────────────────────────────────────────────────────────────────
Pydantic models for API request and response bodies.

What is Pydantic?
  Pydantic is a Python library that validates data using type hints.
  When FastAPI receives a request, it automatically:
  1. Parses the JSON body
  2. Validates each field against the Pydantic model
  3. Returns a 422 error if validation fails
  4. Converts it to a typed Python object if validation succeeds

Why separate from SQLAlchemy models?
  SQLAlchemy models define database TABLE STRUCTURE.
  Pydantic models define API REQUEST/RESPONSE SHAPE.
  They're often similar but serve different purposes:
  - DB model has foreign keys, indexes, relationships
  - API model has validation rules, computed fields, optional fields
─────────────────────────────────────────────────────────────────────────────
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── RESPONSE models (what the API sends back) ────────────────────────────────

class AccountSummary(BaseModel):
    """
    Summary of an account — shown in the risk queue.
    We don't need ALL account fields for the queue view.
    """
    account_id:    str
    holder_name:   str
    account_type:  str
    risk_score:    Optional[float] = None
    risk_tier:     Optional[str]   = None   # "critical", "high", "medium", "low"
    top_signal:    Optional[str]   = None   # which rule fired with highest score
    typology:      str             = "benign"
    disposition:   Optional[str]  = None
    scored_at:     Optional[datetime] = None

    # Pydantic v2: allow creating from SQLAlchemy objects (not just dicts)
    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    """
    One transaction as returned by the API.
    """
    transaction_id:      str
    sender_account_id:   str
    receiver_account_id: str
    amount:              float
    transaction_type:    str
    description:         str
    transaction_date:    datetime
    is_suspicious:       bool
    typology:            str

    model_config = {"from_attributes": True}


class SignalResponse(BaseModel):
    """
    One detection signal as returned by the API.
    """
    signal_type:  str
    score:        float
    weight:       float
    evidence:     str
    confidence:   float
    created_at:   datetime

    model_config = {"from_attributes": True}


class AccountDetailResponse(BaseModel):
    """
    Full account detail — shown on the Account Detail screen.
    Includes transactions, signals, and evidence string.
    """
    account_id:       str
    holder_name:      str
    account_type:     str
    branch:           str
    opened_date:      datetime
    balance:          float
    is_suspicious:    bool          # ground truth (only in dev — hide in production!)
    typology:         str
    risk_score:       Optional[float]  = None
    evidence:         Optional[str]    = None
    scored_at:        Optional[datetime] = None
    disposition:      Optional[str]    = None
    disposition_note: Optional[str]    = None
    disposition_at:   Optional[datetime] = None
    transactions:     List[TransactionResponse] = []
    signals:          List[SignalResponse]       = []

    model_config = {"from_attributes": True}


class GraphDataResponse(BaseModel):
    """
    Transaction graph data for a specific account.
    Format matches react-force-graph input format.
    """
    nodes: List[dict]  # [{"id": "ACC_001", ...}, ...]
    links: List[dict]  # [{"source": "ACC_001", "target": "ACC_002", "weight": 5000}, ...]


class QueueResponse(BaseModel):
    """
    Paginated risk queue response.
    """
    accounts:    List[AccountSummary]
    total:       int   # total accounts matching the filter
    page:        int
    page_size:   int
    has_more:    bool


class StatsResponse(BaseModel):
    """
    Dashboard statistics for the header.
    """
    total_accounts:      int
    scored_accounts:     int
    high_risk_accounts:  int
    escalated:           int
    avg_score:           float


class FPREntry(BaseModel):
    """
    False positive rate for one signal type.
    """
    signal_type:         str
    total_fires:         int
    dismissed:           int
    false_positive_rate: float


# ─── REQUEST models (what the API receives) ────────────────────────────────────

class DispositionRequest(BaseModel):
    """
    Request body for recording an analyst's disposition decision.
    """
    decision: str = Field(
        ...,
        pattern="^(escalated|dismissed)$",  # must be one of these two values
        description="Analyst decision: 'escalated' or 'dismissed'"
    )
    note: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional analyst note explaining the decision"
    )
