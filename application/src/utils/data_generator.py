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
    region_ibge_code: str,
    leukocytes: float,
    hours_ago: float = 0,
    include_coordinates: bool = True,
    include_phone: bool = True
) -> Dict[str, Any]:
    """
    Generate a synthetic FHIR Observation for hemogram data.

    Args:
        region_ibge_code: IBGE code for the region
        leukocytes: Leukocyte count value
        hours_ago: How many hours ago the observation was made (for time distribution)
        include_coordinates: Whether to include lat/lng
        include_phone: Whether to include performer phone

    Returns:
        A FHIR Observation dict
    """
    observation_id = str(uuid.uuid4())

    # Calculate effective datetime
    now = datetime.now(timezone.utc)
    effective_time = now - timedelta(hours=hours_ago)

    # Get region info
    region_info = BRAZILIAN_REGIONS.get(region_ibge_code, {
        "name": "Unknown",
        "state": "XX",
        "lat_range": (-15.0, -14.0),
        "lng_range": (-48.0, -47.0)
    })

    # Generate coordinates
    lat = None
    lng = None
    if include_coordinates:
        lat = random.uniform(*region_info["lat_range"])
        lng = random.uniform(*region_info["lng_range"])

    # Generate phone
    phone = None
    if include_phone:
        phone = f"+55 62 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"

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
            "reference": f"Patient/{uuid.uuid4()}",
            "identifier": {
                "system": "http://ibge.gov.br/regiao",
                "value": region_ibge_code
            }
        },
        "effectiveDateTime": effective_time.isoformat(),
        "issued": effective_time.isoformat(),
        "valueQuantity": {
            "value": leukocytes,
            "unit": "/uL",
            "system": "http://unitsofmeasure.org",
            "code": "/uL"
        },
        "extension": [
            {
                "url": "http://ibge.gov.br/fhir/extension/region",
                "valueString": region_ibge_code
            }
        ]
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

    # Add performer with phone if present
    if phone:
        observation["performer"] = [
            {
                "reference": f"Practitioner/{uuid.uuid4()}",
                "display": f"Lab {region_info['name']}",
                "telecom": [
                    {
                        "system": "phone",
                        "value": phone
                    }
                ]
            }
        ]

    return observation


def generate_bulk_test_data(
    total_count: int = 3000,
    goias_percentage: float = 0.15,
    goias_elevated_percentage: float = 0.50,
    other_elevated_percentage: float = 0.15
) -> List[Dict[str, Any]]:
    """
    Generate bulk test data with specific characteristics.

    Args:
        total_count: Total number of observations to generate
        goias_percentage: Percentage of observations from Goiás
        goias_elevated_percentage: Percentage of Goiás observations with elevated leukocytes
        other_elevated_percentage: Percentage of other observations with elevated leukocytes

    Returns:
        List of FHIR Observation dicts
    """
    observations = []
    goias_code = "5208707"  # Goiânia
    other_regions = [code for code in BRAZILIAN_REGIONS.keys() if code != goias_code]

    # Calculate counts
    goias_count = int(total_count * goias_percentage)
    other_count = total_count - goias_count

    # Generate Goiás observations
    # Split into two time periods to create 24h increase
    goias_prev_24h_count = int(goias_count * 0.35)  # 35% in previous 24h
    goias_last_24h_count = goias_count - goias_prev_24h_count  # 65% in last 24h (increase!)

    # Previous 24h (25-48 hours ago)
    for i in range(goias_prev_24h_count):
        hours_ago = random.uniform(25, 48)

        # Determine if elevated
        is_elevated = random.random() < goias_elevated_percentage

        if is_elevated:
            # Elevated: 11000-20000
            leukocytes = random.uniform(11000, 20000)
        else:
            # Normal: 4000-10000
            leukocytes = random.uniform(4000, 10000)

        obs = generate_fhir_observation(
            region_ibge_code=goias_code,
            leukocytes=leukocytes,
            hours_ago=hours_ago,
            include_coordinates=True,
            include_phone=True
        )
        observations.append(obs)

    # Last 24h (0-24 hours ago)
    for i in range(goias_last_24h_count):
        hours_ago = random.uniform(0, 24)

        # Determine if elevated (higher percentage for alert)
        is_elevated = random.random() < goias_elevated_percentage

        if is_elevated:
            # Elevated: 11000-20000
            leukocytes = random.uniform(11000, 20000)
        else:
            # Normal: 4000-10000
            leukocytes = random.uniform(4000, 10000)

        obs = generate_fhir_observation(
            region_ibge_code=goias_code,
            leukocytes=leukocytes,
            hours_ago=hours_ago,
            include_coordinates=True,
            include_phone=True
        )
        observations.append(obs)

    # Generate other regions observations
    for i in range(other_count):
        region_code = random.choice(other_regions)
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
            region_ibge_code=region_code,
            leukocytes=leukocytes,
            hours_ago=hours_ago,
            include_coordinates=True,
            include_phone=random.random() < 0.7  # 70% have phone
        )
        observations.append(obs)

    # Shuffle to mix time periods
    random.shuffle(observations)

    return observations
