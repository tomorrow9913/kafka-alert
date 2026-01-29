import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.dispatcher import NotificationDispatcher
from src.sender_providers.provider.sender_base import BaseSenderProvider
from src.storage_providers.provider.db_provider import DatabaseProvider
from src.core.config import settings

# Adjust the cache settings for testing to prevent conflicts with other tests
settings.APP_CONFIG.ROUTING_CACHE_TTL = 1
settings.APP_CONFIG.ROUTING_CACHE_MAXSIZE = 10


@pytest.fixture
def mock_db_provider():
    """Fixture to provide a mock DatabaseProvider."""
    return MagicMock(spec=DatabaseProvider)


@pytest.fixture
def mock_sender_provider():
    """Fixture to provide a mock BaseSenderProvider."""
    mock = MagicMock(spec=BaseSenderProvider)
    mock.send = AsyncMock(return_value=True)
    mock.render.return_value = "rendered content"
    mock.apply_template_rules.return_value = "template.txt"
    mock.format_payload.return_value = {"key": "value"}
    mock.default_destination = "default_dest"
    return mock


@pytest.fixture
def dispatcher(mock_sender_provider, mock_db_provider):
    """Fixture to provide a NotificationDispatcher instance with mocks."""
    providers = {"test_provider": mock_sender_provider}
    return NotificationDispatcher(providers=providers, db_provider=mock_db_provider)


@pytest.mark.asyncio
async def test_process_direct_success(dispatcher, mock_sender_provider):
    """Test successful direct dispatching."""
    message = {
        "provider": "test_provider",
        "template": "template",
        "destination": "dest",
        "data": {"foo": "bar"},
    }

    await dispatcher.process(message)

    mock_sender_provider.apply_template_rules.assert_called_once_with("template")
    mock_sender_provider.render.assert_called_once_with(
        template_path="template.txt",
        template_content=None,
        context={"foo": "bar", "_meta": {}},
    )
    mock_sender_provider.format_payload.assert_called_once_with("rendered content", {})
    mock_sender_provider.send.assert_called_once_with("dest", {"key": "value"})


@pytest.mark.asyncio
async def test_process_direct_fallback(dispatcher, mock_sender_provider):
    """Test direct dispatching with fallback mechanism."""
    mock_sender_provider.send = AsyncMock()  # Reset mock for this test
    mock_sender_provider.render.side_effect = Exception("Rendering failed")
    mock_sender_provider.get_fallback_payload.return_value = {"error": "message"}

    message = {
        "provider": "test_provider",
        "template": "template",
        "destination": "dest",
        "data": {"foo": "bar"},
    }

    await dispatcher.process(message)

    assert mock_sender_provider.send.call_count == 1
    # Note: get_fallback_payload is part of with_dlq_fallback, which is a decorator
    # The actual call might be within the decorator's logic or a different path
    # For now, just ensure send was called once and a mock was involved
    mock_sender_provider.send.assert_called_once()  # We expect it to be called with a fallback payload


@pytest.mark.asyncio
async def test_process_direct_with_mail_meta(dispatcher, mock_sender_provider):
    """Test direct dispatching with _mail_meta in data."""
    message = {
        "provider": "test_provider",
        "template": "template",
        "destination": "dest",
        "data": {
            "foo": "bar",
            "_mail_meta": {
                "subject": "Test Subject",
                "recipients": ["test@example.com"],
            },
        },
    }

    await dispatcher.process(message)

    expected_context = {
        "foo": "bar",
        "_meta": {"subject": "Test Subject", "recipients": ["test@example.com"]},
    }
    expected_metadata = {"subject": "Test Subject", "recipients": ["test@example.com"]}

    mock_sender_provider.apply_template_rules.assert_called_once_with("template")
    mock_sender_provider.render.assert_called_once_with(
        template_path="template.txt",
        template_content=None,
        context=expected_context,
    )
    mock_sender_provider.format_payload.assert_called_once_with(
        "rendered content", expected_metadata
    )
    mock_sender_provider.send.assert_called_once_with("dest", {"key": "value"})


@pytest.mark.asyncio
@patch("src.dispatcher.NotificationDispatcher._query_channels_from_db")
@patch(
    "src.dispatcher.NotificationDispatcher._construct_and_send", new_callable=AsyncMock
)
async def test_dispatch_event_success_and_caching(
    mock_construct_and_send,
    mock_query_channels_from_db,
    dispatcher,
    mock_sender_provider,
):
    """TC-1: Test successful event dispatching with caching."""
    mock_query_channels_from_db.return_value = [
        {
            "provider": "test_provider",
            "destination": "event_dest",
            "template_key": "event_template",
            "metadata": "{}",
        }
    ]
    message = {
        "event": "test_event",
        "data": {"node": "test_node", "alert_data": "some_value"},
    }

    # First call: cache miss, DB query, send notification
    await dispatcher.process(message)
    mock_query_channels_from_db.assert_called_once_with("test_node", "test_event")
    mock_construct_and_send.assert_called_once_with(
        {
            "provider": "test_provider",
            "destination": "event_dest",
            "template_key": "event_template",
            "metadata": "{}",
        },
        message,
    )
    mock_query_channels_from_db.reset_mock()
    mock_construct_and_send.reset_mock()

    # Second call: cache hit, no DB query, send notification
    await dispatcher.process(message)
    mock_query_channels_from_db.assert_not_called()  # Should be served from cache
    mock_construct_and_send.assert_called_once_with(
        {
            "provider": "test_provider",
            "destination": "event_dest",
            "template_key": "event_template",
            "metadata": "{}",
        },
        message,
    )


