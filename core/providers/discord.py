import aiohttp
from typing import Dict, Any, Union
from .base import BaseProvider
from utils.logger import LogManager

logger = LogManager.get_logger(__name__)

class DiscordProvider(BaseProvider):
    async def send(self, destination: str, payload: Union[Dict[str, Any], str]) -> bool:
        """
        Sends a message to a Discord Webhook.
        
        Args:
            destination: Discord Webhook URL.
            payload: JSON payload (dict).
        """
        if not isinstance(payload, dict):
            logger.error("DiscordProvider requires a dict payload.")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(destination, json=payload) as response:
                    if 200 <= response.status < 300:
                        logger.info("Discord message sent successfully.")
                        return True
                    else:
                        text = await response.text()
                        logger.error(f"Failed to send Discord message. Status: {response.status}, Response: {text}")
                        return False
        except Exception as e:
            logger.error(f"Exception sending Discord message: {e}")
            return False
