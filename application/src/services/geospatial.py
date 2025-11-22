"""
Geospatial analysis functions for outbreak detection.
Handles centroid calculation, radius computation, and geographic clustering.
"""
from typing import List, Dict, Any, Optional
from math import sqrt
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from ..models import HemogramObservation


def calculate_centroid(points: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Calculates the geographic center (centroid) of a set of points.

    Args:
        points: List of dicts with 'lat' and 'lng' keys

    Returns:
        Dict with 'lat' and 'lng' keys representing the centroid
    """
    if not points:
        return {"lat": 0.0, "lng": 0.0}

    sum_lat = sum(p["lat"] for p in points)
    sum_lng = sum(p["lng"] for p in points)

    return {
        "lat": sum_lat / len(points),
        "lng": sum_lng / len(points)
    }


def calculate_radius(points: List[Dict[str, float]], centroid: Dict[str, float]) -> float:
    """
    Calculates the outbreak radius in meters.

    Finds the maximum distance from centroid to any point,
    then applies a 30% safety margin and converts to meters.

    Args:
        points: List of dicts with 'lat' and 'lng' keys
        centroid: Dict with 'lat' and 'lng' keys

    Returns:
        Radius in meters
    """
    if not points:
        return 0.0

    max_distance = 0.0
    for point in points:
        distance = sqrt(
            (point["lat"] - centroid["lat"]) ** 2 +
            (point["lng"] - centroid["lng"]) ** 2
        )
        max_distance = max(max_distance, distance)

    # Convert degrees to meters (1 degree ≈ 111km) and add 30% margin
    radius_meters = max_distance * 111000 * 1.3

    return radius_meters


def compute_outbreak_regions(db: Session) -> Dict[str, Any]:
    """
    Computes outbreak information based on recent alerts.

    Returns outbreak data including:
    - centroid (lat, lng)
    - radius (in meters)
    - point count
    - observations

    Args:
        db: Database session

    Returns:
        Dict with outbreak data
    """
    from ..models import AlertCommunication

    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    # Check if there are recent alerts (last 24 hours)
    recent_alerts = db.execute(
        select(AlertCommunication)
        .where(AlertCommunication.created_at >= since_24h)
    ).scalars().all()

    if not recent_alerts:
        return {}

    # Get all observations with coordinates (last 7 days)
    since_7d = now - timedelta(days=7)
    observations = db.execute(
        select(HemogramObservation)
        .where(
            HemogramObservation.latitude.isnot(None),
            HemogramObservation.longitude.isnot(None),
            HemogramObservation.received_at >= since_7d
        )
    ).scalars().all()

    if not observations:
        return {}

    # Convert to point list
    points = [
        {"lat": obs.latitude, "lng": obs.longitude}
        for obs in observations
    ]

    # Calculate centroid and radius
    centroid = calculate_centroid(points)
    radius = calculate_radius(points, centroid)

    outbreak_data = {
        "centroid": centroid,
        "radius": radius,
        "point_count": len(points),
        "observations": [
            {
                "lat": obs.latitude,
                "lng": obs.longitude,
                "leukocytes": obs.leukocytes,
                "received_at": obs.received_at.isoformat() if obs.received_at else None
            }
            for obs in observations
        ]
    }

    return {"outbreak": outbreak_data}


def get_observations_within_radius(
    db: Session,
    center_lat: float,
    center_lng: float,
    radius_meters: float
) -> List[HemogramObservation]:
    """
    Finds all observations within a geographic radius.

    Uses simple Euclidean distance approximation.
    For more accuracy, consider using PostGIS or geopy.

    Args:
        db: Database session
        center_lat: Center latitude
        center_lng: Center longitude
        radius_meters: Radius in meters

    Returns:
        List of HemogramObservation records within radius
    """
    # Convert radius back to degrees (approximate)
    radius_degrees = radius_meters / 111000

    # Get all observations with coordinates
    query = select(HemogramObservation).where(
        HemogramObservation.latitude.isnot(None),
        HemogramObservation.longitude.isnot(None)
    )

    all_observations = db.execute(query).scalars().all()

    # Filter by distance
    nearby = []
    for obs in all_observations:
        distance = sqrt(
            (obs.latitude - center_lat) ** 2 +
            (obs.longitude - center_lng) ** 2
        )
        if distance <= radius_degrees:
            nearby.append(obs)

    return nearby
