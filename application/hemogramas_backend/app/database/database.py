from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ObservationDB(Base):
    __tablename__ = "observations"
    
    id = Column(String, primary_key=True, index=True)
    fhir_id = Column(String, unique=True, index=True)
    status = Column(String)
    region = Column(String, index=True)
    parameter = Column(String, index=True)
    value = Column(Float)
    unit = Column(String)
    effective_datetime = Column(DateTime)
    received_at = Column(DateTime)
    has_alert = Column(Boolean, default=False)
    raw_data = Column(JSON)

class CollectiveAlertDB(Base):
    __tablename__ = "collective_alerts"
    
    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime)
    region = Column(String, index=True)
    parameter = Column(String, index=True)
    total_samples = Column(Integer)
    alert_samples = Column(Integer)
    alert_proportion = Column(Float)
    current_mean = Column(Float)
    previous_mean = Column(Float)
    trend_increase = Column(Float)
    alert_level = Column(String)
    contributing_observations = Column(JSON)
    suggested_action = Column(String)
    is_investigated = Column(Boolean, default=False)

class SlidingWindowDB(Base):
    __tablename__ = "sliding_windows"
    
    id = Column(String, primary_key=True, index=True)
    region = Column(String, index=True)
    parameter = Column(String, index=True)
    window_start = Column(DateTime)
    window_end = Column(DateTime)
    stats = Column(JSON)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)