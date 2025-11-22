"""
Data generation endpoints for testing and demonstrations.

This view handles HTTP requests for generating synthetic test data,
delegating business logic to the data_generation_service.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..services.data_generation_service import generate_synthetic_data

router = APIRouter(tags=["Data Generation"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/seed-data")
async def seed_test_data(db: Session = Depends(get_db), count: int = 3000):
    """
    Generate synthetic test data for demonstration purposes.

    Creates hemogram observations distributed across Brazil,
    with specific patterns in Goiás to trigger an alert.

    Generates data in REAL-TIME with 0.05s interval between observations
    to allow real-time visualization on the heatmap.

    Query params:
        count: Total number of observations to generate (min: 100, max: 10000, default: 3000)

    Returns:
        Statistics about the generated data and alerts created:
        - status: Success status
        - inserted_count: Number of observations created
        - regions_processed: Number of unique regions
        - region_distribution: Count per region
        - alerts_created: Number of alerts generated
        - alerts: Details of each alert
        - goias_stats: Detailed statistics for Goiás region
        - message: Summary message

    Raises:
        HTTPException: If count is outside valid range (100-10000)
    """
    # Validate input parameters
    if count < 100 or count > 10000:
        raise HTTPException(
            status_code=400,
            detail="Count must be between 100 and 10000"
        )

    # Delegate to service
    result = await generate_synthetic_data(
        db=db,
        count=count,
        goias_percentage=0.20,       # 20% from Goiás (concentrated outbreak area)
        goias_elevated_percentage=0.60,  # 60% elevated in Goiás (strong outbreak signal)
        other_elevated_percentage=0.15   # 15% elevated in other regions (normal baseline)
    )

    return result
