from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AlertLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class CollectiveAlert(BaseModel):
    id: Optional[str] = None
    timestamp: datetime
    region: str
    parameter: str
    total_samples: int
    alert_samples: int
    alert_proportion: float
    current_mean: float
    previous_mean: float
    trend_increase: float
    alert_level: AlertLevel
    contributing_observations: List[str]
    suggested_action: str
    is_investigated: bool = False

class GeographicRegion(BaseModel):
    ibge_code: str
    name: str
    population: Optional[int] = None
    region_type: str  # municipio, distrito_sanitario, etc.

class SlidingWindowStats(BaseModel):
    region: str
    parameter: str
    window_start: datetime
    window_end: datetime
    total_count: int
    alert_count: int
    mean_value: float
    std_dev: float
    previous_mean: Optional[float] = None
    trend: Optional[float] = None