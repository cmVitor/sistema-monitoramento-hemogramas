from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://hemouser:hemopass@postgres-db:5432/hemogram"
    redis_url: str = "redis://localhost:6379/0"
    app_env: str = "local"
    hash_salt: str = "local-salt"

    class Config:
        env_prefix = ""
        env_file = None

settings = Settings()
