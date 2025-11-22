"""
Alerts endpoints for managing outbreak alerts.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from ..db import SessionLocal
from ..schemas import AlertOut
from ..models import AlertCommunication

router = APIRouter(tags=["Alerts"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/alerts", response_model=List[AlertOut])
def list_alerts(db: Session = Depends(get_db)):
    """
    List all outbreak alerts.

    Returns alerts ordered by creation date (most recent first).
    Each alert contains:
    - Alert ID
    - Region IBGE code
    - Summary description
    - FHIR Communication resource
    """
    rows = db.execute(
        select(AlertCommunication).order_by(AlertCommunication.created_at.desc())
    ).scalars().all()

    return [
        AlertOut(
            id=row.id,
            summary=row.summary,
            fhir_communication=row.fhir_communication,
        )
        for row in rows
    ]
