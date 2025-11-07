from typing import Any, Optional, Dict
from dateutil import parser as dateparser

LEUKOCYTE_CODES = {
    "6690-2",
    "26464-8",
}

ELEVATED_LEUKOCYTES_THRESHOLD = 11000.0

def extract_region_ibge_code(observation: Dict[str, Any]) -> Optional[str]:
    for ext in observation.get("extension", []) or []:
        url = ext.get("url")
        if url and "ibge" in url.lower():
            for k in ("valueString", "valueCode", "valueIdentifier"):
                v = ext.get(k)
                if isinstance(v, dict):
                    val = v.get("value") or v.get("id") or v.get("system")
                    if val:
                        return str(val)
                elif v:
                    return str(v)

    subject = observation.get("subject") or {}
    identifier = subject.get("identifier")
    if isinstance(identifier, list):
        for ident in identifier:
            system = (ident.get("system") or "").lower()
            if "ibge" in system:
                return str(ident.get("value") or "") or None
    elif isinstance(identifier, dict):
        system = (identifier.get("system") or "").lower()
        if "ibge" in system:
            return str(identifier.get("value") or "") or None

    meta = observation.get("meta") or {}
    for tag in (meta.get("tag") or []):
        if "ibge" in (tag.get("system") or "").lower():
            return str(tag.get("code") or "") or None

    return None

def extract_leukocytes(observation: Dict[str, Any]) -> Optional[float]:
    vq = observation.get("valueQuantity")
    if isinstance(vq, dict):
        code = (vq.get("code") or vq.get("unit") or "").lower()
        if vq.get("value") is not None:
            if is_leukocyte_observation(observation):
                try:
                    return float(vq.get("value"))
                except (TypeError, ValueError):
                    pass

    for comp in observation.get("component") or []:
        if is_leukocyte_component(comp):
            vq = comp.get("valueQuantity") or {}
            if vq.get("value") is not None:
                try:
                    return float(vq.get("value"))
                except (TypeError, ValueError):
                    continue

    return None

def is_leukocyte_observation(observation: Dict[str, Any]) -> bool:
    code = observation.get("code") or {}
    for coding in code.get("coding") or []:
        if coding.get("code") in LEUKOCYTE_CODES:
            return True
    return False

def is_leukocyte_component(component: Dict[str, Any]) -> bool:
    code = component.get("code") or {}
    for coding in code.get("coding") or []:
        if coding.get("code") in LEUKOCYTE_CODES:
            return True
    return False

def anonymize_observation(observation: Dict[str, Any]) -> Dict[str, Any]:
    obs = dict(observation)

    subject = obs.get("subject")
    if isinstance(subject, dict):
        if "identifier" in subject:
            subj_ident = subject["identifier"]
            if isinstance(subj_ident, list):
                obs["subject"]["identifier"] = [
                    ident for ident in subj_ident if not looks_like_pii_identifier(ident)
                ]
            elif isinstance(subj_ident, dict) and looks_like_pii_identifier(subj_ident):
                obs["subject"]["identifier"] = None
        if "display" in subject:
            obs["subject"]["display"] = None

    performers = obs.get("performer") or []
    clean_performers = []
    for perf in performers:
        if isinstance(perf, dict):
            perf = dict(perf)
            if "display" in perf:
                perf["display"] = None
            clean_performers.append(perf)
    if clean_performers:
        obs["performer"] = clean_performers

    for res in obs.get("contained") or []:
        if isinstance(res, dict) and res.get("resourceType") == "Patient":
            if "name" in res:
                res["name"] = None
            if "identifier" in res:
                res["identifier"] = None

    return obs

def looks_like_pii_identifier(ident: Dict[str, Any]) -> bool:
    system = (ident.get("system") or "").lower()
    value = str(ident.get("value") or "")
    if "cpf" in system:
        return True
    if len(value) in (11, 14) and value.isdigit():
        return True
    return False

