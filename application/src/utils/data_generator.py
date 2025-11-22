"""
Utility to generate synthetic FHIR Observation data for testing purposes.
"""
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List


# Brazilian states with IBGE codes and coordinates
BRAZILIAN_REGIONS = {
    "5208707": {"name": "Goiânia", "state": "GO", "lat_range": (-16.75, -16.55), "lng_range": (-49.35, -49.15)},
    "5300108": {"name": "Brasília", "state": "DF", "lat_range": (-15.95, -15.65), "lng_range": (-48.10, -47.80)},
    "3550308": {"name": "São Paulo", "state": "SP", "lat_range": (-23.75, -23.35), "lng_range": (-46.85, -46.35)},
    "3304557": {"name": "Rio de Janeiro", "state": "RJ", "lat_range": (-23.10, -22.75), "lng_range": (-43.80, -43.10)},
    "3106200": {"name": "Belo Horizonte", "state": "MG", "lat_range": (-20.05, -19.75), "lng_range": (-44.10, -43.85)},
    "4106902": {"name": "Curitiba", "state": "PR", "lat_range": (-25.60, -25.30), "lng_range": (-49.40, -49.15)},
    "4314902": {"name": "Porto Alegre", "state": "RS", "lat_range": (-30.20, -29.90), "lng_range": (-51.35, -51.05)},
    "2927408": {"name": "Salvador", "state": "BA", "lat_range": (-13.10, -12.75), "lng_range": (-38.65, -38.35)},
    "2611606": {"name": "Recife", "state": "PE", "lat_range": (-8.20, -7.95), "lng_range": (-35.10, -34.85)},
    "2304400": {"name": "Fortaleza", "state": "CE", "lat_range": (-3.90, -3.65), "lng_range": (-38.65, -38.40)},
    "1302603": {"name": "Manaus", "state": "AM", "lat_range": (-3.20, -2.95), "lng_range": (-60.15, -59.85)},
    "1501402": {"name": "Belém", "state": "PA", "lat_range": (-1.55, -1.35), "lng_range": (-48.60, -48.40)},
}


def generate_fhir_observation(
    leukocytes: float,
    hours_ago: float = 0,
    include_coordinates: bool = True,
    lat_range: tuple = (-16.75, -16.55),
    lng_range: tuple = (-49.35, -49.15)
) -> Dict[str, Any]:
    """
    Generate a synthetic FHIR Observation for hemogram data.

    Args:
        leukocytes: Leukocyte count value
        hours_ago: How many hours ago the observation was made (for time distribution)
        include_coordinates: Whether to include lat/lng
        lat_range: Latitude range for coordinate generation
        lng_range: Longitude range for coordinate generation

    Returns:
        A FHIR Observation dict
    """
    observation_id = str(uuid.uuid4())

    # Calculate effective datetime
    now = datetime.now(timezone.utc)
    effective_time = now - timedelta(hours=hours_ago)

    # Generate coordinates
    lat = None
    lng = None
    if include_coordinates:
        lat = random.uniform(*lat_range)
        lng = random.uniform(*lng_range)

    # Build FHIR Observation
    observation = {
        "resourceType": "Observation",
        "id": observation_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "6690-2",
                    "display": "Leukocytes [#/volume] in Blood"
                }
            ],
            "text": "Leucócitos"
        },
        "subject": {
            "reference": f"Patient/{uuid.uuid4()}"
        },
        "effectiveDateTime": effective_time.isoformat(),
        "issued": effective_time.isoformat(),
        "valueQuantity": {
            "value": leukocytes,
            "unit": "/uL",
            "system": "http://unitsofmeasure.org",
            "code": "/uL"
        },
        "extension": []
    }

    # Add geolocation if coordinates present
    if lat is not None and lng is not None:
        observation["extension"].append({
            "url": "http://hl7.org/fhir/StructureDefinition/geolocation",
            "extension": [
                {
                    "url": "latitude",
                    "valueDecimal": lat
                },
                {
                    "url": "longitude",
                    "valueDecimal": lng
                }
            ]
        })

    return observation


