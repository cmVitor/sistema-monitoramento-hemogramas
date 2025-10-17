from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.database.database import ObservationDB, SlidingWindowDB
from app.models.alert_models import SlidingWindowStats, CollectiveAlert
from config import settings
import statistics

class AnalysisService:
    def __init__(self):
        self.window_hours = settings.sliding_window_hours
        self.min_samples = settings.min_samples_threshold
        self.alert_threshold = settings.alert_proportion_threshold
        self.trend_threshold = settings.trend_increase_threshold
    
    def check_individual_alert(self, parameter: str, value: float) -> bool:
        """Verifica se um valor individual é anômalo"""
        reference_ranges = {
            'leukocytes': (4.0, 11.0),  # 10^3/μL
            'hemoglobin': (12.0, 16.0),  # g/dL (mulheres adultas)
            'platelets': (150, 450),     # 10^3/μL
            'hematocrit': (36, 48)       # %
        }
        
        if parameter in reference_ranges:
            low, high = reference_ranges[parameter]
            return value < low or value > high
        
        return False
    
    def calculate_window_stats(self, db: Session, region: str, parameter: str, 
                             end_time: datetime) -> SlidingWindowStats:
        """Calcula estatísticas para uma janela deslizante"""
        start_time = end_time - timedelta(hours=self.window_hours)
        
        # Buscar observações na janela
        observations = db.query(ObservationDB).filter(
            ObservationDB.region == region,
            ObservationDB.parameter == parameter,
            ObservationDB.effective_datetime >= start_time,
            ObservationDB.effective_datetime <= end_time
        ).all()
        
        if not observations:
            return None
        
        values = [obs.value for obs in observations if obs.value is not None]
        alert_count = sum(1 for obs in observations if obs.has_alert)
        
        stats = SlidingWindowStats(
            region=region,
            parameter=parameter,
            window_start=start_time,
            window_end=end_time,
            total_count=len(observations),
            alert_count=alert_count,
            mean_value=statistics.mean(values) if values else 0,
            std_dev=statistics.stdev(values) if len(values) > 1 else 0,
            alert_proportion=alert_count / len(observations) if observations else 0
        )
        
        return stats
    
    def detect_collective_pattern(self, db: Session, current_stats: SlidingWindowStats) -> Optional[CollectiveAlert]:
        """Detecta padrões coletivos anômalos"""
        if current_stats.total_count < self.min_samples:
            return None
        
        if current_stats.alert_proportion < self.alert_threshold:
            return None
        
        # Calcular tendência comparando com janela anterior
        previous_end = current_stats.window_start - timedelta(minutes=1)
        previous_stats = self.calculate_window_stats(
            db, current_stats.region, current_stats.parameter, previous_end
        )
        
        if not previous_stats or previous_stats.total_count < self.min_samples:
            return None
        
        trend_increase = (current_stats.mean_value - previous_stats.mean_value) / previous_stats.mean_value
        
        if trend_increase < self.trend_threshold:
            return None
        
        # Determinar nível do alerta
        if trend_increase > 0.5:
            alert_level = "high"
        elif trend_increase > 0.3:
            alert_level = "medium"
        else:
            alert_level = "low"
        
        # Buscar observações que contribuíram para o alerta
        contributing_obs = db.query(ObservationDB.fhir_id).filter(
            ObservationDB.region == current_stats.region,
            ObservationDB.parameter == current_stats.parameter,
            ObservationDB.effective_datetime >= current_stats.window_start,
            ObservationDB.effective_datetime <= current_stats.window_end,
            ObservationDB.has_alert == True
        ).limit(50).all()
        
        alert = CollectiveAlert(
            timestamp=datetime.now(),
            region=current_stats.region,
            parameter=current_stats.parameter,
            total_samples=current_stats.total_count,
            alert_samples=current_stats.alert_count,
            alert_proportion=current_stats.alert_proportion,
            current_mean=current_stats.mean_value,
            previous_mean=previous_stats.mean_value,
            trend_increase=trend_increase,
            alert_level=alert_level,
            contributing_observations=[obs[0] for obs in contributing_obs],
            suggested_action=self._get_suggested_action(current_stats.parameter, alert_level)
        )
        
        return alert
    
    def _get_suggested_action(self, parameter: str, level: str) -> str:
        """Retorna sugestão de ação baseada no parâmetro e nível do alerta"""
        actions = {
            'leukocytes': {
                'low': "Investigar possíveis infecções virais ou imunossupressão",
                'medium': "Reforçar vigilância para doenças infecciosas",
                'high': "Ativar protocolo de investigação in loco para surtos infecciosos"
            },
            'hemoglobin': {
                'low': "Avaliar possíveis anemias ou hemorragias",
                'medium': "Investigar causas nutricionais ou parasitárias",
                'high': "Verificar condições cardiopulmonares ou desidratação"
            },
            'platelets': {
                'low': "Avaliar para dengue ou outras infecções virais",
                'medium': "Monitorar casos de febre hemorrágica",
                'high': "Investigar processos inflamatórios ou neoplasias"
            }
        }
        
        return actions.get(parameter, {}).get(level, "Investigar alteração laboratorial coletiva")