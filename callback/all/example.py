import utils.logger

logger = utils.logger.setup_logging(__name__)

Z_INDEX = 0

async def callback(key, value):
    logger.info(f"Received {key}: {value}")