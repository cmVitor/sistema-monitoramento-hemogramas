from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Any, Dict

from .db import SessionLocal, engine, Base
from .models import HemogramObservation, AlertCommunication
from .schemas import HemogramIn, HemogramOut, AlertOut
from .utils.fhir_utils import extract_region_ibge_code, extract_leukocytes, anonymize_observation
from .services.analysis import evaluate_and_create_alert_if_needed

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hemogram Monitoring API", version="0.1.0")

# Simple permissive CORS for local usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/observations", response_model=HemogramOut)
def receive_observation(obs: HemogramIn, db: Session = Depends(get_db)):
    data: Dict[str, Any] = obs.model_dump()
    if data.get("resourceType") != "Observation":
        raise HTTPException(status_code=400, detail="Expected FHIR Observation")

    region_ibge_code = extract_region_ibge_code(data) or "unknown"
    leukocytes = extract_leukocytes(data)

    sanitized = anonymize_observation(data)

    record = HemogramObservation(
        fhir_id=data.get("id") or None,
        region_ibge_code=region_ibge_code,
        leukocytes=leukocytes,
        raw=sanitized,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # After saving, evaluate for alerts for that region
    evaluate_and_create_alert_if_needed(db, region_ibge_code)

    return HemogramOut(id=record.id, region_ibge_code=record.region_ibge_code, leukocytes=record.leukocytes)


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
