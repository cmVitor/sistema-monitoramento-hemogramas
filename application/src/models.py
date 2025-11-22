from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from sqlalchemy.sql import func
from .db import Base

class HemogramObservation(Base):
    __tablename__ = "hemogram_observations"

    id = Column(Integer, primary_key=True, index=True)
    fhir_id = Column(String, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    leukocytes = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    raw = Column(JSON, nullable=False)

class AlertCommunication(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    summary = Column(String)
    fhir_communication = Column(JSON, nullable=False)
