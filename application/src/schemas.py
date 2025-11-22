from pydantic import BaseModel
from typing import Any, Optional, List, Literal

class HemogramIn(BaseModel):
    # Store raw FHIR Observation JSON
    resourceType: Literal["Observation"] = "Observation"
    id: Optional[str] = None
    status: Optional[str] = None
    code: Optional[Any] = None
    subject: Optional[Any] = None
    effectiveDateTime: Optional[str] = None
    issued: Optional[str] = None
    valueQuantity: Optional[Any] = None
    component: Optional[List[Any]] = None
    performer: Optional[List[Any]] = None
    encounter: Optional[Any] = None
    category: Optional[List[Any]] = None
    meta: Optional[Any] = None
    extension: Optional[List[Any]] = None
    identifier: Optional[List[Any]] = None

class HemogramOut(BaseModel):
    id: int
    leukocytes: float | None
    latitude: float | None
    longitude: float | None

class AlertOut(BaseModel):
    id: int
    summary: str
    fhir_communication: Any