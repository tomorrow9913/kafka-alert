import functools
from typing import Any, Callable, Coroutine

from src.utils.kafka_manager import get_kafka_manager
from src.utils.logger import LogManager

logger = LogManager.get_logger(__name__)


def with_dlq_fallback(
    func: Callable[..., Coroutine[Any, Any, None]],
) -> Callable[..., Coroutine[Any, Any, None]]:
    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
        message = args[0] if args else kwargs.get("message", {})
        provider_name = message.get("provider", "unknown")
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            logger.error(
                f"Error processing notification for {provider_name}: {e}",
                exc_info=True,
            )
            provider = self.providers.get(provider_name)
            if not provider:
                logger.error(f"Provider '{provider_name}' not found for fallback.")
                return

            destination = message.get("destination") or provider.default_destination
            context = self._get_message_context(message)

            try:
                # Handle fallback
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
                kafka_manager = get_kafka_manager()
                await kafka_manager.send_to_dlq(
                    message=message,
                    provider_name=provider_name,
                    error=fallback_error,
                )

    return wrapper
