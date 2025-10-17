import httpx
from typing import List
from app.models.alert_models import CollectiveAlert
from app.database.database import CollectiveAlertDB
from config import settings

class AlertService:
    def __init__(self):
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
    
    async def send_push_notification(self, alert: CollectiveAlert, device_tokens: List[str]):
        """Envia notificação push para dispositivos móveis"""
        message = {
            "registration_ids": device_tokens,
            "notification": {
                "title": f"Alerta Coletivo - {alert.region}",
                "body": self._format_alert_message(alert),
                "click_action": "OPEN_ALERT_DETAIL"
            },
            "data": {
                "alert_id": str(alert.id),
                "region": alert.region,
                "parameter": alert.parameter,
                "alert_level": alert.alert_level
            }
        }
        
        # Em produção, adicionar headers de autenticação do FCM
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.fcm_url, json=message)
                return response.status_code == 200
            except Exception as e:
                print(f"Erro ao enviar notificação: {e}")
                return False
    
    def _format_alert_message(self, alert: CollectiveAlert) -> str:
        """Formata mensagem da notificação"""
        return (f"{alert.parameter.capitalize()} alterados em {alert.region}. "
                f"{alert.alert_samples}/{alert.total_samples} exames com alerta "
                f"({alert.alert_proportion:.1%}). Aumento de {alert.trend_increase:.1%}.")
    
    def create_fhir_communication(self, alert: CollectiveAlert) -> dict:
        """Cria recurso FHIR Communication para o alerta"""
        return {
            "resourceType": "Communication",
            "status": "completed",
            "subject": {
                "reference": f"Location/{alert.region}",
                "display": f"Região {alert.region}"
            },
            "sent": alert.timestamp.isoformat(),
            "payload": [
                {
                    "contentString": self._format_alert_message(alert)
                }
            ],
            "reasonCode": [
                {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "420008001",
                        "display": "Epidemic outbreak monitoring"
                    }]
                }
            ]
        }