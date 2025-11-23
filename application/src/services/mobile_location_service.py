"""
Mobile location service for checking if devices are in outbreak regions.
"""
from typing import Optional, Dict, Any
from math import sqrt
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from ..models import MobileDevice
from .geospatial import compute_outbreak_regions

logger = logging.getLogger(__name__)

# Cooldown period between alerts for the same device (in minutes)
ALERT_COOLDOWN_MINUTES = 5


class MobileLocationService:
    """Service for managing mobile device locations and outbreak alerts."""

    @staticmethod
    def is_in_outbreak_zone(
        latitude: float,
        longitude: float,
        outbreak_data: Dict[str, Any]
    ) -> bool:
        """
        Check if a location is within an outbreak zone.

        Args:
            latitude: Device latitude
            longitude: Device longitude
            outbreak_data: Outbreak data from compute_outbreak_regions

        Returns:
            True if location is in outbreak zone, False otherwise
        """
        if not outbreak_data or "outbreak" not in outbreak_data:
            return False

        outbreak = outbreak_data["outbreak"]
        centroid = outbreak["centroid"]
        radius_meters = outbreak["radius"]

        # Calculate distance from centroid
        lat_diff = latitude - centroid["lat"]
        lng_diff = longitude - centroid["lng"]
        distance_degrees = sqrt(lat_diff**2 + lng_diff**2)

        # Convert to meters (1 degree ≈ 111km)
        distance_meters = distance_degrees * 111000

        return distance_meters <= radius_meters

    @staticmethod
    def update_device_location(
        db: Session,
        device_id: str,
        latitude: float,
        longitude: float,
        timestamp: Optional[datetime] = None
    ) -> tuple[MobileDevice, bool, bool]:
        """
        Update device location and check if it entered an outbreak zone.

        Args:
            db: Database session
            device_id: Device identifier
            latitude: Device latitude
            longitude: Device longitude
            timestamp: Location timestamp (defaults to now)

        Returns:
            Tuple of (device, should_alert, in_outbreak_zone)
            - device: MobileDevice object
            - should_alert: True if device JUST entered outbreak zone
            - in_outbreak_zone: True if device IS currently in outbreak zone
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Get or create device
        device = db.query(MobileDevice).filter(
            MobileDevice.device_id == device_id
        ).first()

        if not device:
            logger.warning(f"Device {device_id} not registered, cannot update location")
            return None, False, False

        # Get outbreak data
        outbreak_data = compute_outbreak_regions(db)
        in_outbreak = MobileLocationService.is_in_outbreak_zone(
            latitude, longitude, outbreak_data
        )

        # Check if device just entered outbreak zone
        was_in_outbreak = False
        if device.last_location_lat and device.last_location_lng:
            was_in_outbreak = MobileLocationService.is_in_outbreak_zone(
                device.last_location_lat,
                device.last_location_lng,
                outbreak_data
            )

        # Update device location
        device.last_location_lat = latitude
        device.last_location_lng = longitude
        device.last_location_update = timestamp

        db.commit()
        db.refresh(device)

        # should_alert: True only if device JUST entered outbreak zone (transition)
        entered_outbreak_zone = in_outbreak and not was_in_outbreak

        # Check cooldown: don't alert if last alert was sent recently
        should_alert = False
        if entered_outbreak_zone:
            if device.last_alert_sent:
                # Check if enough time has passed since last alert
                time_since_last_alert = timestamp - device.last_alert_sent
                if time_since_last_alert < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    minutes_remaining = ALERT_COOLDOWN_MINUTES - (time_since_last_alert.total_seconds() / 60)
                    logger.info(
                        f"Device {device_id} entered outbreak zone but alert is in cooldown "
                        f"({minutes_remaining:.1f} minutes remaining)"
                    )
                    should_alert = False
                else:
                    should_alert = True
            else:
                # First time entering outbreak zone
                should_alert = True

            if should_alert:
                # Update last_alert_sent timestamp
                device.last_alert_sent = timestamp
                db.commit()
                db.refresh(device)
                logger.info(f"Device {device_id} ENTERED outbreak zone at ({latitude}, {longitude}) - ALERT SENT")
        elif in_outbreak:
            logger.debug(f"Device {device_id} is STILL in outbreak zone at ({latitude}, {longitude})")

        # Return both: should_alert AND current outbreak status
        return device, should_alert, in_outbreak

    @staticmethod
    def get_devices_in_outbreak_zone(db: Session) -> list[MobileDevice]:
        """
        Get all active devices currently in outbreak zones.

        Args:
            db: Database session

        Returns:
            List of MobileDevice objects
        """
        outbreak_data = compute_outbreak_regions(db)
        if not outbreak_data or "outbreak" not in outbreak_data:
            return []

        # Get all active devices with location
        devices = db.query(MobileDevice).filter(
            MobileDevice.is_active == True,
            MobileDevice.last_location_lat.isnot(None),
            MobileDevice.last_location_lng.isnot(None)
        ).all()

        # Filter devices in outbreak zone
        devices_in_zone = []
        for device in devices:
            if MobileLocationService.is_in_outbreak_zone(
                device.last_location_lat,
                device.last_location_lng,
                outbreak_data
            ):
                devices_in_zone.append(device)

        return devices_in_zone


# Singleton instance
mobile_location_service = MobileLocationService()
