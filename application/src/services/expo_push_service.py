"""
Expo Push Notifications Service

Serviço para enviar notificações push via Expo Push Notification Service.
Complementa o Socket.IO para quando o app está em background.
"""
import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class ExpoPushService:
    """
    Serviço para enviar push notifications via Expo.

    Use quando:
    - App está em background/fechado
    - Notificações críticas que precisam chegar sempre

    Use Socket.IO quando:
    - App está em foreground
    - Dados em tempo real (localização, chat, etc)
    - Latência baixa é crítica
    """

    def __init__(self):
        self.session = requests.Session()

    def send_push_notification(
        self,
        expo_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict] = None,
        priority: str = "high"
    ) -> Dict:
        """
        Envia push notification para um ou mais dispositivos.

        Args:
            expo_tokens: Lista de tokens Expo Push (ExponentPushToken[...])
            title: Título da notificação
            body: Corpo da notificação
            data: Dados adicionais (dict)
            priority: 'default' ou 'high'

        Returns:
            Dict com resultado do envio
        """
        try:
            messages = []
            for token in expo_tokens:
                # Validar formato do token
                if not token.startswith('ExponentPushToken['):
                    logger.warning(f"Token inválido: {token}")
                    continue

                messages.append({
                    'to': token,
                    'title': title,
                    'body': body,
                    'data': data or {},
                    'priority': priority,
                    'sound': 'default',
                    'badge': 1
                })

            if not messages:
                logger.warning("Nenhum token válido para enviar")
                return {'status': 'error', 'message': 'No valid tokens'}

            # Enviar para Expo Push Service
            response = self.session.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            # Verificar erros
            data_result = result.get('data', [])
            errors = [r for r in data_result if r.get('status') == 'error']

            if errors:
                logger.error(f"Erros ao enviar push: {errors}")

            success_count = len([r for r in data_result if r.get('status') == 'ok'])
            logger.info(f"✅ Push enviado: {success_count}/{len(messages)} sucesso")

            return {
                'status': 'success',
                'sent': success_count,
                'total': len(messages),
                'errors': errors
            }

        except Exception as e:
            logger.error(f"❌ Erro ao enviar push notification: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def send_outbreak_alert(
        self,
        expo_tokens: List[str],
        location: str,
        severity: str = "high"
    ) -> Dict:
        """
        Envia alerta de surto via push notification.

        Args:
            expo_tokens: Lista de tokens dos usuários
            location: Nome da localização
            severity: Severidade ('low', 'medium', 'high')

        Returns:
            Resultado do envio
        """
        title = "🚨 ALERTA DE SURTO"

        if severity == "high":
            body = f"ATENÇÃO! Surto ativo detectado em {location}. Evite a região."
        elif severity == "medium":
            body = f"Surto reportado em {location}. Mantenha precauções."
        else:
            body = f"Alerta de monitoramento em {location}."

        return self.send_push_notification(
            expo_tokens=expo_tokens,
            title=title,
            body=body,
            data={
                'type': 'outbreak_alert',
                'location': location,
                'severity': severity
            },
            priority='high'
        )

    def send_nearby_alert(
        self,
        expo_tokens: List[str],
        distance_km: float
    ) -> Dict:
        """
        Alerta usuário que está próximo a zona de surto.

        Args:
            expo_tokens: Tokens dos usuários próximos
            distance_km: Distância da zona de surto

        Returns:
            Resultado do envio
        """
        return self.send_push_notification(
            expo_tokens=expo_tokens,
            title="⚠️ Zona de Surto Próxima",
            body=f"Você está a {distance_km:.1f}km de uma zona de surto ativa. Mantenha distância.",
            data={
                'type': 'nearby_alert',
                'distance': distance_km
            },
            priority='high'
        )

    def send_batch_notifications(
        self,
        notifications: List[Dict]
    ) -> Dict:
        """
        Envia múltiplas notificações em batch.

        Args:
            notifications: Lista de dicts com:
                - expo_token: str
                - title: str
                - body: str
                - data: dict (opcional)

        Returns:
            Resultado do envio
        """
        try:
            messages = [
                {
                    'to': n['expo_token'],
                    'title': n['title'],
                    'body': n['body'],
                    'data': n.get('data', {}),
                    'sound': 'default'
                }
                for n in notifications
                if n['expo_token'].startswith('ExponentPushToken[')
            ]

            if not messages:
                return {'status': 'error', 'message': 'No valid tokens'}

            # Expo aceita até 100 mensagens por request
            batch_size = 100
            total_sent = 0
            total_errors = []

            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]

                response = self.session.post(
                    EXPO_PUSH_URL,
                    json=batch,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

                response.raise_for_status()
                result = response.json()

                data_result = result.get('data', [])
                total_sent += len([r for r in data_result if r.get('status') == 'ok'])
                total_errors.extend([r for r in data_result if r.get('status') == 'error'])

            logger.info(f"✅ Batch push enviado: {total_sent}/{len(messages)}")

            return {
                'status': 'success',
                'sent': total_sent,
                'total': len(messages),
                'errors': total_errors
            }

        except Exception as e:
            logger.error(f"❌ Erro ao enviar batch: {e}")
            return {'status': 'error', 'message': str(e)}


# Instância global
expo_push_service = ExpoPushService()
