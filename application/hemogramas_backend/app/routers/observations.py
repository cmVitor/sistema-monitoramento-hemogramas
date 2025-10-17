from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database.database import get_db, ObservationDB
from app.services.fhir_service import FHIRService
from app.services.analysis_service import AnalysisService
from app.models.fhir_models import FHIRObservation
from datetime import datetime

router = APIRouter(prefix="/fhir", tags=["FHIR"])
fhir_service = FHIRService()
analysis_service = AnalysisService()

@router.post("/Observation")
async def receive_observation(observation_data: Dict, background_tasks: BackgroundTasks, 
                            db: Session = Depends(get_db)):
    """Endpoint para receber Observations via subscription FHIR"""
    try:
        # Parse da observation
        observations = fhir_service.parse_observation(observation_data)
        
        if not observations:
            raise HTTPException(status_code=400, detail="Invalid observation data")
        
        saved_observations = []
        for obs in observations:
            # Verificar alerta individual
            obs.has_alert = analysis_service.check_individual_alert(obs.parameter, obs.value)
            
            # Salvar no banco
            db.add(obs)
            db.commit()
            db.refresh(obs)
            saved_observations.append(obs)
        
        # Processar análise coletiva em background
        background_tasks.add_task(process_collective_analysis, db, observations[0].region)
        
        return {"status": "processed", "count": len(saved_observations)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing observation: {str(e)}")

async def process_collective_analysis(db: Session, region: str):
    """Processa análise coletiva para uma região"""
    analysis_service = AnalysisService()
    parameters = ['leukocytes', 'hemoglobin', 'platelets', 'hematocrit']
    
    for param in parameters:
        current_stats = analysis_service.calculate_window_stats(db, region, param, datetime.now())
        if current_stats:
            alert = analysis_service.detect_collective_pattern(db, current_stats)
            if alert:
                # Salvar alerta e enviar notificação
                alert_db = CollectiveAlertDB(**alert.dict())
                db.add(alert_db)
                db.commit()
                
                # Enviar notificação (implementar)
                print(f"Alerta coletivo detectado: {alert}")

@router.get("/observations")
def get_observations(region: str = None, parameter: str = None, 
                    start_date: datetime = None, end_date: datetime = None,
                    db: Session = Depends(get_db)):
    """Consulta observations com filtros"""
    query = db.query(ObservationDB)
    
    if region:
        query = query.filter(ObservationDB.region == region)
    if parameter:
        query = query.filter(ObservationDB.parameter == parameter)
    if start_date:
        query = query.filter(ObservationDB.effective_datetime >= start_date)
    if end_date:
        query = query.filter(ObservationDB.effective_datetime <= end_date)
    
    return query.order_by(ObservationDB.effective_datetime.desc()).limit(1000).all()