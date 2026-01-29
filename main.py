import asyncio

from src.core.config import settings
from src.utils.logger import LogManager
from src.utils.kafka_manager import init_kafka_manager
from src.callback import callbacks
from src.dispatcher import NotificationDispatcher

# --- Import Sender Providers ---
from src.sender_providers.provider.discord import DiscordProvider
from src.sender_providers.provider.slack import SlackProvider
from src.sender_providers.provider.email import EmailProvider

# --- Import Storage and Rendering Infrastructure ---
from src.storage_providers.provider.db_provider import DatabaseProvider
from src.storage_providers.provider.file_provider import FileSystemProvider
from src.storage_providers.storage_manager import TemplateStorageManager
from src.sender_providers.renderer import TemplateRenderer

logger = LogManager.get_logger(__name__)


async def main():
    """Initializes and runs the application."""
    if not settings.KAFKA_BROKERS:
        logger.error(
            "No Kafka brokers configured. Please set KAFKA_BROKERS environment variable."
        )
        return

    # 1. Initialize dynamic template storage and rendering engine
    try:
        logger.info("Initializing template storage providers...")
        db_provider = DatabaseProvider()
        file_provider = FileSystemProvider()

        # The order in the list defines the fallback chain: DB -> FileSystem
        storage_manager = TemplateStorageManager(providers=[db_provider, file_provider])

        # Create a single renderer instance backed by the storage manager
        renderer = TemplateRenderer(storage_manager=storage_manager)
        logger.info("Dynamic template engine initialized successfully.")

    except Exception as e:
        logger.critical(
            f"Failed to initialize the template storage system: {e}", exc_info=True
        )
        return

    # 2. Initialize sender providers with the shared renderer
    logger.info("Initializing notification sender providers...")
    providers = {
        "discord": DiscordProvider(renderer=renderer),
        "slack": SlackProvider(renderer=renderer),
        "email": EmailProvider(renderer=renderer),
    }
    dispatcher = NotificationDispatcher(providers=providers, db_provider=db_provider)
    logger.info("Notification dispatcher is ready.")

    # 3. Initialize and run the Kafka manager
    logger.info("Initializing Kafka manager...")
    kafka_manager = init_kafka_manager(
        bootstrap_servers=settings.KAFKA_BROKERS,
        consumer_group=settings.KAFKA_CONSUMER_GROUP,
        consumer_config=settings.KAFKA_CONSUMER_CONFIG,
        producer_config=settings.KAFKA_PRODUCER_CONFIG,
        callback_context=dispatcher,
    )

    all_topic_sub_callbacks = callbacks.pop("all", [])

    logger.info(f"Subscribing to callbacks for topics: {list(callbacks.keys())}")
    for topic, topic_callbacks in callbacks.items():
        topic_callbacks.extend(all_topic_sub_callbacks)
        for callback in topic_callbacks:
            logger.info(
                f"Subscribing [{topic}] {callback.name}-{callback.func.__name__}"
            )
            kafka_manager.register_callback(topic, callback.func)

    try:
        logger.info("Starting Kafka manager...")
        await kafka_manager.start()

        # Keep the application running by waiting on the consumer task
        if kafka_manager.consumer_task:
            logger.info("Consumer task started. Waiting for completion...")
            await kafka_manager.consumer_task
        else:
            logger.warning(
                "No consumer task running (no topics subscribed?). Waiting indefinitely..."
            )
            stop_event = asyncio.Event()
            await stop_event.wait()

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
