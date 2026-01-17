import aiohttp
import json
from typing import Dict, Any, Union, List, Optional
from .base import BaseProvider
from utils.logger import LogManager
from core.config import settings

logger = LogManager.get_logger(__name__)


class SlackProvider(BaseProvider):
    @property
    def default_destination(self) -> Optional[str]:
        return settings.SLACK_WEBHOOK_URL

    def apply_template_rules(self, template_name: str) -> str:
        return f"{template_name}.json.j2"

    def format_payload(
        self, rendered_content: Union[Dict[str, Any], str], metadata: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        if isinstance(rendered_content, dict):
            return rendered_content
        return json.loads(rendered_content)

    def get_fallback_payload(
        self, error: Exception, context: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        context_str = json.dumps(context, indent=2, ensure_ascii=False)
        return {
            "text": f"🚨 Error processing Kafka message on topic {context.get('topic', 'N/A')}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "An error occurred while processing a Kafka message.",
                    },
                },
                {
                    "type": "fields",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Topic:*\n{context.get('topic', 'N/A')}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Partition:*\n{context.get('partition', 'N/A')}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Offset:*\n{context.get('offset', 'N/A')}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Error:*\n```{error}```"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Original Data:*\n```json\n{context_str}\n```",
                    },
                },
            ],
        }

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
