from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ObservationStatus(str, Enum):
    REGISTERED = "registered"
    PRELIMINARY = "preliminary"
    FINAL = "final"
    AMENDED = "amended"

class ParameterType(str, Enum):
    LEUKOCYTES = "leukocytes"
    HEMOGLOBIN = "hemoglobin"
    PLATELETS = "platelets"
    HEMATOCRIT = "hematocrit"

class FHIRObservation(BaseModel):
    resourceType: str = "Observation"
    id: Optional[str] = None
    status: ObservationStatus
    category: List[Dict] = [{
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "laboratory",
            "display": "Laboratory"
        }]
    }]
    code: Dict
    subject: Dict
    effectiveDateTime: str
    valueQuantity: Optional[Dict] = None
    valueString: Optional[str] = None
    component: Optional[List[Dict]] = None
    extension: Optional[List[Dict]] = None

class FHIRSubscription(BaseModel):
    resourceType: str = "Subscription"
    status: str = "active"
    contact: Optional[List[Dict]] = None
    end: Optional[str] = None
    reason: str = "Monitor hemograms for outbreak detection"
    criteria: str
    channel: Dict