from typing import Any, Optional
from aiokafka import ConsumerRecord
from core.dispatcher import NotificationDispatcher
from utils.logger import LogManager

logger = LogManager.get_logger(__name__)

Z_INDEX = 0
ALERT_DISABLE = False


async def callback(msg: ConsumerRecord, context: Optional[Any] = None):
    """
    Callback for processing Kafka messages using the NotificationDispatcher.
    The message value is expected to be a JSON-deserialized dictionary.
    """
    if not isinstance(context, NotificationDispatcher):
        logger.error(
            f"Expected NotificationDispatcher in context, but got {type(context).__name__}"
        )
        return

    dispatcher: NotificationDispatcher = context

    logger.info(
        f"Received message on topic '{msg.topic}'. Processing with NotificationDispatcher..."
    )
    if msg.value:
        # Enrich the message with Kafka metadata
        enriched_message = {
            **msg.value,
            "_kafka_meta": {
                "topic": msg.topic,
                "partition": msg.partition,
                "offset": msg.offset,
            }
        }
        await dispatcher.process(enriched_message)
    else:
        logger.warning(f"Skipping message with empty value on topic '{msg.topic}'.")
