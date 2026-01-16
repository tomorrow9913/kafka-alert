import aiohttp
from typing import Dict, Any, Union, List
from .base import BaseProvider
from utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class SlackProvider(BaseProvider):
    async def send(
        self, destination: Union[str, List[str]], payload: Union[Dict[str, Any], str]
    ) -> bool:
        """
        Sends a message to a Slack Webhook.

        Args:
            destination: Slack Webhook URL.
            payload: JSON payload (dict) usually containing 'text' or 'blocks'.
        """
        if not isinstance(payload, dict):
            # Fallback if string is passed
            payload = {"text": str(payload)}

        if isinstance(destination, str):
            destinations = [destination]
        else:
            destinations = destination

        results = []
        for dest in destinations:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(dest, json=payload) as response:
                        if 200 <= response.status < 300:
                            logger.info(f"Slack message sent successfully to {dest}.")
                            results.append(True)
                        else:
                            text = await response.text()
                            logger.error(
                                f"Failed to send Slack message to {dest}. Status: {response.status}, Response: {text}"
                            )
                            results.append(False)
            except Exception as e:
                logger.error(f"Exception sending Slack message to {dest}: {e}")
                results.append(False)

        return all(results)
