from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Kafka Configuration
    kafka_brokers: Optional[str] = None
    kafka_group_id: str = 'alert-group'
    kafka_session_timeout_ms: int = 30000
    kafka_heartbeat_interval_ms: int = 10000
    kafka_max_poll_interval_ms: int = 300000
    kafka_auto_offset_reset: str = 'earliest'

    # Logging Configuration
    log_dir: str = 'logs'

    # Discord Configuration
    discord_webhook_url: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra env vars
    )

settings = Settings()
