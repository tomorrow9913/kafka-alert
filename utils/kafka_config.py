from typing import Optional
from pydantic import BaseModel, Field

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
