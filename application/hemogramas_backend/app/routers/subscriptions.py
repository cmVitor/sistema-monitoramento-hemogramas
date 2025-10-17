from fastapi import APIRouter, Depends, HTTPException
from app.services.fhir_service import FHIRService

router = APIRouter(prefix="/fhir", tags=["Subscriptions"])
fhir_service = FHIRService()

@router.post("/Subscription")
async def create_subscription():
    """Cria uma nova subscription FHIR"""
    try:
        # Criteria para receber Observations de hemogramas
        criteria = "Observation?category=laboratory&code=http://loinc.org|58410-2"
        subscription = await fhir_service.create_subscription(criteria)
        return subscription
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating subscription: {str(e)}")