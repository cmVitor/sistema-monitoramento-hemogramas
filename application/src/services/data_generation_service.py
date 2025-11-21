"""
Data generation service for creating synthetic test data.

This service handles the business logic of generating hemogram observations
for testing and demonstration purposes.
"""
import asyncio
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from dateutil import parser as dateparser

from ..models import HemogramObservation
from ..utils.data_generator import generate_bulk_test_data
from ..utils.fhir_utils import (
    extract_region_ibge_code,
    extract_leukocytes,
    extract_latitude,
    extract_longitude,
    extract_telefone,
    anonymize_observation
)
from .analysis import evaluate_and_create_alert_if_needed, compute_region_stats
from .websocket_manager import manager as ws_manager


async def generate_synthetic_data(
    db: Session,
    count: int,
    goias_percentage: float = 0.15,
    goias_elevated_percentage: float = 0.50,
    other_elevated_percentage: float = 0.15,
    delay_seconds: float = 0.05
) -> Dict[str, Any]:
    """
    Generate synthetic hemogram observations for testing.

    This function creates realistic test data distributed across Brazil,
    with configurable patterns to trigger outbreak alerts.

    Args:
        db: Database session
        count: Total number of observations to generate
        goias_percentage: Percentage of observations from Goiás (default: 0.15)
        goias_elevated_percentage: Percentage of elevated leukocytes in Goiás (default: 0.50)
        other_elevated_percentage: Percentage of elevated leukocytes in other regions (default: 0.15)
        delay_seconds: Delay between observations for real-time visualization (default: 0.05)

    Returns:
        Dictionary with generation statistics:
        - status: Success status
        - inserted_count: Number of observations created
        - regions_processed: Number of unique regions
        - region_distribution: Count per region
        - alerts_created: Number of alerts generated
        - alerts: Details of each alert
        - goias_stats: Detailed statistics for Goiás region
        - message: Summary message
    """
    print(f"📊 Iniciando geração de {count} observações sintéticas...")

    # Generate synthetic FHIR observations
    observations = generate_bulk_test_data(
        total_count=count,
        goias_percentage=goias_percentage,
        goias_elevated_percentage=goias_elevated_percentage,
        other_elevated_percentage=other_elevated_percentage
    )

    # Track statistics
    inserted_count = 0
    region_counts: Dict[str, int] = {}
    alerts_created: List[Dict[str, Any]] = []
    regions_checked_for_alerts = set()

    # Process each observation
    for i, obs_data in enumerate(observations):
        # Extract data from FHIR observation
        region_ibge_code = extract_region_ibge_code(obs_data) or "unknown"
        leukocytes = extract_leukocytes(obs_data)
        latitude = extract_latitude(obs_data)
        longitude = extract_longitude(obs_data)
        telefone = extract_telefone(obs_data)

        # Anonymize sensitive data
        sanitized = anonymize_observation(obs_data)

        # Create database record
        record = HemogramObservation(
            fhir_id=obs_data.get("id") or None,
            region_ibge_code=region_ibge_code,
            leukocytes=leukocytes,
            latitude=latitude,
            longitude=longitude,
            telefone=telefone,
            raw=sanitized,
        )

        # Set received_at from effectiveDateTime
        if "effectiveDateTime" in obs_data:
            record.received_at = dateparser.parse(obs_data["effectiveDateTime"])

        # Persist to database
        db.add(record)
        db.commit()
        db.refresh(record)

        # Update statistics
        inserted_count += 1
        region_counts[region_ibge_code] = region_counts.get(region_ibge_code, 0) + 1

        # Send WebSocket notification
        await _send_observation_notification(record)

        # Check for alerts periodically
        if (i + 1) % 50 == 0 or region_counts[region_ibge_code] >= 20:
            alert = await _check_and_create_alert(
                db, region_ibge_code, regions_checked_for_alerts
            )
            if alert:
                alerts_created.append(alert)
                regions_checked_for_alerts.add(region_ibge_code)

        # Delay for real-time visualization
        await asyncio.sleep(delay_seconds)

        # Log progress
        if (i + 1) % 100 == 0:
            print(f"   ⏳ Progresso: {i + 1}/{count} observações")

    # Final alert check for all regions
    print("   🔍 Verificação final de alertas...")
    unique_regions = set(region_counts.keys())

    for region_code in unique_regions:
        if region_code not in regions_checked_for_alerts:
            alert = await _check_and_create_alert(db, region_code, set())
            if alert:
                alerts_created.append(alert)

    # Get detailed stats for Goiás
    goias_stats = compute_region_stats(db, "5208707")

    # Send final refresh notification
    await ws_manager.send_data_refresh_event()

    print(f"   ✅ Geração concluída: {inserted_count} observações, {len(alerts_created)} alertas")

    return {
        "status": "success",
        "inserted_count": inserted_count,
        "regions_processed": len(unique_regions),
        "region_distribution": region_counts,
        "alerts_created": len(alerts_created),
        "alerts": alerts_created,
        "goias_stats": goias_stats,
        "message": (
            f"Successfully generated {inserted_count} hemogram observations in real-time. "
            f"Created {len(alerts_created)} alert(s)."
        )
    }


async def _send_observation_notification(record: HemogramObservation) -> None:
    """
    Send WebSocket notification for a new observation.

    Args:
        record: The hemogram observation record
    """
    observation_data = {
        "id": record.id,
        "region": record.region_ibge_code,
        "leukocytes": record.leukocytes,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "received_at": record.received_at.isoformat() if record.received_at else None
    }
    await ws_manager.send_new_observation_event(observation_data)


async def _check_and_create_alert(
    db: Session,
    region_ibge_code: str,
    regions_checked: set
) -> Dict[str, Any] | None:
    """
    Check if an alert should be created for a region and send notification.

    Args:
        db: Database session
        region_ibge_code: Region IBGE code
        regions_checked: Set of regions already checked

    Returns:
        Alert data if created, None otherwise
    """
    if region_ibge_code in regions_checked:
        return None

    alert = evaluate_and_create_alert_if_needed(db, region_ibge_code)

    if alert:
        # Send WebSocket notification
        alert_data = {
            "id": alert.id,
            "region": alert.region_ibge_code,
            "summary": alert.summary,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        }
        await ws_manager.send_outbreak_alert_event(alert_data)

        return {
            "region": region_ibge_code,
            "summary": alert.summary,
            "id": alert.id
        }

    return None
