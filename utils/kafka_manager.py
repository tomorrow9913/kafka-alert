# -*- coding: utf-8 -*-
import asyncio
import json
from collections import defaultdict
from typing import Awaitable, Callable, Optional

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord

from utils.logger import LogManager
from core.config import (
    KafkaConsumerConfig,
    KafkaProducerConfig,
)

logger = LogManager.get_logger("kafka")

# Type hint for the callback function
MessageHandler = Callable[[ConsumerRecord], Awaitable[None]]


def _safe_json_deserializer(value: bytes) -> Optional[dict]:
    """
    Helper function to safely handle JSON deserialization errors.
    Prevents the entire consumer from crashing due to malformed messages.
    """
    try:
        return json.loads(value.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Failed to deserialize message value: {value!r}. Error: {e}")
        return None


class KafkaManager:
    """
    Manages the application's Kafka producers and consumers.
    Created via dependency injection and managed with the application's lifecycle.
    """
    def __init__(
        self,
        bootstrap_servers: list[str],
        consumer_group: str,
        consumer_config: KafkaConsumerConfig,
        producer_config: KafkaProducerConfig,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._consumer_group = consumer_group
        self._consumer_config = consumer_config
        self._producer_config = producer_config

        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._consumer_task: Optional[asyncio.Task[None]] = None
        self._callbacks: dict[str, list[MessageHandler]] = defaultdict(list)

    @property
    def subscribed_topics(self) -> list[str]:
        """Returns a list of all topics that are currently slated for subscription."""
        return list(self._callbacks.keys())

    def register_callback(self, topic: str, callback: MessageHandler):
        """Registers a message handling callback for a specific topic."""
        logger.info(f"Registering callback for topic '{topic}': {callback.__name__}")
        self._callbacks[topic].append(callback)

    async def get_all_topics(self) -> set[str]:
        """Fetches all topics present in the Kafka cluster. This method should be called after the consumer has started."""
        if not self.consumer:
            logger.warning("Consumer is not initialized. Cannot fetch topics.")
            return set()
        try:
            topics = await self.consumer.topics()
            return topics
        except Exception as e:
            logger.error(f"Failed to fetch topics from Kafka cluster: {e}", exc_info=True)
            return set()

    async def _run_consumer(self):
        """Continuously receives Kafka messages in the background and executes callbacks."""
        if not self.consumer:
            logger.warning("Consumer is not initialized. Cannot run consumer task.")
            return

        try:
            async for msg in self.consumer:
                if msg.value is None:
                    logger.debug(f"Skipping message with deserialization failure on topic '{msg.topic}'")
                    continue

                logger.debug(f"Message received: Topic={msg.topic}, Partition={msg.partition}, Offset={msg.offset}, Key={msg.key}, Header={msg.headers}, Value={msg.value}")
                if msg.topic in self._callbacks:
                    tasks = [self._execute_callback(cb, msg) for cb in self._callbacks[msg.topic]]
                    await asyncio.gather(*tasks)

        except asyncio.CancelledError:
            logger.info("Consumer task cancelled.")
        except Exception as e:
            logger.error(f"A critical error occurred in the consumer task: {e}", exc_info=True)
        finally:
            logger.info("Consumer task finished.")

    async def _execute_callback(self, callback: MessageHandler, msg: ConsumerRecord):
        """Safely executes a callback and logs exceptions."""
        try:
            await callback(msg)
        except Exception as e:
            logger.error(f"Error executing callback '{callback.__name__}' for topic '{msg.topic}': {e}", exc_info=True)

    async def start(self):
        """Starts the Kafka producer and consumer, and runs the consumer task in the background."""
        logger.info(f"Connecting to Kafka at {self._bootstrap_servers}...")
        try:
            producer_kwargs = self._producer_config.model_dump(exclude_none=True)
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                **producer_kwargs,
            )
            await self.producer.start()
            logger.info("Kafka Producer connected successfully.")

            if self.subscribed_topics:
                consumer_kwargs = self._consumer_config.model_dump(exclude_none=True)
                
                temp_consumer = AIOKafkaConsumer(
                    bootstrap_servers=self._bootstrap_servers,
                    group_id=self._consumer_group,
                    value_deserializer=_safe_json_deserializer,
                    **consumer_kwargs,
                )
                await temp_consumer.start()
                try:
                    all_cluster_topics = await temp_consumer.topics()
                    logger.info(f"Available topics in Kafka cluster: {all_cluster_topics}")
                    
                    configured_topics = list(self._callbacks.keys())
                    valid_topics = [t for t in configured_topics if t in all_cluster_topics]
                    invalid_topics = [t for t in configured_topics if t not in all_cluster_topics]

                    for t in invalid_topics:
                        logger.error(f"Configured topic '{t}' does not exist in Kafka cluster. Removing callbacks and will not subscribe.")
                        self._callbacks.pop(t, None)
                    
                    if not valid_topics:
                        logger.info("No valid existing topics to subscribe after filtering. Skipping consumer start.")
                        return

                    self.consumer = temp_consumer
                    self.consumer.subscribe(valid_topics)
                    logger.info(f"Kafka Consumer connected and subscribed to topics: {valid_topics}")
                    
                    self._consumer_task = asyncio.create_task(self._run_consumer())
                except Exception:
                    await temp_consumer.stop()
                    raise
            else:
                logger.info("No topics subscribed for consumer. Skipping consumer start.")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise

    async def stop(self):
        """Safely shuts down Kafka clients and background tasks."""
        logger.info("Disconnecting from Kafka...")
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                logger.info("Consumer task has been successfully cancelled.")

        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka Consumer disconnected.")
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka Producer disconnected.")

    async def send_message(self, topic: str, message: dict) -> Awaitable[ConsumerRecord]:
        """Sends a message to the specified topic and waits for a response."""
        if not self.producer:
            raise RuntimeError("Kafka Producer is not initialized or has been stopped.")
        try:
            future = await self.producer.send_and_wait(topic, value=message)
            logger.debug(f"Message sent and confirmed to topic '{topic}': {message}")
            return future
        except Exception as e:
            logger.error(f"Failed to send message to topic '{topic}': {e}")
            raise

    def send_message_async(self, topic: str, message: dict) -> asyncio.Future:
        """Asynchronously sends a message to the specified topic."""
        if not self.producer:
            raise RuntimeError("Kafka Producer is not initialized or has been stopped.")
        try:
            future = self.producer.send(topic, value=message)
            logger.debug(f"Message enqueued to be sent to topic '{topic}': {message}")
            return future
        except Exception as e:
            logger.error(f"Failed to enqueue message for topic '{topic}': {e}")
            raise

_kafka_manager_instance: Optional[KafkaManager] = None

def init_kafka_manager(
    bootstrap_servers: list[str],
    consumer_group: str,
    consumer_config: KafkaConsumerConfig = KafkaConsumerConfig(),
    producer_config: KafkaProducerConfig = KafkaProducerConfig(),
) -> KafkaManager:
    """Creates and initializes the KafkaManager instance at application startup."""
    global _kafka_manager_instance
    if _kafka_manager_instance is not None:
        logger.warning("KafkaManager is already initialized.")
        return _kafka_manager_instance

    _kafka_manager_instance = KafkaManager(
        bootstrap_servers=bootstrap_servers,
        consumer_group=consumer_group,
        consumer_config=consumer_config,
        producer_config=producer_config,
    )
    logger.info("KafkaManager initialized.")
    return _kafka_manager_instance

def get_kafka_manager() -> KafkaManager:
    """Returns the initialized KafkaManager instance."""
    if _kafka_manager_instance is None:
        raise RuntimeError("KafkaManager is not initialized. Call init_kafka_manager() first.")
    return _kafka_manager_instance
