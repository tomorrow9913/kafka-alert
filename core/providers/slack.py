import aiohttp
from typing import Dict, Any, Union
from .base import BaseProvider
from utils.logger import LogManager

logger = LogManager.get_logger(__name__)

class SlackProvider(BaseProvider):
    async def send(self, destination: str, payload: Union[Dict[str, Any], str]) -> bool:
        """
        Sends a message to a Slack Webhook.
        
        Args:
            destination: Slack Webhook URL.
            payload: JSON payload (dict) usually containing 'text' or 'blocks'.
        """
        if not isinstance(payload, dict):
            # Fallback if string is passed
            payload = {"text": str(payload)}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(destination, json=payload) as response:
                    if 200 <= response.status < 300:
                        logger.info("Slack message sent successfully.")
                        return True
                    else:
                        text = await response.text()
                        logger.error(f"Failed to send Slack message. Status: {response.status}, Response: {text}")
                        return False
        except Exception as e:
            logger.error(f"Exception sending Slack message: {e}")
            return False
