"""
Notification service using Expo Push Notifications.
Free service that scales to millions of devices without server overhead.
"""
import requests
from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class NotificationService:
    """Service for sending push notifications via Expo."""

    @staticmethod
    def send_notification(
        expo_token: str,
        title: str,
        body: str,
        data: Dict[str, Any] = None
    ) -> bool:
        """
        Send a push notification to a single device.

        Args:
            expo_token: Expo push token (ExponentPushToken[...])
            title: Notification title
            body: Notification message
            data: Optional custom data

        Returns:
            True if sent successfully, False otherwise
        """
        if not expo_token.startswith('ExponentPushToken'):
            logger.warning(f"Invalid Expo token format: {expo_token}")
            return False

        payload = {
            "to": expo_token,
            "title": title,
            "body": body,
            "sound": "default",
            "priority": "high",
            "channelId": "outbreak-alerts",
        }

        if data:
            payload["data"] = data

        try:
            response = requests.post(
                EXPO_PUSH_URL,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("data"):
                    status = result["data"][0].get("status")
                    if status == "ok":
                        logger.info(f"Notification sent successfully to {expo_token[:20]}...")
                        return True
                    else:
                        logger.error(f"Notification failed: {result['data'][0]}")
                        return False
            else:
                logger.error(f"Expo API returned status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    @staticmethod
    def send_batch_notifications(
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, Any] = None
    ) -> Dict[str, int]:
        """
        Send push notifications to multiple devices in a single request.
        Expo supports up to 100 tokens per request.

        Args:
            tokens: List of Expo push tokens
            title: Notification title
            body: Notification message
            data: Optional custom data

        Returns:
            Dict with success and failure counts
        """
        if not tokens:
            return {"success": 0, "failed": 0}

        # Filter invalid tokens
        valid_tokens = [t for t in tokens if t.startswith('ExponentPushToken')]

        if not valid_tokens:
            logger.warning("No valid Expo tokens provided")
            return {"success": 0, "failed": len(tokens)}

        # Split into batches of 100 (Expo limit)
        batch_size = 100
        batches = [valid_tokens[i:i+batch_size] for i in range(0, len(valid_tokens), batch_size)]

        total_success = 0
        total_failed = 0

        for batch in batches:
            messages = []
            for token in batch:
                message = {
                    "to": token,
                    "title": title,
                    "body": body,
                    "sound": "default",
                    "priority": "high",
                    "channelId": "outbreak-alerts",
                }
                if data:
                    message["data"] = data
                messages.append(message)

            try:
                response = requests.post(
                    EXPO_PUSH_URL,
                    json=messages,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("data"):
                        for ticket in result["data"]:
                            if ticket.get("status") == "ok":
                                total_success += 1
                            else:
                                total_failed += 1
                                logger.error(f"Notification failed: {ticket}")
                else:
                    logger.error(f"Batch request failed with status {response.status_code}")
                    total_failed += len(batch)

            except Exception as e:
                logger.error(f"Error sending batch notification: {e}")
                total_failed += len(batch)

        logger.info(f"Batch notification complete: {total_success} success, {total_failed} failed")
        return {"success": total_success, "failed": total_failed}

    @staticmethod
    def send_outbreak_alert(
        tokens: List[str],
        location_name: str = "região próxima",
        severity: str = "medium"
    ) -> Dict[str, int]:
        """
        Send outbreak alert to multiple devices.

        Args:
            tokens: List of Expo push tokens
            location_name: Name of the outbreak location
            severity: Alert severity (low, medium, high)

        Returns:
            Dict with success and failure counts
        """
        severity_emoji = {
            "low": "⚠️",
            "medium": "⚠️",
            "high": "🚨"
        }

        title = f"{severity_emoji.get(severity, '⚠️')} Alerta de Surto"
        body = (
            f"Foi detectado um surto em {location_name}. "
            "Evite aglomerações e procure orientação médica se apresentar sintomas."
        )

        data = {
            "type": "outbreak_alert",
            "severity": severity,
            "location": location_name,
            "timestamp": datetime.utcnow().isoformat()
        }

        return NotificationService.send_batch_notifications(tokens, title, body, data)


# Singleton instance
notification_service = NotificationService()
