import utils.logger
from core.factory import factory

logger = utils.logger.setup_logging(__name__)

Z_INDEX = 0
ALERT_DISABLE = False

async def callback(key, value):
    logger.info(f"Received message. Processing with AlertFactory...")
    await factory.process(value)
