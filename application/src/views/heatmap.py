"""
Heatmap data endpoints for visualization.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from ..db import SessionLocal
from ..models import HemogramObservation, AlertCommunication
from ..services.geospatial import compute_outbreak_regions

router = APIRouter(tags=["Heatmap"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/heatmap-data")
def get_heatmap_data(db: Session = Depends(get_db)):
    """
    Returns observation data for heatmap visualization.

    Filters out records without coordinates.
    Includes aggregated region statistics (case count and outbreak status).
    ALL BUSINESS LOGIC CENTRALIZED HERE - frontend just renders.

    Returns:
    - observations: List of observation points with metadata
    - outbreaks: Computed outbreak regions with centroid, radius, and affected points
    """
    # Get observations with coordinates
    rows = db.execute(
        select(HemogramObservation)
        .where(HemogramObservation.latitude.isnot(None))
        .where(HemogramObservation.longitude.isnot(None))
        .order_by(HemogramObservation.received_at.desc())
    ).scalars().all()

    # Check for recent alerts (outbreak status) in last 24h
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    has_recent_alerts = db.execute(
        select(func.count()).select_from(AlertCommunication)
        .where(AlertCommunication.created_at >= since_24h)
    ).scalar() > 0

    # Compute outbreak geospatial data (centroid, radius, affected points)
    outbreak_data = compute_outbreak_regions(db)

    return {
        "observations": [
            {
                "lat": row.latitude,
                "lng": row.longitude,
                "intensity": row.leukocytes if row.leukocytes else 1.0,
                "received_at": row.received_at.isoformat() if row.received_at else None,
                "outbreak": has_recent_alerts
            }
            for row in rows
        ],
        "outbreaks": outbreak_data
    }
