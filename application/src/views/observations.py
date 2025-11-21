"""
Observations endpoints for receiving and managing hemogram data.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import asyncio
from typing import Dict, Any

from ..db import SessionLocal
from ..schemas import HemogramIn, HemogramOut
from ..models import HemogramObservation
from ..utils.fhir_utils import (
    extract_region_ibge_code,
    extract_leukocytes,
    extract_latitude,
    extract_longitude,
    extract_telefone,
    anonymize_observation
)
from ..services.analysis import evaluate_and_create_alert_if_needed
from ..services.websocket_manager import manager as ws_manager

router = APIRouter(tags=["Observations"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint para atualizações em tempo real.
    Envia notificações de novas observações e alertas de surtos.
    """
    await ws_manager.connect(websocket)
    try:
        # Keep connection alive and listen for messages (heartbeat)
        while True:
            # Wait for any message from client (used as heartbeat)
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send ping to check if connection is still alive
                await websocket.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@router.post("/observations", response_model=HemogramOut)
async def receive_observation(obs: HemogramIn, db: Session = Depends(get_db)):
    """
    Receive and process a FHIR Observation (hemogram).

    - Validates FHIR resource type
    - Extracts hemogram data
    - Anonymizes patient information
    - Stores in database
    - Evaluates for alerts
    - Sends real-time notifications via WebSocket
    """
    data: Dict[str, Any] = obs.model_dump()
    if data.get("resourceType") != "Observation":
        raise HTTPException(status_code=400, detail="Expected FHIR Observation")

    region_ibge_code = extract_region_ibge_code(data) or "unknown"
    leukocytes = extract_leukocytes(data)
    latitude = extract_latitude(data)
    longitude = extract_longitude(data)
    telefone = extract_telefone(data)

    sanitized = anonymize_observation(data)

    record = HemogramObservation(
        fhir_id=data.get("id") or None,
        region_ibge_code=region_ibge_code,
        leukocytes=leukocytes,
        latitude=latitude,
        longitude=longitude,
        telefone=telefone,
        raw=sanitized,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # After saving, evaluate for alerts for that region
    alert = evaluate_and_create_alert_if_needed(db, region_ibge_code)

    # Send WebSocket notification for new observation
    observation_data = {
        "id": record.id,
        "region": record.region_ibge_code,
        "leukocytes": record.leukocytes,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "received_at": record.received_at.isoformat() if record.received_at else None
    }
    await ws_manager.send_new_observation_event(observation_data)

    # Send WebSocket notification if alert was created
    if alert:
        alert_data = {
            "id": alert.id,
            "region": alert.region_ibge_code,
            "summary": alert.summary,
            "created_at": alert.created_at.isoformat() if alert.created_at else None
        }
        await ws_manager.send_outbreak_alert_event(alert_data)

    return HemogramOut(
        id=record.id,
        region_ibge_code=record.region_ibge_code,
        leukocytes=record.leukocytes,
        latitude=record.latitude,
        longitude=record.longitude,
        telefone=record.telefone
    )
