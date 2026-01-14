import pytest
from unittest.mock import AsyncMock
from aiokafka import ConsumerRecord
from utils.kafka_manager import KafkaManager
from core.config import KafkaConsumerConfig, KafkaProducerConfig

@pytest.mark.asyncio
async def test_kafka_manager_consumption(mocker):
    # Mock AIOKafkaConsumer
    mock_consumer_cls = mocker.patch("utils.kafka_manager.AIOKafkaConsumer")
    mock_consumer_instance = AsyncMock()
    mock_consumer_cls.return_value = mock_consumer_instance
    
    # Mock Producer
    mocker.patch("utils.kafka_manager.AIOKafkaProducer", return_value=AsyncMock())

    # Mock Consumer iteration
    # We provide a dict value simulating successful deserialization
    record = ConsumerRecord(
        topic="test-topic", partition=0, offset=0, timestamp=0, timestamp_type=0,
        key=b"key", value={"test": "data"}, headers=[], checksum=0, serialized_key_size=0, serialized_value_size=0
    )
    
    async def async_iter():
        yield record
        # Yielding only one record then finishing iteration
        
    mock_consumer_instance.__aiter__.return_value = async_iter()
    mock_consumer_instance.topics = AsyncMock(return_value={"test-topic"})
    
    # Init Manager
    manager = KafkaManager(
        bootstrap_servers=["localhost:9092"],
        consumer_group="test-group",
        consumer_config=KafkaConsumerConfig(),
        producer_config=KafkaProducerConfig()
    )
    
    # Register Callback
    mock_callback = AsyncMock()
    manager.register_callback("test-topic", mock_callback)
    
    # Start
    await manager.start()
    
    # Wait for consumer task to finish
    if manager.consumer_task:
        await manager.consumer_task
    
    # Verify
    mock_callback.assert_called_once()
    args = mock_callback.call_args[0]
    msg = args[0]
    assert msg.topic == "test-topic"
    assert msg.value == {"test": "data"}

@pytest.mark.asyncio
async def test_kafka_manager_topic_filtering(mocker):
    # Test that callbacks for non-existent topics are removed
    mock_consumer_cls = mocker.patch("utils.kafka_manager.AIOKafkaConsumer")
    mock_consumer_instance = AsyncMock()
    mock_consumer_cls.return_value = mock_consumer_instance
    mocker.patch("utils.kafka_manager.AIOKafkaProducer", return_value=AsyncMock())

    # Mock available topics
    mock_consumer_instance.topics = AsyncMock(return_value={"existing-topic"})
    
    manager = KafkaManager(
        bootstrap_servers=["localhost:9092"],
        consumer_group="test-group",
        consumer_config=KafkaConsumerConfig(),
        producer_config=KafkaProducerConfig()
    )
    
    mock_cb1 = AsyncMock()
    mock_cb2 = AsyncMock()
    
    manager.register_callback("existing-topic", mock_cb1)
    manager.register_callback("missing-topic", mock_cb2)
    
    await manager.start()
    
    # Verify
    assert "existing-topic" in manager.subscribed_topics
    assert "missing-topic" not in manager.subscribed_topics
    
    # Cleanup
    await manager.stop()