def extract_latitude(observation: Dict[str, Any]) -> Optional[float]:
    """Extrai latitude de extensions ou subject"""
    # Procura em extensions
    for ext in observation.get("extension", []) or []:
        url = ext.get("url", "").lower()
        if "latitude" in url or "geolocation" in url:
            if "valueDecimal" in ext:
                try:
                    return float(ext["valueDecimal"])
                except (TypeError, ValueError):
                    pass
            # Geolocation extension pode ter position
            if "extension" in ext:
                for sub_ext in ext["extension"]:
                    if "latitude" in sub_ext.get("url", "").lower():
                        try:
                            return float(sub_ext.get("valueDecimal", 0))
                        except (TypeError, ValueError):
                            pass

    # Procura em subject (Location reference)
    subject = observation.get("subject") or {}
    if isinstance(subject, dict) and "extension" in subject:
        for ext in subject["extension"]:
            if "latitude" in ext.get("url", "").lower():
                try:
                    return float(ext.get("valueDecimal", 0))
                except (TypeError, ValueError):
                    pass

    return None

def extract_longitude(observation: Dict[str, Any]) -> Optional[float]:
    """Extrai longitude de extensions ou subject"""
    # Procura em extensions
    for ext in observation.get("extension", []) or []:
        url = ext.get("url", "").lower()
        if "longitude" in url or "geolocation" in url:
            if "valueDecimal" in ext:
                try:
                    return float(ext["valueDecimal"])
                except (TypeError, ValueError):
                    pass
            # Geolocation extension pode ter position
            if "extension" in ext:
                for sub_ext in ext["extension"]:
                    if "longitude" in sub_ext.get("url", "").lower():
                        try:
                            return float(sub_ext.get("valueDecimal", 0))
                        except (TypeError, ValueError):
                            pass

    # Procura em subject (Location reference)
    subject = observation.get("subject") or {}
    if isinstance(subject, dict) and "extension" in subject:
        for ext in subject["extension"]:
            if "longitude" in ext.get("url", "").lower():
                try:
                    return float(ext.get("valueDecimal", 0))
                except (TypeError, ValueError):
                    pass

    return None

def extract_telefone(observation: Dict[str, Any]) -> Optional[str]:
    """Extrai telefone de quem realizou o hemograma (performer)"""
    # Procura em performer
    performers = observation.get("performer", []) or []
    for perf in performers:
        if isinstance(perf, dict):
            # Procura em telecom
            telecoms = perf.get("telecom", []) or []
            for telecom in telecoms:
                if isinstance(telecom, dict):
                    system = telecom.get("system", "").lower()
                    if system in ("phone", "sms", "telefone"):
                        value = telecom.get("value")
                        if value:
                            return str(value)

            # Procura em extension
            extensions = perf.get("extension", []) or []
            for ext in extensions:
                url = ext.get("url", "").lower()
                if "phone" in url or "telefone" in url or "telecom" in url:
                    value = ext.get("valueString") or ext.get("valueContactPoint", {}).get("value")
                    if value:
                        return str(value)

    # Procura em extensions da observação
    for ext in observation.get("extension", []) or []:
        url = ext.get("url", "").lower()
        if "performer-phone" in url or "telefone" in url:
            value = ext.get("valueString") or ext.get("valueContactPoint", {}).get("value")
            if value:
                return str(value)

    return None

def build_fhir_communication_alert(region_ibge_code: str, stats: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "resourceType": "Communication",
        "status": "completed",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/communication-category",
                        "code": "alert",
                        "display": "Alert"
                    }
                ]
            }
        ],
        "reasonCode": [
            {
                "text": "Potential infectious outbreak based on leukocyte trends"
            }
        ],
        "payload": [
            {
                "contentString": (
                    f"Regiao IBGE {region_ibge_code}: {stats.get('total', 0)} observacoes nas ultimas 7d; "
                    f"{stats.get('pct_elevated', 0):.1f}% leucocitos elevados; "
                    f"variacao 24h: {stats.get('increase_24h_pct', 0):.1f}%"
                )
            }
        ],
        "note": [
            {
                "text": "Recomendacao: investigacao local e aumento de testes sorologicos."
            }
        ]
    }
