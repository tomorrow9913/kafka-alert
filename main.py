import asyncio

from core.config import settings
from utils.logger import LogManager
from utils.kafka_manager import init_kafka_manager, get_kafka_manager
from callback import callbacks

logger = LogManager.get_logger(__name__)

async def main():
    """Initializes and runs the application."""
    if not settings.KAFKA_BROKERS:
        logger.error("No Kafka brokers configured. Please set KAFKA_BROKERS environment variable.")
        return

    logger.info("Initializing Kafka manager...")
    kafka_manager = init_kafka_manager(
        bootstrap_servers=settings.KAFKA_BROKERS,
        consumer_group=settings.KAFKA_CONSUMER_GROUP,
    )

    all_topic_sub_callbacks = callbacks.pop("all", [])
    
    logger.info(f"Subscribing to callbacks for topics: {list(callbacks.keys())}")
    for topic, topic_callbacks in callbacks.items():
        topic_callbacks.extend(all_topic_sub_callbacks)
        for callback in topic_callbacks:
            logger.info(f"Subscribing [{topic}] {callback.name}-{callback.func.__name__}")
            kafka_manager.register_callback(topic, callback.func)
    
    try:
        logger.info("Starting Kafka manager...")
        await kafka_manager.start()
        
        # Keep the application running
        while True:
            await asyncio.sleep(3600) # Sleep for a long time
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received.")
    finally:
        logger.info("Stopping Kafka manager...")
        await kafka_manager.stop()
        logger.info("Application shut down gracefully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
