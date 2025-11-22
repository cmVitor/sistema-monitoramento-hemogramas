from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Tuple
from math import sqrt

from ..models import HemogramObservation, AlertCommunication
from ..utils.fhir_utils import ELEVATED_LEUKOCYTES_THRESHOLD, build_fhir_communication_alert


def find_geographic_clusters(
    observations: List[HemogramObservation],
    grid_size: float = 0.1
) -> Dict[Tuple[int, int], List[HemogramObservation]]:
    """
    Agrupa observações em clusters geográficos usando uma grade.

    Args:
        observations: Lista de observações com coordenadas
        grid_size: Tamanho da célula da grade em graus (padrão: 0.1° ≈ 11km)

    Returns:
        Dicionário mapeando células da grade para listas de observações
    """
    clusters = {}

    for obs in observations:
        if obs.latitude is None or obs.longitude is None:
            continue

        # Mapeia coordenadas para célula da grade
        grid_lat = int(obs.latitude / grid_size)
        grid_lng = int(obs.longitude / grid_size)
        grid_cell = (grid_lat, grid_lng)

        if grid_cell not in clusters:
            clusters[grid_cell] = []
        clusters[grid_cell].append(obs)

    return clusters


def compute_cluster_stats(
    cluster_observations: List[HemogramObservation],
    since_24h: datetime,
    since_prev_24h: datetime,
    since_7d: datetime
) -> Dict[str, Any]:
    """
    Calcula estatísticas para um cluster de observações.

    Args:
        cluster_observations: Observações do cluster
        since_24h: Timestamp de 24h atrás
        since_prev_24h: Timestamp de 48h atrás
        since_7d: Timestamp de 7 dias atrás

    Returns:
        Dicionário com estatísticas do cluster
    """
    # Filtra observações dos últimos 7 dias
    obs_7d = [obs for obs in cluster_observations if obs.received_at >= since_7d]

    if not obs_7d:
        return None

    total = len(obs_7d)

    # Conta casos elevados nos últimos 7 dias
    elevated = sum(
        1 for obs in obs_7d
        if obs.leukocytes is not None and obs.leukocytes >= ELEVATED_LEUKOCYTES_THRESHOLD
    )

    # Conta casos nas últimas 24h
    last_24 = sum(1 for obs in obs_7d if obs.received_at >= since_24h)

    # Conta casos nas 24h anteriores (48h-24h atrás)
    prev_24 = sum(
        1 for obs in obs_7d
        if since_prev_24h <= obs.received_at < since_24h
    )

    # Calcula percentuais
    pct_elevated = (elevated / total * 100.0) if total else 0.0

    increase_24h_pct = 0.0
    if prev_24 > 0:
        increase_24h_pct = ((last_24 - prev_24) / prev_24) * 100.0
    elif last_24 > 0 and prev_24 == 0:
        increase_24h_pct = 100.0

    return {
        "total": total,
        "elevated": elevated,
        "pct_elevated": pct_elevated,
        "last_24": last_24,
        "prev_24": prev_24,
        "increase_24h_pct": increase_24h_pct,
        "observations": obs_7d
    }


def evaluate_and_create_alert_if_needed(db: Session) -> AlertCommunication | None:
    """
    Detecta surtos usando clustering geográfico.

    Algoritmo:
    1. Busca todas as observações dos últimos 7 dias com coordenadas
    2. Agrupa observações em clusters geográficos (grade de 0.1° ≈ 11km)
    3. Para cada cluster com pelo menos 20 observações:
       - Calcula % de casos elevados
       - Calcula crescimento nas últimas 24h
    4. Detecta surto se algum cluster atender aos critérios

    Critérios de surto:
    - Pelo menos 20 observações no cluster
    - >40% dos casos com leucócitos elevados
    - >20% de aumento nas últimas 24h

    Returns:
        AlertCommunication se surto detectado, None caso contrário
    """
    now = datetime.now(timezone.utc)
    since_7d = now - timedelta(days=7)
    since_24h = now - timedelta(hours=24)
    since_prev_24h = since_24h - timedelta(hours=24)

    # Busca todas as observações dos últimos 7 dias com coordenadas
    all_observations = db.execute(
        select(HemogramObservation)
        .where(
            HemogramObservation.received_at >= since_7d,
            HemogramObservation.latitude.isnot(None),
            HemogramObservation.longitude.isnot(None)
        )
    ).scalars().all()

    if not all_observations:
        return None

    # Agrupa em clusters geográficos
    clusters = find_geographic_clusters(all_observations, grid_size=0.1)

    # Avalia cada cluster
    outbreak_detected = False
    best_cluster_stats = None

    for grid_cell, cluster_obs in clusters.items():
        # Ignora clusters muito pequenos
        if len(cluster_obs) < 20:
            continue

        stats = compute_cluster_stats(
            cluster_obs,
            since_24h,
            since_prev_24h,
            since_7d
        )

        if stats is None:
            continue

        # Verifica critérios de surto
        if stats["pct_elevated"] > 40.0 and stats["increase_24h_pct"] > 20.0:
            outbreak_detected = True

            # Guarda o cluster com maior severidade
            if (best_cluster_stats is None or
                stats["pct_elevated"] > best_cluster_stats["pct_elevated"]):
                best_cluster_stats = stats
                best_cluster_stats["grid_cell"] = grid_cell

    # Cria alerta se surto detectado
    if outbreak_detected and best_cluster_stats:
        # Calcula centroide do cluster
        cluster_lat = sum(obs.latitude for obs in best_cluster_stats["observations"]) / len(best_cluster_stats["observations"])
        cluster_lng = sum(obs.longitude for obs in best_cluster_stats["observations"]) / len(best_cluster_stats["observations"])

        summary = (
            f"Alerta de possivel surto detectado: "
            f"{best_cluster_stats['total']} casos identificados, "
            f"{best_cluster_stats['pct_elevated']:.1f}% com leucocitos elevados, "
            f"aumento de {best_cluster_stats['increase_24h_pct']:.1f}% nas ultimas 24h. "
            f"Localizacao: ({cluster_lat:.4f}, {cluster_lng:.4f})"
        )

        fhir_comm = build_fhir_communication_alert(best_cluster_stats)

        alert = AlertCommunication(
            summary=summary,
            fhir_communication=fhir_comm,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    return None
