import pytest
from unittest.mock import AsyncMock, MagicMock
from src.dispatcher import NotificationDispatcher
from src.sender_providers.base import BaseSenderProvider


@pytest.mark.asyncio
async def test_process_success():
    # Setup
    mock_provider = MagicMock(spec=BaseSenderProvider)
    mock_provider.send = AsyncMock(return_value=True)
    mock_provider.render.return_value = "rendered content"
    mock_provider.apply_template_rules.return_value = "template.txt"
    mock_provider.format_payload.return_value = {"key": "value"}

    providers = {"test_provider": mock_provider}
    dispatcher = NotificationDispatcher(providers)

    message = {
        "provider": "test_provider",
        "template": "template",
        "destination": "dest",
        "data": {"foo": "bar"},
    }

    # Execute
    await dispatcher.process(message)

    # Verify
    mock_provider.apply_template_rules.assert_called_once_with("template")
    mock_provider.render.assert_called_once_with(
        template_path="template.txt",
        template_content=None,
        context={"foo": "bar", "_meta": {}},
    )
    mock_provider.format_payload.assert_called_once_with("rendered content", {})
    mock_provider.send.assert_called_once_with("dest", {"key": "value"})


@pytest.mark.asyncio
async def test_process_fallback():
    # Setup
    mock_provider = MagicMock(spec=BaseSenderProvider)
    mock_provider.send = AsyncMock()
    mock_provider.render.side_effect = Exception("Rendering failed")
    mock_provider.get_fallback_payload.return_value = {"error": "message"}

    providers = {"test_provider": mock_provider}
    dispatcher = NotificationDispatcher(providers)

    message = {
        "provider": "test_provider",
        "template": "template",
        "destination": "dest",
        "data": {"foo": "bar"},
    }

    # Execute
    await dispatcher.process(message)

    # Verify
    assert mock_provider.send.call_count == 1
    mock_provider.get_fallback_payload.assert_called_once()
    mock_provider.send.assert_called_once_with("dest", {"error": "message"})


@pytest.mark.asyncio
async def test_process_with_mail_meta():
    # Setup
    mock_provider = MagicMock(spec=BaseSenderProvider)
    mock_provider.send = AsyncMock(return_value=True)
    mock_provider.render.return_value = "rendered content"
    mock_provider.apply_template_rules.return_value = "template.txt"
    mock_provider.format_payload.return_value = {"key": "value"}

    providers = {"test_provider": mock_provider}
    dispatcher = NotificationDispatcher(providers)

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

    # Execute
    await dispatcher.process(message)

    # Verify
    expected_context = {
        "foo": "bar",
        "_meta": {"subject": "Test Subject", "recipients": ["test@example.com"]},
    }
    expected_metadata = {"subject": "Test Subject", "recipients": ["test@example.com"]}

    mock_provider.apply_template_rules.assert_called_once_with("template")
    # The _mail_meta should be removed from data, and only regular data should be passed to render
    mock_provider.render.assert_called_once_with(
        template_path="template.txt",
        template_content=None,
        context=expected_context,
    )
    # The metadata should be extracted and passed to format_payload
    mock_provider.format_payload.assert_called_once_with(
        "rendered content", expected_metadata
    )
    mock_provider.send.assert_called_once_with("dest", {"key": "value"})
