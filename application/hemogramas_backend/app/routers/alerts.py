from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db, CollectiveAlertDB
from app.models.alert_models import CollectiveAlert
from datetime import datetime

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("/", response_model=List[CollectiveAlert])
def get_alerts(region: Optional[str] = None, 
               parameter: Optional[str] = None,
               start_date: Optional[datetime] = None,
               investigated: Optional[bool] = None,
               db: Session = Depends(get_db)):
    """Consulta alertas coletivos"""
    query = db.query(CollectiveAlertDB)
    
    if region:
        query = query.filter(CollectiveAlertDB.region == region)
    if parameter:
        query = query.filter(CollectiveAlertDB.parameter == parameter)
    if start_date:
        query = query.filter(CollectiveAlertDB.timestamp >= start_date)
    if investigated is not None:
        query = query.filter(CollectiveAlertDB.is_investigated == investigated)
    
    return query.order_by(CollectiveAlertDB.timestamp.desc()).all()

@router.post("/{alert_id}/investigate")
def mark_alert_investigated(alert_id: str, db: Session = Depends(get_db)):
    """Marca alerta como investigado"""
    alert = db.query(CollectiveAlertDB).filter(CollectiveAlertDB.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_investigated = True
    db.commit()
    
    return {"status": "investigated", "alert_id": alert_id}

@router.get("/stats/regions")
def get_region_stats(db: Session = Depends(get_db)):
    """Estatísticas por região"""
    # Implementar agregações por região
    pass