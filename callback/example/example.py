from aiokafka import ConsumerRecord
from core.factory import factory
from utils.logger import LogManager

logger = LogManager.get_logger(__name__)

Z_INDEX = 0
ALERT_DISABLE = False

async def callback(msg: ConsumerRecord):
    """
    Callback for processing Kafka messages using the AlertFactory.
    The message value is expected to be a JSON-deserialized dictionary.
    """
    logger.info(f"Received message on topic '{msg.topic}'. Processing with AlertFactory...")
    if msg.value:
        await factory.process(msg.value)
    else:
        logger.warning(f"Skipping message with empty value on topic '{msg.topic}'.")