def generate_bulk_test_data(
    total_count: int = 3000,
    goias_percentage: float = 0.15,
    goias_elevated_percentage: float = 0.50,
    other_elevated_percentage: float = 0.15
) -> List[Dict[str, Any]]:
    """
    Generate bulk test data with specific characteristics designed to trigger outbreak detection.

    Outbreak Detection Strategy:
    - Temporal surge: 90% of Goiás cases in last 24h vs 10% in previous 24h (~800% growth)
    - High severity: 60%+ cases with elevated leukocytes in recent period
    - Geographic concentration: 20% of all observations focused in Goiás
    - Chronological ordering: Sorted by timestamp to simulate realistic outbreak progression

    Args:
        total_count: Total number of observations to generate
        goias_percentage: Percentage of observations from concentrated area (outbreak region)
        goias_elevated_percentage: Percentage of concentrated area observations with elevated leukocytes
        other_elevated_percentage: Percentage of other observations with elevated leukocytes (baseline)

    Returns:
        List of FHIR Observation dicts, sorted chronologically (oldest to newest)
    """
    observations = []

    # Calculate counts
    concentrated_count = int(total_count * goias_percentage)
    other_count = total_count - concentrated_count

    # Split concentrated area into two time periods to create strong 24h increase
    # Using 10%/90% split for ~800% growth, guaranteeing >20% threshold even with random insertion
    concentrated_prev_24h_count = int(concentrated_count * 0.10)  # 10% in previous 24h
    concentrated_last_24h_count = concentrated_count - concentrated_prev_24h_count  # 90% in last 24h (surge!)

    # Previous 24h (24-48 hours ago) - Concentrated area (Goiânia coordinates)
    # This represents the baseline before the outbreak surge
    for i in range(concentrated_prev_24h_count):
        hours_ago = random.uniform(24, 48)

        # Determine if elevated (using base percentage)
        is_elevated = random.random() < goias_elevated_percentage

        if is_elevated:
            # Elevated: 11000-20000
            leukocytes = random.uniform(11000, 20000)
        else:
            # Normal: 4000-10000
            leukocytes = random.uniform(4000, 10000)

        obs = generate_fhir_observation(
            leukocytes=leukocytes,
            hours_ago=hours_ago,
            include_coordinates=True,
            lat_range=(-16.75, -16.55),
            lng_range=(-49.35, -49.15)
        )
        observations.append(obs)

    # Last 24h (0-24 hours ago) - Concentrated area (OUTBREAK SURGE)
    # This represents the recent outbreak with significantly elevated cases
    for i in range(concentrated_last_24h_count):
        hours_ago = random.uniform(0, 24)

        # Determine if elevated (using outbreak percentage - even higher than baseline)
        # Adding +5% boost to ensure strong outbreak signal in recent period
        outbreak_elevated_pct = min(goias_elevated_percentage + 0.05, 0.75)
        is_elevated = random.random() < outbreak_elevated_pct

        if is_elevated:
            # Elevated: 11000-20000 (higher values more likely during outbreak)
            leukocytes = random.uniform(11500, 20000)
        else:
            # Normal: 4000-10000
            leukocytes = random.uniform(4000, 10000)

        obs = generate_fhir_observation(
            leukocytes=leukocytes,
            hours_ago=hours_ago,
            include_coordinates=True,
            lat_range=(-16.75, -16.55),
            lng_range=(-49.35, -49.15)
        )
        observations.append(obs)

    # Generate observations from other regions
    for i in range(other_count):
        # Select random region from BRAZILIAN_REGIONS
        region_info = random.choice(list(BRAZILIAN_REGIONS.values()))
        hours_ago = random.uniform(0, 168)  # Up to 7 days

        # Determine if elevated
        is_elevated = random.random() < other_elevated_percentage

        if is_elevated:
            # Elevated: 11000-18000
            leukocytes = random.uniform(11000, 18000)
        else:
            # Normal: 4000-10000
            leukocytes = random.uniform(4000, 10000)

        obs = generate_fhir_observation(
            leukocytes=leukocytes,
            hours_ago=hours_ago,
            include_coordinates=True,
            lat_range=region_info["lat_range"],
            lng_range=region_info["lng_range"]
        )
        observations.append(obs)

    # Sort by timestamp (oldest first) to simulate realistic temporal growth
    # This ensures the surge pattern is maintained during incremental insertion
    observations.sort(key=lambda obs: obs.get("effectiveDateTime", ""))

    return observations
