"""
backend/api/routes/export.py
─────────────────────────────────────────────────────────────────────────────
Data export endpoints for AML reports and compliance documentation.

Endpoints:
  GET /export/escalated.csv
    Download all escalated accounts as CSV.
    Used to prepare SAR filing batch exports.

  GET /export/signals.csv
    Download all signals (one row per signal) as CSV.
    Used for offline analysis and model validation.

Why CSV export?
  AML teams often work with existing compliance tools (Excel, Tableau,
  regulatory reporting systems) that accept CSV. Rather than building
  native integrations, CSV export provides maximum compatibility.

  In a real system, this might also export to:
    - FinCEN's BSA E-Filing system (direct SAR submission)
    - A case management system (Actimize, NICE, Oracle FCCM)
    - A data lake for regulatory reporting
─────────────────────────────────────────────────────────────────────────────
"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database.schema import get_session_factory, get_engine, Account, Signal

router = APIRouter(prefix='/export', tags=['export'])

# Characters that make a spreadsheet treat a cell as a formula.
_FORMULA_TRIGGERS = ('=', '+', '-', '@', '\t', '\r')


def _csv_safe(value):
    """
    Neutralise CSV/formula injection (CWE-1236). Free-text fields such as
    holder_name or disposition_note are analyst-controlled and these CSVs are
    opened in Excel/Sheets; a value like '=HYPERLINK(...)' would execute. Prefix
    a leading formula trigger with a single quote so the cell stays literal.
    """
    if isinstance(value, str) and value and value[0] in _FORMULA_TRIGGERS:
        return "'" + value
    return value


def get_db():
    engine  = get_engine()
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@router.get('/escalated.csv')
def export_escalated_accounts(db: Session = Depends(get_db)):
    """
    Export all escalated accounts as a CSV file.

    Columns: account_id, holder_name, account_type, branch, risk_score,
             typology, disposition_note, disposition_at

    The response streams the CSV directly — no temporary file is created.
    StreamingResponse lets us send large files without loading them into memory.

    Content-Disposition header triggers the browser to download the file
    rather than displaying it inline.
    """
    # Fetch all escalated accounts
    accounts = (
        db.query(Account)
        .filter(Account.disposition == 'escalated')
        .order_by(Account.risk_score.desc())
        .all()
    )

    # Build CSV in memory using StringIO buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'account_id', 'holder_name', 'account_type', 'branch',
        'risk_score', 'typology', 'evidence', 'disposition_note', 'disposition_at',
    ])

    # Data rows
    for acc in accounts:
        writer.writerow([
            _csv_safe(acc.account_id),
            _csv_safe(acc.holder_name),
            _csv_safe(acc.account_type),
            _csv_safe(acc.branch),
            f'{acc.risk_score:.1f}' if acc.risk_score else '',
            _csv_safe(acc.typology or ''),
            _csv_safe(acc.evidence or ''),
            _csv_safe(acc.disposition_note or ''),
            acc.disposition_at.isoformat() if acc.disposition_at else '',
        ])

    # Generate filename with current date
    today = datetime.utcnow().strftime('%Y%m%d')
    filename = f'aml_escalated_accounts_{today}.csv'

    # Rewind the buffer and stream it back
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.get('/signals.csv')
def export_signals(db: Session = Depends(get_db)):
    """
    Export all detection signals as CSV for offline analysis.

    Columns: account_id, signal_type, score, weight, confidence, evidence

    This export is useful for:
      - Tuning signal weights (see which signals have high FPR)
      - Validating the scoring model against ground truth labels
      - Regulatory documentation of the detection methodology
    """
    signals = (
        db.query(Signal)
        .order_by(Signal.account_id, Signal.score.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'signal_id', 'account_id', 'signal_type', 'score',
        'weight', 'confidence', 'evidence', 'created_at',
    ])

    for sig in signals:
        writer.writerow([
            _csv_safe(sig.signal_id),
            _csv_safe(sig.account_id),
            _csv_safe(sig.signal_type),
            f'{sig.score:.1f}',
            f'{sig.weight:.2f}',
            f'{sig.confidence:.2f}',
            _csv_safe(sig.evidence or ''),
            sig.created_at.isoformat() if sig.created_at else '',
        ])

    today = datetime.utcnow().strftime('%Y%m%d')
    filename = f'aml_signals_{today}.csv'

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
