from typing import Dict, Any

from src.sender_providers.provider.sender_base import BaseSenderProvider
from src.utils.decorators import with_dlq_fallback
from src.utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class NotificationDispatcher:
    def __init__(self, providers: Dict[str, BaseSenderProvider]) -> None:
        self.providers = providers

    @with_dlq_fallback
    async def process(self, message: Dict[str, Any]) -> None:
        """
        Orchestrates the processing of a notification message.

        1.  Selects the appropriate provider.
        2.  Determines the destination.
        3.  Delegates rendering to the provider.
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

        template_name = message.get("template")
        template_content = message.get("template_content")

        if not template_name and not template_content:
            logger.error(f"Invalid or missing template for provider '{provider_name}'.")
            return

        context = self._get_message_context(message)

        # 1. Apply template rules (only if template_name is present)
        if template_name:
            template_name = provider.apply_template_rules(template_name)

        # 2. Delegate rendering to the provider
        rendered_content = provider.render(
            template_path=template_name,
            template_content=template_content,
            context=context,
        )

        # 3. Format payload
        metadata = context.get("_meta", {})
        payload = provider.format_payload(rendered_content, metadata)

        # 4. Send
        await provider.send(destination, payload)
        logger.info(f"Notification sent successfully via {provider_name}.")

    def _get_message_context(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts the rendering context and metadata from the message data."""
        # Extract Kafka metadata if present
        kafka_meta = message.get("_kafka_meta", {})

        data = message.get("data", {})
        if isinstance(data, dict):
            meta = data.pop("_mail_meta", {})
            context = {k: v for k, v in data.items() if not k.startswith("_")}
            context["_meta"] = meta
            # Add Kafka metadata to context for fallback payloads
            if kafka_meta:
                context.update(
                    {
                        "topic": kafka_meta.get("topic"),
                        "partition": kafka_meta.get("partition"),
                        "offset": kafka_meta.get("offset"),
                    }
                )
            return context
        return {"data": data, **kafka_meta}
