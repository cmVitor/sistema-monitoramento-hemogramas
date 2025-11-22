"""
Mobile API endpoints for device registration and location updates.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..db import get_db
from ..schemas import (
    MobileDeviceRegister,
    LocationUpdate,
    MobileDeviceOut
)
from ..models import MobileDevice
from ..services.mobile_location_service import mobile_location_service
from ..services.notification_service import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mobile", tags=["mobile"])


@router.post("/register", response_model=MobileDeviceOut)
async def register_device(
    device_data: MobileDeviceRegister,
    db: Session = Depends(get_db)
):
    """
    Register or update a mobile device for outbreak alerts.

    - **device_id**: Unique device identifier
    - **fcm_token**: Expo Push Token for notifications
    - **platform**: Device platform (ios or android)
    """
    try:
        # Check if device already exists
        existing_device = db.query(MobileDevice).filter(
            MobileDevice.device_id == device_data.device_id
        ).first()

        if existing_device:
            # Update existing device
            existing_device.fcm_token = device_data.fcm_token
            existing_device.platform = device_data.platform
            existing_device.is_active = True
            device = existing_device
            logger.info(f"Updated device {device_data.device_id}")
        else:
            # Create new device
            device = MobileDevice(
                device_id=device_data.device_id,
                fcm_token=device_data.fcm_token,
                platform=device_data.platform,
                is_active=True
            )
            db.add(device)
            logger.info(f"Registered new device {device_data.device_id}")

        db.commit()
        db.refresh(device)

        return MobileDeviceOut(
            device_id=device.device_id,
            platform=device.platform,
            is_active=device.is_active,
            registered_at=device.registered_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Error registering device: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to register device")


@router.post("/location")
async def update_location(
    location_data: LocationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update device location and check for outbreak alerts.

    - **device_id**: Device identifier
    - **latitude**: Current latitude
    - **longitude**: Current longitude
    - **timestamp**: Location timestamp (ISO format)
    """
    try:
        # Parse timestamp
        timestamp = datetime.fromisoformat(location_data.timestamp.replace('Z', '+00:00'))

        # Update location and check for outbreak
        # Returns: (device, should_alert, in_outbreak_zone)
        device, should_alert, in_outbreak_zone = mobile_location_service.update_device_location(
            db=db,
            device_id=location_data.device_id,
            latitude=location_data.latitude,
            longitude=location_data.longitude,
            timestamp=timestamp
        )

        if not device:
            raise HTTPException(
                status_code=404,
                detail="Device not registered. Please register device first."
            )

        # Send alert if device JUST entered outbreak zone (push notification)
        alert_sent = False
        if should_alert:
            logger.info(f"Device {location_data.device_id} ENTERED outbreak zone - sending push notification")
            notification_service.send_outbreak_alert(
                tokens=[device.fcm_token],
                location_name="região próxima",
                severity="medium"
            )
            alert_sent = True

        # Log current status
        if in_outbreak_zone:
            logger.info(f"Device {location_data.device_id} is currently IN outbreak zone at ({location_data.latitude}, {location_data.longitude})")
        else:
            logger.debug(f"Device {location_data.device_id} is OUTSIDE outbreak zones")

        # Always return current outbreak zone status
        return {
            "status": "success",
            "message": "Location updated",
            "alert_sent": alert_sent,
            "in_outbreak_zone": in_outbreak_zone  # TRUE if currently in outbreak zone
        }

    except ValueError as e:
        logger.error(f"Invalid timestamp format: {e}")
        raise HTTPException(status_code=400, detail="Invalid timestamp format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating location: {e}")
        raise HTTPException(status_code=500, detail="Failed to update location")


@router.post("/unregister/{device_id}")
async def unregister_device(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    Unregister a device from receiving alerts.

    - **device_id**: Device identifier to unregister
    """
    try:
        device = db.query(MobileDevice).filter(
            MobileDevice.device_id == device_id
        ).first()

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        device.is_active = False
        db.commit()

        logger.info(f"Unregistered device {device_id}")

        return {
            "status": "success",
            "message": "Device unregistered successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering device: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to unregister device")


@router.get("/devices/count")
async def get_device_count(db: Session = Depends(get_db)):
    """Get count of active registered devices."""
    try:
        count = db.query(MobileDevice).filter(
            MobileDevice.is_active == True
        ).count()

        return {
            "active_devices": count
        }

    except Exception as e:
        logger.error(f"Error getting device count: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device count")


# Export router
mobile_router = router
