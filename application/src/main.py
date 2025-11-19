from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Any, Dict
import os
import time
import asyncio

from .db import SessionLocal, engine, Base
from .models import HemogramObservation, AlertCommunication
from .schemas import HemogramIn, HemogramOut, AlertOut
from .utils.fhir_utils import (
    extract_region_ibge_code,
    extract_leukocytes,
    extract_latitude,
    extract_longitude,
    extract_telefone,
    anonymize_observation
)
from .services.analysis import evaluate_and_create_alert_if_needed
from .services.websocket_manager import manager as ws_manager

# Create tables with retry logic
max_retries = 5
retry_delay = 2

for attempt in range(max_retries):
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")
        break
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"⚠ Database connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
        else:
            print(f"✗ Failed to connect to database after {max_retries} attempts")
            raise

app = FastAPI(title="Hemogram Monitoring API", version="0.1.0")

# Simple permissive CORS for local usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    """Serve the heatmap visualization page"""
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    return FileResponse(os.path.join(static_path, "heatmap.html"))


@app.websocket("/ws")
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


@app.post("/observations", response_model=HemogramOut)
async def receive_observation(obs: HemogramIn, db: Session = Depends(get_db)):
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


@app.get("/alerts", response_model=List[AlertOut])
def list_alerts(db: Session = Depends(get_db)):
    rows = db.execute(select(AlertCommunication).order_by(AlertCommunication.created_at.desc())).scalars().all()
    return [
        AlertOut(
            id=row.id,
            region_ibge_code=row.region_ibge_code,
            summary=row.summary,
            fhir_communication=row.fhir_communication,
        )
        for row in rows
    ]


@app.get("/heatmap-data")
def get_heatmap_data(db: Session = Depends(get_db)):
    """
    Returns observation data for heatmap visualization.
    Filters out records without coordinates.
    Includes aggregated region statistics (case count and outbreak status).
    ALL BUSINESS LOGIC CENTRALIZED HERE - frontend just renders.
    """
    from datetime import datetime, timedelta, timezone
    from .services.geospatial import compute_outbreak_regions

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


@app.post("/seed-data")
async def seed_test_data(db: Session = Depends(get_db), count: int = 3000):
    """
    Generate synthetic test data for demonstration purposes.
    Creates hemogram observations distributed across Brazil,
    with specific patterns in Goiás to trigger an alert.

    NOW GENERATES IN REAL-TIME: Each observation is created with 0.5s interval
    to allow real-time visualization on the heatmap.

    Query params:
        count: Total number of observations to generate (default: 3000)

    Returns:
        Statistics about the generated data and alerts created
    """
    from .utils.data_generator import generate_bulk_test_data
    from .services.analysis import compute_region_stats

    if count < 100 or count > 10000:
        raise HTTPException(status_code=400, detail="Count must be between 100 and 10000")

    # Generate synthetic FHIR observations
    observations = generate_bulk_test_data(
        total_count=count,
        goias_percentage=0.15,  # 15% from Goiás
        goias_elevated_percentage=0.50,  # 50% elevated in Goiás (triggers alert)
        other_elevated_percentage=0.15  # 15% elevated in other regions (normal)
    )

    # Insert observations one by one with real-time updates
    inserted_count = 0
    region_counts: Dict[str, int] = {}
    alerts_created = []
    regions_checked_for_alerts = set()

    print(f"Iniciando geração em tempo real de {count} observações...")

    for i, obs_data in enumerate(observations):
        region_ibge_code = extract_region_ibge_code(obs_data) or "unknown"
        leukocytes = extract_leukocytes(obs_data)
        latitude = extract_latitude(obs_data)
        longitude = extract_longitude(obs_data)
        telefone = extract_telefone(obs_data)

        sanitized = anonymize_observation(obs_data)

        record = HemogramObservation(
            fhir_id=obs_data.get("id") or None,
            region_ibge_code=region_ibge_code,
            leukocytes=leukocytes,
            latitude=latitude,
            longitude=longitude,
            telefone=telefone,
            raw=sanitized,
        )

        # Set received_at to the effectiveDateTime from the observation
        if "effectiveDateTime" in obs_data:
            from dateutil import parser as dateparser
            record.received_at = dateparser.parse(obs_data["effectiveDateTime"])

        db.add(record)
        db.commit()  # Commit immediately to make it available
        db.refresh(record)

        inserted_count += 1
        region_counts[region_ibge_code] = region_counts.get(region_ibge_code, 0) + 1

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

        # Check for alerts every 50 observations or when we have enough data from a region
        if (i + 1) % 50 == 0 or region_counts[region_ibge_code] >= 20:
            if region_ibge_code not in regions_checked_for_alerts:
                alert = evaluate_and_create_alert_if_needed(db, region_ibge_code)
                if alert:
                    alerts_created.append({
                        "region": region_ibge_code,
                        "summary": alert.summary,
                        "id": alert.id
                    })
                    # Send WebSocket notification for outbreak alert
                    alert_data = {
                        "id": alert.id,
                        "region": alert.region_ibge_code,
                        "summary": alert.summary,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None
                    }
                    await ws_manager.send_outbreak_alert_event(alert_data)
                    regions_checked_for_alerts.add(region_ibge_code)

        # Wait 0.5 seconds before next observation for real-time visualization
        await asyncio.sleep(0.05)

        # Log progress every 100 observations
        if (i + 1) % 100 == 0:
            print(f"Progresso: {i + 1}/{count} observações geradas")

    # Final check for alerts on all regions
    print("Verificação final de alertas em todas as regiões...")
    unique_regions = set(region_counts.keys())

    for region_code in unique_regions:
        if region_code not in regions_checked_for_alerts:
            alert = evaluate_and_create_alert_if_needed(db, region_code)
            if alert:
                alerts_created.append({
                    "region": region_code,
                    "summary": alert.summary,
                    "id": alert.id
                })
                # Send WebSocket notification for outbreak alert
                alert_data = {
                    "id": alert.id,
                    "region": alert.region_ibge_code,
                    "summary": alert.summary,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None
                }
                await ws_manager.send_outbreak_alert_event(alert_data)

    # Get detailed stats for Goiás
    goias_stats = compute_region_stats(db, "5208707")

    # Send final WebSocket notification to refresh all data
    await ws_manager.send_data_refresh_event()

    print(f"✓ Geração em tempo real concluída: {inserted_count} observações, {len(alerts_created)} alertas")

    return {
        "status": "success",
        "inserted_count": inserted_count,
        "regions_processed": len(unique_regions),
        "region_distribution": region_counts,
        "alerts_created": len(alerts_created),
        "alerts": alerts_created,
        "goias_stats": goias_stats,
        "message": f"Successfully generated {inserted_count} hemogram observations in real-time. "
                   f"Created {len(alerts_created)} alert(s)."
    }
