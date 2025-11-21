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

    # Aggregate statistics by region (last 7 days)
    now = datetime.now(timezone.utc)
    since_7d = now - timedelta(days=7)
    since_24h = now - timedelta(hours=24)

    # Count cases per region in last 7 days
    region_counts = {}
    region_rows = db.execute(
        select(
            HemogramObservation.region_ibge_code,
            func.count(HemogramObservation.id).label('count')
        )
        .where(HemogramObservation.received_at >= since_7d)
        .group_by(HemogramObservation.region_ibge_code)
    ).all()

    for region_code, count in region_rows:
        region_counts[region_code] = count

    # Check for recent alerts (outbreak status) in last 24h
    region_outbreaks = set()
    alert_rows = db.execute(
        select(AlertCommunication.region_ibge_code.distinct())
        .where(AlertCommunication.created_at >= since_24h)
    ).scalars().all()

    region_outbreaks = set(alert_rows)

    # Compute outbreak geospatial data (centroid, radius, affected points)
    outbreak_data = compute_outbreak_regions(db)

    return {
        "observations": [
            {
                "lat": row.latitude,
                "lng": row.longitude,
                "intensity": row.leukocytes if row.leukocytes else 1.0,
                "region": row.region_ibge_code,
                "received_at": row.received_at.isoformat() if row.received_at else None,
                "region_case_count": region_counts.get(row.region_ibge_code, 0),
                "region_outbreak": row.region_ibge_code in region_outbreaks
            }
            for row in rows
        ],
        "outbreaks": outbreak_data
    }
