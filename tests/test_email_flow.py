import pytest
from unittest.mock import AsyncMock, MagicMock
from core.dispatcher import NotificationDispatcher
from core.renderer import TemplateRenderer
from core.providers.email import EmailProvider


@pytest.mark.asyncio
async def test_email_full_flow_with_meta(mocker):
    """
    Test the full flow from Dispatcher to EmailProvider with CC and BCC.
    """
    # Setup
    mock_renderer = MagicMock(spec=TemplateRenderer)
    email_provider = EmailProvider()
    spy_send = mocker.spy(email_provider, "send")
    mock_smtp_send = mocker.patch("aiosmtplib.send", new_callable=AsyncMock)

    providers = {"email": email_provider}
    dispatcher = NotificationDispatcher(providers, mock_renderer)

    mock_renderer.render.return_value = "<html>Rendered Content</html>"

    message = {
        "provider": "email",
        "template": "alert",
        "destination": "user@example.com",
        "data": {
            "_mail_meta": {
                "subject": "Test Subject from Meta",
                "cc": ["cc@example.com"],
                "bcc": ["bcc@example.com"],
            },
            "foo": "bar",
        },
    }

    # Execute
    await dispatcher.process(message)

    # Assertions
    spy_send.assert_called_once()
    provider_dest, provider_payload = spy_send.call_args[0]

    assert provider_dest == "user@example.com"
    assert provider_payload["subject"] == "Test Subject from Meta"
    assert provider_payload["body"] == "<html>Rendered Content</html>"
    assert provider_payload["meta"]["cc"] == ["cc@example.com"]

    mock_smtp_send.assert_called_once()
    sent_message = mock_smtp_send.call_args[0][0]
    recipients = mock_smtp_send.call_args[1]["recipients"]
    assert sent_message["Subject"] == "Test Subject from Meta"
    assert sent_message["To"] == "user@example.com"
    assert sent_message["Cc"] == "cc@example.com"
    assert "bcc" not in sent_message  # BCC should not be in headers
    assert set(recipients) == {"user@example.com", "cc@example.com", "bcc@example.com"}
