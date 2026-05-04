from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Server configs
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    reload: bool = Field(True, env="RELOAD")
    log_level: str = Field("info", env="LOG_LEVEL")

    # API configs
    api_base_url: str = Field("http://localhost:8000", env="API_BASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # Security
    ai_service_internal_token: str = Field(..., env="AI_SERVICE_INTERNAL_TOKEN")
    allowed_origins: str = Field("http://localhost:3000", env="ALLOWED_ORIGINS")

    # AI Configs
    google_api_key: str = Field("", env="GOOGLE_API_KEY")
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    default_model: str = Field("gemini-2.0-flash", env="DEFAULT_MODEL")
    ollama_host: str = Field("http://localhost:11434", env="OLLAMA_HOST")
    ollama_model: str = Field("llama3.1:8b", env="OLLAMA_MODEL")

    # Databases
    database_url: str = Field("sqlite:///agno_scraper_agent.db", env="DATABASE_URL")
    worker_database_url: str = Field("postgresql://postgres:root@localhost:5432/chatcheckout", env="WORKER_DATABASE_URL")
    worker_redis_url: str = Field("redis://:redis_password_secret@localhost:6379/0", env="WORKER_REDIS_URL")

    # Storage (R2)
    r2_account_id: str = Field("", env="R2_ACCOUNT_ID")
    r2_access_key_id: str = Field("", env="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str = Field("", env="R2_SECRET_ACCESS_KEY")
    r2_bucket_name: str = Field("", env="R2_BUCKET_NAME")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
