from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Hemogramas Monitoring System"
    version: str = "1.0.0"
    database_url: str = "sqlite:///./hemogramas.db"
    
    # FHIR Configuration
    fhir_base_url: str = "http://localhost:8001/fhir"
    subscription_endpoint: str = "http://localhost:8000/fhir/subscription"
    
    # Analysis Configuration
    sliding_window_hours: int = 24
    min_samples_threshold: int = 30
    alert_proportion_threshold: float = 0.4
    trend_increase_threshold: float = 0.2
    
    class Config:
        env_file = ".env"

settings = Settings()