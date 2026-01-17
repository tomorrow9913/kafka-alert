import pytest
from unittest.mock import AsyncMock, MagicMock
from core.dispatcher import NotificationDispatcher
from core.renderer import TemplateRenderer
from core.providers.email import EmailProvider


@pytest.mark.asyncio
async def test_email_full_flow(mocker):
    """
    Test the full flow from Dispatcher to EmailProvider.
    """
    # Setup
    mock_renderer = MagicMock(spec=TemplateRenderer)
    email_provider = EmailProvider()
    spy_send = mocker.spy(email_provider, "send")
    mock_smtp_send = mocker.patch("aiosmtplib.send", new_callable=AsyncMock)

    providers = {"email": email_provider}
    dispatcher = NotificationDispatcher(providers, mock_renderer)

    mock_renderer.render.return_value = "Test Subject\n<html>Rendered Content</html>"

    message = {
        "provider": "email",
        "template": "alert",
        "destination": "user@example.com",
        "data": {"foo": "bar"},
    }

    # Execute
    await dispatcher.process(message)

    # Assertions
    spy_send.assert_called_once()
    provider_dest, provider_payload = spy_send.call_args[0]

    assert provider_dest == "user@example.com"
    assert provider_payload["subject"] == "Test Subject"
    assert provider_payload["body"] == "<html>Rendered Content</html>"

    mock_smtp_send.assert_called_once()
    sent_message = mock_smtp_send.call_args[0][0]
    assert sent_message["Subject"] == "Test Subject"
    assert sent_message["To"] == "user@example.com"
