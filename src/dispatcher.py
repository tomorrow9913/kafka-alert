import json
from typing import Dict, Any, List

from cachetools import TTLCache  # type: ignore
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select

from src.sender_providers.provider.sender_base import BaseSenderProvider
from src.storage_providers.provider.db_provider import DatabaseProvider
from src.utils.decorators import with_dlq_fallback
from src.utils.logger import LogManager
from src.core.config import settings
from src.models import ResponsibleGroupNode, NotificationChannel
from src.schema.alert_schema import (
    AlertPayload,
    DirectAlertPayload,
    EventAlertPayload,
)

logger = LogManager.get_logger(__name__)


class NotificationDispatcher:
    def __init__(
        self,
        providers: Dict[str, BaseSenderProvider],
        db_provider: DatabaseProvider,
    ) -> None:
        self.providers = providers
        self.db_provider = db_provider

        # Initialize Cache
        self.routing_cache = TTLCache(
            maxsize=settings.APP_CONFIG.ROUTING_CACHE_MAXSIZE,
            ttl=settings.APP_CONFIG.ROUTING_CACHE_TTL,
        )

        # Initialize Pydantic Adapter for Validation
        self.payload_adapter: TypeAdapter[AlertPayload] = TypeAdapter(AlertPayload)

    @with_dlq_fallback
    async def process(self, message: Dict[str, Any]) -> None:
        """
        Orchestrates the processing of a notification message.
        Validates the schema first, then routes based on content.
        """
        # 1. Validate Schema
        try:
            # Pydantic v2 TypeAdapter Validation
            # 검증 후, 딕셔너리로 다시 변환하여 내부 로직에서 사용 (dump_python)
            # 혹은 validated_data 객체를 그대로 사용할 수도 있으나, 기존 로직 호환성을 위해 dict 유지
            validated_payload = self.payload_adapter.validate_python(message)
            # Serialize the validated model back to a dict for downstream compatibility
            message = validated_payload.model_dump(mode="json")
        except ValidationError as e:
            logger.error(f"Invalid AlertPayload format: {e}")
            raise e

        # 2. Routing Strategy
        if isinstance(validated_payload, EventAlertPayload):
            await self._dispatch_event(message)
        elif isinstance(validated_payload, DirectAlertPayload):
            await self._dispatch_direct(message)
        else:
            # This case should not be reached if validation is correct
            logger.error(
                "Routing failed: Validated payload is neither EventAlertPayload nor DirectAlertPayload."
            )
            raise TypeError("Validated payload has an unexpected type.")

    async def _dispatch_event(self, message: Dict[str, Any]) -> None:
        """Handles event-based dynamic routing with caching."""
        event = message.get("event")
        data = message.get("data", {})
        node_name = data.get("node")

        # 스키마 검증을 통과했으므로 node_name은 존재해야 하지만 안전하게 체크
        if not event or not node_name:
            logger.error("Routing failed: Missing 'event' or 'data.node' key.")
            return

        cache_key = (node_name, event)

        # 3. Cache Lookup
        if cache_key in self.routing_cache:
            channels = self.routing_cache[cache_key]
            logger.debug(f"Cache HIT for key: {cache_key}")
            # '정보 없음'에 대한 캐시 적중 시, 경고 로그만 남기고 조용히 종료
            if not channels:
                logger.warning(
                    f"Ignoring event for unregistered node/event (cached): Node='{node_name}', Event='{event}'"
                )
                return
        else:
            # 4. DB Lookup (Cache Miss)
            logger.debug(f"Cache MISS for key: {cache_key}. Querying DB.")
            channels = self._query_channels_from_db(node_name, event)

            if not channels:
                # [Critical] 미등록 노드/이벤트에 대한 명시적 에러 로깅
                logger.error(
                    f"Routing Error: No notification channels found for Node='{node_name}', Event='{event}'. "
                    "Check if the node is registered in 'ResponsibleGroupNode' and has linked channels."
                )

            # 5. Update Cache (Negative Caching 포함)
            self.routing_cache[cache_key] = channels
            logger.debug(
                f"Cache SET for key: {cache_key}, value count: {len(channels)}"
            )

        # 6. Fan-out Dispatch
        if channels:
            for channel in channels:
                await self._construct_and_send(channel, message)

    def _query_channels_from_db(
        self, node_name: str, event: str
    ) -> List[Dict[str, Any]]:
        """Queries the database to find notification channels for a given node and event."""
        try:
            with self.db_provider.get_db() as session:
                stmt = (
                    select(
                        NotificationChannel.provider,
                        NotificationChannel.destination,
                        NotificationChannel.template_key,
                        NotificationChannel.metadata_.label("metadata"),
                    )
                    .join(
                        ResponsibleGroupNode,
                        NotificationChannel.responsible_group_idx
                        == ResponsibleGroupNode.responsible_group_idx,
                    )
                    .where(
                        ResponsibleGroupNode.node_name == node_name,
                        NotificationChannel.event == event,
                    )
                )
                # mappings()를 사용하여 딕셔너리 형태로 변환 용이하게 함
                results = session.execute(stmt).mappings().all()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(
                f"DB Error querying channels for node '{node_name}', event '{event}': {e}",
                exc_info=True,
            )
            return []

    async def _construct_and_send(
        self, channel: Dict[str, Any], message: Dict[str, Any]
    ) -> None:
        """Constructs and sends a notification for a dynamically routed event."""
        provider_name = channel.get("provider")
        if not provider_name or provider_name not in self.providers:
            logger.error(f"Invalid or missing provider in channel: {provider_name}")
            return

        provider = self.providers[provider_name]

        # For event-based alerts, destination comes from the DB.
        # Allow override from message for testing purposes.
        destination = message.get("destination") or channel.get("destination")

        if not destination:
            logger.error(
                f"No destination found for provider '{provider_name}' in event-based flow."
            )
            return

        # Template comes from the DB.
        # Allow override from message for testing purposes.
        template_name = message.get("template") or channel.get("template_key")
        template_content = message.get("template_content")

        if not template_name and not template_content:
            logger.error(f"Invalid or missing template for provider '{provider_name}'.")
            return

        context = self._get_message_context(message)

        if template_name:
            template_name = provider.apply_template_rules(template_name)

        rendered_content = provider.render(
            template_path=template_name,
            template_content=template_content,
            context=context,
        )

        # Merge metadata: Channel Metadata (DB) + Message Metadata (Kafka)
        channel_metadata_str = channel.get("metadata")
        channel_metadata = {}
        if channel_metadata_str:
            if isinstance(channel_metadata_str, str):
                try:
                    channel_metadata = json.loads(channel_metadata_str)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse channel metadata JSON: {channel_metadata_str}"
                    )
            elif isinstance(channel_metadata_str, dict):
                channel_metadata = channel_metadata_str

        message_metadata = context.get("_meta", {})
        final_metadata = {**channel_metadata, **message_metadata}

        payload = provider.format_payload(rendered_content, final_metadata)

        await provider.send(destination, payload)
        logger.info(
            f"Event-based notification sent successfully via {provider_name} to {destination}."
        )

    async def _dispatch_direct(self, message: Dict[str, Any]) -> None:
        """
        Handles direct provider-based message dispatching (Legacy/Direct Mode).
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

        if template_name:
            template_name = provider.apply_template_rules(template_name)

        rendered_content = provider.render(
            template_path=template_name,
            template_content=template_content,
            context=context,
        )

        metadata = context.get("_meta", {})
        payload = provider.format_payload(rendered_content, metadata)

        await provider.send(destination, payload)
        logger.info(f"Direct notification sent successfully via {provider_name}.")

    def _get_message_context(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts the rendering context and metadata from the message data."""
        kafka_meta = message.get("_kafka_meta", {})

        data = message.get("data", {})
        if isinstance(data, dict):
            # Shallow copy to avoid modifying the original message dict
            context_data = data.copy()
            meta = context_data.pop("_mail_meta", {})
            context = {k: v for k, v in context_data.items() if not k.startswith("_")}
            context["_meta"] = meta
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
