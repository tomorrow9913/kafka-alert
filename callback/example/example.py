from aiokafka import ConsumerRecord
from core.dispatcher import NotificationDispatcher
from core.renderer import TemplateRenderer
from core.providers.discord import DiscordProvider
from core.providers.slack import SlackProvider
from core.providers.email import EmailProvider
from utils.logger import LogManager

logger = LogManager.get_logger(__name__)

Z_INDEX = 0
ALERT_DISABLE = False


# Create instances of providers
discord_provider = DiscordProvider()
slack_provider = SlackProvider()
email_provider = EmailProvider()

# Create a dictionary of providers
providers = {
    "discord": discord_provider,
    "slack": slack_provider,
    "email": email_provider,
}

# Create an instance of the renderer
renderer = TemplateRenderer()

# Create an instance of the dispatcher
dispatcher = NotificationDispatcher(providers, renderer)


async def callback(msg: ConsumerRecord):
    """
    Callback for processing Kafka messages using the NotificationDispatcher.
    The message value is expected to be a JSON-deserialized dictionary.
    """
    logger.info(
        f"Received message on topic '{msg.topic}'. Processing with NotificationDispatcher..."
    )
    if msg.value:
        await dispatcher.process(msg.value)
    else:
        logger.warning(f"Skipping message with empty value on topic '{msg.topic}'.")
