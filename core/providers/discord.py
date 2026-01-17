import aiohttp
import json
from typing import Dict, Any, Union, List, Optional
from .base import BaseProvider
from utils.logger import LogManager
from core.config import settings

logger = LogManager.get_logger(__name__)


class DiscordProvider(BaseProvider):
    @property
    def default_destination(self) -> Optional[str]:
        return settings.DISCORD_WEBHOOK_URL

    def apply_template_rules(self, template_name: str) -> str:
        return f"{template_name}.json.j2"

    def format_payload(
        self, rendered_content: Union[Dict[str, Any], str], metadata: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        if isinstance(rendered_content, dict):
            return rendered_content
        try:
            return json.loads(rendered_content)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to decode rendered Discord payload as JSON: %s; content=%r",
                e,
                rendered_content,
            )
            # Fallback: return the original string; downstream send() will validate type.
            return rendered_content

    def get_fallback_payload(
        self, error: Exception, context: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        context_str = json.dumps(context, indent=2, ensure_ascii=False)
        return {
            "content": f"🚨 **Error processing Kafka message:**\n"
            f"**Topic:** {context.get('topic', 'N/A')}\n"
            f"**Partition:** {context.get('partition', 'N/A')}\n"
            f"**Offset:** {context.get('offset', 'N/A')}\n"
            f"**Error:** ```{error}```\n"
            f"**Original Data:** ```json\n{context_str}\n```"
        }

    async def send(
        self, destination: Union[str, List[str]], payload: Union[Dict[str, Any], str]
    ) -> bool:
        """
        Sends a message to a Discord Webhook.

        Args:
            destination: Discord Webhook URL.
            payload: JSON payload (dict).
        """
        if not isinstance(payload, dict):
            logger.error("DiscordProvider requires a dict payload.")
            return False

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
                            logger.info(f"Discord message sent successfully to {dest}.")
                            results.append(True)
                        else:
                            text = await response.text()
                            logger.error(
                                f"Failed to send Discord message to {dest}. Status: {response.status}, Response: {text}"
                            )
                            results.append(False)
            except Exception as e:
                logger.error(f"Exception sending Discord message to {dest}: {e}")
                results.append(False)

        return all(results)
