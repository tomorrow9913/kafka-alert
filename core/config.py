from typing import Optional, List
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseModel):
    """Application-level configurations."""
    LOG_DIR: str = 'logs'
    LOG_LEVEL: str = 'INFO'
    LOG_NOTIFIER_URL: Optional[str] = None
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
    LOG_BACKUP_COUNT: int = 5
    ENV: str = "prod"

class KafkaConsumerConfig(BaseModel):
    """AIOKafkaConsumer-specific configurations."""
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000
    max_poll_interval_ms: int = 300000
    max_poll_records: int = 500

class KafkaProducerConfig(BaseModel):
    """AIOKafkaProducer-specific configurations."""
    acks: str = "all"
    retries: int = 3
    retry_backoff_ms: int = 100
    linger_ms: int = 0

class Settings(BaseSettings):
    """Main settings object that aggregates all configurations."""
    APP_CONFIG: AppConfig = AppConfig()

    # Kafka Configuration
    KAFKA_BROKERS: List[str] = ["localhost:9092"]
    KAFKA_CONSUMER_GROUP: str = 'alert-group'
    KAFKA_MAX_CONCURRENT_TASKS: int = 100
    
    # Kafka Detailed Configuration
    KAFKA_CONSUMER_CONFIG: KafkaConsumerConfig = KafkaConsumerConfig()
    KAFKA_PRODUCER_CONFIG: KafkaProducerConfig = KafkaProducerConfig()

    # Discord Configuration (from previous setup)
    DISCORD_WEBHOOK_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__', # For nested models like APP_CONFIG__LOG_LEVEL
        extra='ignore'
    )

# Singleton instance
settings = Settings()
