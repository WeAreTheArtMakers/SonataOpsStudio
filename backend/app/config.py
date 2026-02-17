from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "sonataops-studio"
    env: str = "demo"
    log_level: str = "INFO"

    postgres_url: str = "postgresql://sonata:sonata@postgres:5432/sonataops"

    clickhouse_url: str = "http://clickhouse:8123"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "audio"
    minio_secure: bool = False
    public_minio_url: str = "http://localhost:9000"
    public_api_url: str = "http://localhost:8000"

    llm_provider: str = "groq"
    groq_api_key: str | None = None
    zai_api_key: str | None = None

    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"

    n8n_mock_mode: bool = True
    n8n_webhook_incident: str = "http://n8n:5678/webhook/incident-narrator"
    n8n_webhook_exec_brief: str = "http://n8n:5678/webhook/exec-brief-generator"
    n8n_webhook_anomaly_correlator: str = "http://n8n:5678/webhook/anomaly-correlator"

    promptops_require_approval: bool = True
    promptops_auto_approve: bool = True

    default_workspace_id: str = "demo-workspace"

    max_recent_operational_points: int = Field(default=500, ge=100, le=5000)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
