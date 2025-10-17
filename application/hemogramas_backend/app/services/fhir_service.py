import json
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.fhir_models import FHIRObservation, FHIRSubscription
from app.database.database import get_db, ObservationDB
from config import settings

class FHIRService:
    def __init__(self):
        self.base_url = settings.fhir_base_url
    
    async def create_subscription(self, criteria: str) -> Dict:
        """Cria uma subscription FHIR para receber Observations"""
        subscription = FHIRSubscription(
            criteria=criteria,
            channel={
                "type": "rest-hook",
                "endpoint": settings.subscription_endpoint,
                "payload": "application/fhir+json"
            }
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/Subscription",
                json=subscription.dict(),
                headers={"Content-Type": "application/fhir+json"}
            )
            return response.json()
    
    def parse_observation(self, observation_data: Dict) -> Optional[ObservationDB]:
        """Parse de um recurso FHIR Observation para o modelo interno"""
        try:
            # Extrair região do código IBGE (assumindo extensão customizada)
            region = self._extract_region(observation_data)
            
            # Extrair parâmetros do hemograma
            parameters = self._extract_parameters(observation_data)
            
            observations = []
            for param_type, value, unit in parameters:
                obs = ObservationDB(
                    fhir_id=observation_data.get('id'),
                    status=observation_data.get('status'),
                    region=region,
                    parameter=param_type.value,
                    value=value,
                    unit=unit,
                    effective_datetime=datetime.fromisoformat(
                        observation_data.get('effectiveDateTime').replace('Z', '+00:00')
                    ),
                    received_at=datetime.now(),
                    raw_data=observation_data
                )
                observations.append(obs)
            
            return observations
            
        except Exception as e:
            print(f"Erro ao parse observation: {e}")
            return None
    
    def _extract_region(self, observation: Dict) -> str:
        """Extrai código da região geográfica"""
        # Implementar lógica para extrair código IBGE ou região
        # Por enquanto, retorna um valor padrão
        extensions = observation.get('extension', [])
        for ext in extensions:
            if ext.get('url') == 'http://example.org/ibge-code':
                return ext.get('valueString', 'unknown')
        return 'unknown'
    
    def _extract_parameters(self, observation: Dict) -> List[tuple]:
        """Extrai parâmetros do hemograma do recurso Observation"""
        parameters = []
        
        # Verificar se é uma observação com componentes (painel de hemograma)
        components = observation.get('component', [])
        
        for component in components:
            code = component.get('code', {})
            codings = code.get('coding', [])
            
            for coding in codings:
                code_value = coding.get('code', '').lower()
                
                if 'leukocyte' in code_value or 'wbc' in code_value:
                    value_quant = component.get('valueQuantity', {})
                    parameters.append((
                        'leukocytes',
                        value_quant.get('value'),
                        value_quant.get('unit', '10^3/μL')
                    ))
                elif 'hemoglobin' in code_value or 'hgb' in code_value:
                    value_quant = component.get('valueQuantity', {})
                    parameters.append((
                        'hemoglobin',
                        value_quant.get('value'),
                        value_quant.get('unit', 'g/dL')
                    ))
                elif 'platelet' in code_value:
                    value_quant = component.get('valueQuantity', {})
                    parameters.append((
                        'platelets',
                        value_quant.get('value'),
                        value_quant.get('unit', '10^3/μL')
                    ))
                elif 'hematocrit' in code_value or 'hct' in code_value:
                    value_quant = component.get('valueQuantity', {})
                    parameters.append((
                        'hematocrit',
                        value_quant.get('value'),
                        value_quant.get('unit', '%')
                    ))
        
        return parameters