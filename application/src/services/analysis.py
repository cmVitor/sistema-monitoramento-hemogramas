from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..models import HemogramObservation, AlertCommunication
from ..utils.fhir_utils import ELEVATED_LEUKOCYTES_THRESHOLD, build_fhir_communication_alert


def compute_region_stats(db: Session, region_ibge_code: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    since_7d = now - timedelta(days=7)
    since_24h = now - timedelta(hours=24)
    since_prev_24h = since_24h - timedelta(hours=24)

    # Total last 7d
    q_total = db.execute(
        select(func.count()).select_from(HemogramObservation)
        .where(
            HemogramObservation.region_ibge_code == region_ibge_code,
            HemogramObservation.received_at >= since_7d,
        )
    ).scalar()

    # Elevated leukocytes last 7d
    q_elev = db.execute(
        select(func.count()).select_from(HemogramObservation)
        .where(
            HemogramObservation.region_ibge_code == region_ibge_code,
            HemogramObservation.received_at >= since_7d,
            HemogramObservation.leukocytes != None,  # noqa: E711
            HemogramObservation.leukocytes >= ELEVATED_LEUKOCYTES_THRESHOLD,
        )
    ).scalar()

    # Last 24h count
    last_24 = db.execute(
        select(func.count()).select_from(HemogramObservation)
        .where(
            HemogramObservation.region_ibge_code == region_ibge_code,
            HemogramObservation.received_at >= since_24h,
        )
    ).scalar()

    # Previous 24h count
    prev_24 = db.execute(
        select(func.count()).select_from(HemogramObservation)
        .where(
            HemogramObservation.region_ibge_code == region_ibge_code,
            HemogramObservation.received_at >= since_prev_24h,
            HemogramObservation.received_at < since_24h,
        )
    ).scalar()

    pct_elev = (q_elev / q_total * 100.0) if q_total else 0.0
    increase_24h_pct = 0.0
    if prev_24:
        increase_24h_pct = ((last_24 - prev_24) / prev_24) * 100.0
    elif last_24 and not prev_24:
        increase_24h_pct = 100.0

    return {
        "total": int(q_total or 0),
        "elevated": int(q_elev or 0),
        "pct_elevated": float(pct_elev),
        "last_24": int(last_24 or 0),
        "prev_24": int(prev_24 or 0),
        "increase_24h_pct": float(increase_24h_pct),
    }


def evaluate_and_create_alert_if_needed(db: Session, region_ibge_code: str) -> AlertCommunication | None:
    stats = compute_region_stats(db, region_ibge_code)

    # Criteria:
    # - more than 40% with elevated leukocytes
    # - more than 20% increase in last 24h
    if stats["pct_elevated"] > 40.0 and stats["increase_24h_pct"] > 20.0:
        summary = (
            f"Alerta de possivel surto em {region_ibge_code}: "
            f"{stats['pct_elevated']:.1f}% com leucocitos elevados; "
            f"aumento de {stats['increase_24h_pct']:.1f}% nas ultimas 24h."
        )
        fhir_comm = build_fhir_communication_alert(region_ibge_code, stats)
        alert = AlertCommunication(
            region_ibge_code=region_ibge_code,
            summary=summary,
            fhir_communication=fhir_comm,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    return None
