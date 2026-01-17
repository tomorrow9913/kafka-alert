from typing import Dict, Any, Optional

from .renderer import TemplateRenderer
from .providers.base import BaseProvider
from utils.logger import LogManager
from core.config import settings

logger = LogManager.get_logger(__name__)


class NotificationDispatcher:
    def __init__(
        self, providers: Dict[str, BaseProvider], renderer: TemplateRenderer
    ) -> None:
        self.providers = providers
        self.renderer = renderer

    async def process(self, message: Dict[str, Any]) -> None:
        """
        Orchestrates the processing of a notification message.

        1.  Selects the appropriate provider.
        2.  Determines the destination.
        3.  Renders the template.
        4.  Formats the payload.
        5.  Sends the notification.
        6.  Handles errors and sends fallback messages.
        """
        provider_name = message.get("provider")
        if not provider_name or provider_name not in self.providers:
            logger.error(f"Invalid or missing provider: {provider_name}")
            return

        provider = self.providers[provider_name]
        destination = message.get("destination") or provider.default_destination

        if not destination:
            logger.error(f"No destination found for provider '{provider_name}'.")
            return

        context = self._get_message_context(message)

        try:
            # 1. Apply template rules
            template_name = provider.apply_template_rules(message["template"])

            # 2. Render template
            rendered_content = self.renderer.render(template_name, context)

            # 3. Format payload
            metadata = context.get("_meta", {})
            payload = provider.format_payload(rendered_content, metadata)

            # 4. Send
            await provider.send(destination, payload)
            logger.info(f"Notification sent successfully via {provider_name}.")

        except Exception as e:
            logger.error(
                f"Error processing notification for {provider_name}: {e}",
                exc_info=True,
            )
            try:
                # 5. Handle fallback
                fallback_payload = provider.get_fallback_payload(e, context)
                await provider.send(destination, fallback_payload)
                logger.info(
                    f"Fallback notification sent successfully via {provider_name}."
                )
            except Exception as fallback_error:
                logger.critical(
                    f"Failed to send fallback notification for {provider_name}: {fallback_error}",
                    exc_info=True,
                )

    def _get_default_destination(self, provider_name: str) -> Optional[str]:
        """Retrieves the default destination for a given provider."""
        if provider_name == "discord":
            return settings.DISCORD_WEBHOOK_URL
        if provider_name == "email":
            return settings.EMAIL_CONFIG.DEFAULT_TO_EMAIL
        if provider_name == "slack":
            return settings.SLACK_WEBHOOK_URL
        return None

    def _get_message_context(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts the rendering context and metadata from the message data."""
        data = message.get("data", {})
        if isinstance(data, dict):
            meta = data.pop("_mail_meta", {})
            context = {k: v for k, v in data.items() if not k.startswith("_")}
            context["_meta"] = meta
            return context
        return {"data": data}
