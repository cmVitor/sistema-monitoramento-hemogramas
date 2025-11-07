from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Any, Dict
import os
import time

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


@app.post("/observations", response_model=HemogramOut)
def receive_observation(obs: HemogramIn, db: Session = Depends(get_db)):
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
    evaluate_and_create_alert_if_needed(db, region_ibge_code)

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
    """
    rows = db.execute(
        select(HemogramObservation)
        .where(HemogramObservation.latitude.isnot(None))
        .where(HemogramObservation.longitude.isnot(None))
        .order_by(HemogramObservation.received_at.desc())
    ).scalars().all()

    return [
        {
            "lat": row.latitude,
            "lng": row.longitude,
            "intensity": row.leukocytes if row.leukocytes else 1.0,
            "region": row.region_ibge_code,
            "received_at": row.received_at.isoformat() if row.received_at else None
        }
        for row in rows
    ]
