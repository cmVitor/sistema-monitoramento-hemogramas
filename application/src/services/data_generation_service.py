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
    extract_leukocytes,
    extract_latitude,
    extract_longitude,
    anonymize_observation
)
from .analysis import evaluate_and_create_alert_if_needed
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
    alerts_created: List[Dict[str, Any]] = []

    # Process each observation
    for i, obs_data in enumerate(observations):
        # Extract data from FHIR observation
        leukocytes = extract_leukocytes(obs_data)
        latitude = extract_latitude(obs_data)
        longitude = extract_longitude(obs_data)

        # Anonymize sensitive data
        sanitized = anonymize_observation(obs_data)

        # Create database record
        record = HemogramObservation(
            fhir_id=obs_data.get("id") or None,
            leukocytes=leukocytes,
            latitude=latitude,
            longitude=longitude,
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

        # Send WebSocket notification
        await _send_observation_notification(record)

        # Check for alerts periodically
        if (i + 1) % 50 == 0:
            alert = await _check_and_create_alert(db)
            if alert:
                alerts_created.append(alert)

        # Delay for real-time visualization
        await asyncio.sleep(delay_seconds)

        # Log progress
        if (i + 1) % 100 == 0:
            print(f"   ⏳ Progresso: {i + 1}/{count} observações")

    # Final alert check
    print("   🔍 Verificação final de alertas...")
    alert = await _check_and_create_alert(db)
    if alert:
        alerts_created.append(alert)

    # Send final refresh notification
    await ws_manager.send_data_refresh_event()

    print(f"   ✅ Geração concluída: {inserted_count} observações, {len(alerts_created)} alertas")

    return {
        "status": "success",
        "inserted_count": inserted_count,
        "alerts_created": len(alerts_created),
        "alerts": alerts_created,
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
        "leukocytes": record.leukocytes,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "received_at": record.received_at.isoformat() if record.received_at else None
    }
    await ws_manager.send_new_observation_event(observation_data)


async def _check_and_create_alert(
    db: Session
) -> Dict[str, Any] | None:
    """
    Check if an alert should be created and send notification.

    Args:
        db: Database session

    Returns:
        Alert data if created, None otherwise
    """
    alert = evaluate_and_create_alert_if_needed(db)

    if alert:
        # Send WebSocket notification
        alert_data = {
            "id": alert.id,
            "summary": alert.summary,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        }
        await ws_manager.send_outbreak_alert_event(alert_data)

        return {
            "summary": alert.summary,
            "id": alert.id
        }

    return None
