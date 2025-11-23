from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean
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

class MobileDevice(Base):
    __tablename__ = "mobile_devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)
    fcm_token = Column(String, nullable=False)
    platform = Column(String, nullable=False)  # 'ios' or 'android'
    last_location_lat = Column(Float, nullable=True)
    last_location_lng = Column(Float, nullable=True)
    last_location_update = Column(DateTime(timezone=True), nullable=True)
    last_alert_sent = Column(DateTime(timezone=True), nullable=True)  # Timestamp of last outbreak alert
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
