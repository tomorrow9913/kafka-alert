import pytest
from unittest.mock import AsyncMock, MagicMock
from aiokafka import ConsumerRecord
from utils.kafka_manager import KafkaManager
from core.config import KafkaConsumerConfig, KafkaProducerConfig
from core.dispatcher import NotificationDispatcher


@pytest.mark.asyncio
async def test_kafka_manager_consumption_with_dispatcher(mocker):
    # Mock AIOKafkaConsumer
    mock_consumer_cls = mocker.patch("utils.kafka_manager.AIOKafkaConsumer")
    mock_consumer_instance = AsyncMock()
    mock_consumer_cls.return_value = mock_consumer_instance

    # Mock Producer
    mocker.patch("utils.kafka_manager.AIOKafkaProducer", return_value=AsyncMock())

    # Mock NotificationDispatcher
    mock_dispatcher = AsyncMock(spec=NotificationDispatcher)
    mock_dispatcher.process = AsyncMock()

    # Mock Consumer iteration
    record_value = {"provider": "discord", "template": "test", "data": {"foo": "bar"}}
    record = ConsumerRecord(
        topic="test-topic",
        partition=0,
        offset=0,
        timestamp=0,
        timestamp_type=0,
        key=b"key",
        value=record_value,
        headers=[],
        checksum=0,
        serialized_key_size=0,
        serialized_value_size=0,
    )

    async def async_iter():
        yield record

    mock_consumer_instance.__aiter__.side_effect = lambda: async_iter()
    mock_consumer_instance.topics = AsyncMock(return_value={"test-topic"})
    mock_consumer_instance.subscribe = MagicMock()
    mock_consumer_instance.stop = AsyncMock()

    # Init Manager, passing the mock_dispatcher as callback_context
    manager = KafkaManager(
        bootstrap_servers=["localhost:9092"],
        consumer_group="test-group",
        consumer_config=KafkaConsumerConfig(),
        producer_config=KafkaProducerConfig(),
        callback_context=mock_dispatcher,
    )

    # Register Callback that uses the context
    async def test_callback(msg: ConsumerRecord, context: NotificationDispatcher):
        if msg.value:
            await context.process(msg.value)

    manager.register_callback("test-topic", test_callback)

    # Start
    await manager.start()

    # Wait for consumer task to finish
    if manager.consumer_task:
        await manager.consumer_task

    # Verify that dispatcher.process was called
    mock_dispatcher.process.assert_called_once_with(record_value)
    # Ensure the original mock_callback is not called
    # (since we replaced it with test_callback using the dispatcher)
    # mock_callback.assert_not_called()


@pytest.mark.asyncio
async def test_kafka_manager_topic_filtering(mocker):
    # Test that callbacks for non-existent topics are removed
    mock_consumer_cls = mocker.patch("utils.kafka_manager.AIOKafkaConsumer")
    mock_consumer_instance = AsyncMock()
    mock_consumer_cls.return_value = mock_consumer_instance
    mocker.patch("utils.kafka_manager.AIOKafkaProducer", return_value=AsyncMock())

    # Mock available topics
    mock_consumer_instance.topics = AsyncMock(return_value={"existing-topic"})
    mock_consumer_instance.subscribe = MagicMock()
    mock_consumer_instance.stop = AsyncMock()

    manager = KafkaManager(
        bootstrap_servers=["localhost:9092"],
        consumer_group="test-group",
        consumer_config=KafkaConsumerConfig(),
        producer_config=KafkaProducerConfig(),
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