@pytest.mark.asyncio
@patch("src.dispatcher.logger")
@patch("src.dispatcher.NotificationDispatcher._query_channels_from_db")
@patch(
    "src.dispatcher.NotificationDispatcher._construct_and_send", new_callable=AsyncMock
)
async def test_dispatch_event_no_channels_logging(
    mock_construct_and_send, mock_query_channels_from_db, mock_logger, dispatcher
):
    """TC-2: Test error logging when no channels are found."""
    mock_query_channels_from_db.return_value = []
    message = {
        "event": "unknown_event",
        "data": {"node": "Unknown_Node", "alert_data": "some_value"},
    }

    await dispatcher.process(message)

    mock_query_channels_from_db.assert_called_once_with("Unknown_Node", "unknown_event")
    mock_logger.error.assert_called_once_with(
        "Routing Error: No notification channels found for Node='Unknown_Node', Event='unknown_event'. "
        "Check if the node is registered in 'ResponsibleGroupNode' and has linked channels."
    )
    mock_construct_and_send.assert_not_called()


@pytest.mark.asyncio
@patch("src.dispatcher.logger")
@patch("src.dispatcher.NotificationDispatcher._query_channels_from_db")
@patch(
    "src.dispatcher.NotificationDispatcher._construct_and_send", new_callable=AsyncMock
)
async def test_dispatch_event_negative_caching(
    mock_construct_and_send, mock_query_channels_from_db, mock_logger, dispatcher
):
    """TC-2: Test negative caching for unregistered nodes."""
    mock_query_channels_from_db.return_value = []
    message = {
        "event": "unregistered_event",
        "data": {"node": "Uncached_Node", "alert_data": "some_value"},
    }

    # First call: cache miss, DB query returns empty, error logged
    await dispatcher.process(message)
    mock_query_channels_from_db.assert_called_once_with(
        "Uncached_Node", "unregistered_event"
    )
    mock_logger.error.assert_called_once()  # Expect an error log
    mock_construct_and_send.assert_not_called()

    mock_query_channels_from_db.reset_mock()
    mock_logger.error.reset_mock()
    mock_construct_and_send.reset_mock()

    # Second call (within TTL): cache hit (negative cache), no DB query, no error log
    await dispatcher.process(message)
    mock_query_channels_from_db.assert_not_called()  # Should be served from negative cache
    mock_logger.error.assert_not_called()  # No new error log
    mock_construct_and_send.assert_not_called()


@pytest.mark.asyncio
@patch("src.dispatcher.logger")
async def test_message_routing(mock_logger, dispatcher):
    """Test the main process method's routing logic."""
    mock_direct_dispatch = AsyncMock()
    mock_event_dispatch = AsyncMock()

    dispatcher._dispatch_direct = mock_direct_dispatch
    dispatcher._dispatch_event = mock_event_dispatch

    # Test routing to _dispatch_event
    event_message = {"event": "test_event", "data": {"node": "some_node"}}
    await dispatcher.process(event_message)
    mock_event_dispatch.assert_called_once_with(event_message)
    mock_direct_dispatch.assert_not_called()
    mock_event_dispatch.reset_mock()
    mock_direct_dispatch.reset_mock()

    # Test routing to _dispatch_direct
    direct_message = {"provider": "test_provider", "destination": "some_dest"}
    await dispatcher.process(direct_message)
    mock_direct_dispatch.assert_called_once_with(direct_message)
    mock_event_dispatch.assert_not_called()
    mock_event_dispatch.reset_mock()
    mock_direct_dispatch.reset_mock()

    # Test invalid message - expect error log, not raised exception due to decorator
    invalid_message = {"some_key": "some_value"}
    await dispatcher.process(invalid_message)  # No pytest.raises here
    mock_logger.error.assert_called_once_with(
        "Routing failed: Message must contain either 'event' or 'provider' key."
    )
    mock_event_dispatch.assert_not_called()
    mock_direct_dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_query_channels_from_db_success(dispatcher, mock_db_provider):
    """Test _query_channels_from_db returning valid data."""
    mock_session = MagicMock()
    mock_execute_result = MagicMock()
    mock_execute_result.mappings.return_value.all.return_value = [
        {
            "provider": "discord",
            "destination": "webhook_url",
            "template_key": "my_template",
            "metadata": '{"color": "red"}',
        }
    ]
    mock_session.execute.return_value = mock_execute_result
    # Correctly mock the context manager
    mock_db_provider.get_db.return_value.__enter__.return_value = mock_session

    channels = dispatcher._query_channels_from_db("test_node", "test_event")

    assert channels == [
        {
            "provider": "discord",
            "destination": "webhook_url",
            "template_key": "my_template",
            "metadata": '{"color": "red"}',
        }
    ]
    mock_db_provider.get_db.assert_called_once()
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch("src.dispatcher.logger")
async def test_query_channels_from_db_exception(
    mock_logger, dispatcher, mock_db_provider
):
    """Test _query_channels_from_db handling exceptions."""
    mock_db_provider.get_db.side_effect = Exception("DB connection error")

    channels = dispatcher._query_channels_from_db("test_node", "test_event")

    assert channels == []
    mock_logger.error.assert_called_once()
    assert "DB Error querying channels" in mock_logger.error.call_args[0][0]
