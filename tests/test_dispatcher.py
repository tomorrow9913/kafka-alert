import pytest
from unittest.mock import AsyncMock, MagicMock
from core.dispatcher import NotificationDispatcher
from core.renderer import TemplateRenderer
from core.providers.base import BaseProvider


@pytest.mark.asyncio
async def test_process_success():
    # Setup
    mock_renderer = MagicMock(spec=TemplateRenderer)
    mock_provider = MagicMock(spec=BaseProvider)
    mock_provider.send = AsyncMock(return_value=True)

    mock_renderer.render.return_value = "rendered content"
    mock_provider.apply_template_rules.return_value = "template.txt"
    mock_provider.format_payload.return_value = {"key": "value"}

    providers = {"test_provider": mock_provider}
    dispatcher = NotificationDispatcher(providers, mock_renderer)

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
    mock_renderer.render.assert_called_once_with("template.txt", {"foo": "bar", "_meta": {}})
    mock_provider.format_payload.assert_called_once_with("rendered content", {})
    mock_provider.send.assert_called_once_with("dest", {"key": "value"})


@pytest.mark.asyncio
async def test_process_fallback():
    # Setup
    mock_renderer = MagicMock(spec=TemplateRenderer)
    mock_provider = MagicMock(spec=BaseProvider)
    mock_provider.send = AsyncMock()

    mock_renderer.render.side_effect = Exception("Rendering failed")
    mock_provider.get_fallback_payload.return_value = {"error": "message"}

    providers = {"test_provider": mock_provider}
    dispatcher = NotificationDispatcher(providers, mock_renderer)

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
    mock_renderer = MagicMock(spec=TemplateRenderer)
    mock_provider = MagicMock(spec=BaseProvider)
    mock_provider.send = AsyncMock(return_value=True)

    mock_renderer.render.return_value = "rendered content"
    mock_provider.apply_template_rules.return_value = "template.txt"
    mock_provider.format_payload.return_value = {"key": "value"}

    providers = {"test_provider": mock_provider}
    dispatcher = NotificationDispatcher(providers, mock_renderer)

    message = {
        "provider": "test_provider",
        "template": "template",
        "destination": "dest",
        "data": {
            "foo": "bar",
            "_mail_meta": {"subject": "Test Subject", "recipients": ["test@example.com"]},
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
    mock_renderer.render.assert_called_once_with("template.txt", expected_context)
    # The metadata should be extracted and passed to format_payload
    mock_provider.format_payload.assert_called_once_with(
        "rendered content", expected_metadata
    )
    mock_provider.send.assert_called_once_with("dest", {"key": "value"})
