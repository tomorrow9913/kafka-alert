import pytest
from unittest.mock import AsyncMock, MagicMock
from core.factory import AlertFactory


@pytest.mark.asyncio
async def test_email_full_flow_cc_bcc(factory_reset, mocker):
    """
    Test the full flow from Factory to EmailProvider, ensuring:
    1. _mail_meta is extracted.
    2. Render context is cleaned.
    3. EmailProvider correctly handles To/Cc/Bcc and Envelope.
    """
    # Setup Factory
    factory = AlertFactory()

    # Mock Renderer to avoid real file lookups and verify context
    factory.renderer = MagicMock()
    factory.renderer.render.return_value = "<html>Rendered Content</html>"

    # Spy on EmailProvider to check what it receives
    email_provider = factory.providers["email"]
    spy_send = mocker.spy(email_provider, "send")

    # Mock aiosmtplib to verify the final SMTP call
    mock_smtp_send = mocker.patch("aiosmtplib.send", new_callable=AsyncMock)

    # Test Data
    destination = ["user1@example.com", "user2@example.com"]
    mail_meta = {
        "subject": "Test Subject",
        "cc": ["manager@example.com"],
        "bcc": ["audit@example.com"],
    }
    data = {
        "_mail_meta": mail_meta,
        "_hidden_sys_id": "secret-123",
        "visible_var": "hello",
    }

    message = {
        "provider": "email",
        "template": "alert.html.j2",
        "destination": destination,
        "data": data,
    }

    # Execute
    await factory.process(message)

    # --- Assertions ---

    # 1. Verify Renderer Context (Context Cleaning)
    # The renderer should have been called with 'visible_var', but NOT '_mail_meta' or '_hidden_sys_id'
    factory.renderer.render.assert_called_once()
    call_args = factory.renderer.render.call_args
    render_context = call_args[0][1]  # Second argument is context

    assert "visible_var" in render_context
    assert "_mail_meta" not in render_context
    assert "_hidden_sys_id" not in render_context

    # 2. Verify Factory -> Provider Payload (Envelope Construction)
    spy_send.assert_called_once()
    provider_dest, provider_payload = spy_send.call_args[0]

    assert provider_dest == destination
    assert provider_payload["headers"] == mail_meta
    assert provider_payload["body"] == "<html>Rendered Content</html>"

    # 3. Verify SMTP Call (Envelope Recipients & Headers)
    mock_smtp_send.assert_called_once()
    call_args, call_kwargs = mock_smtp_send.call_args

    sent_message = call_args[0]
    recipients_arg = call_kwargs["recipients"]

    # Check MIME Headers
    assert sent_message["Subject"] == "Test Subject"
    assert sent_message["To"] == "user1@example.com,user2@example.com"
    assert sent_message["Cc"] == "manager@example.com"
    assert "Bcc" not in sent_message  # BCC must not be in headers

    # Check Envelope Recipients (Actual Delivery List)
    expected_recipients = set(
        [
            "user1@example.com",
            "user2@example.com",
            "manager@example.com",
            "audit@example.com",
        ]
    )
    assert set(recipients_arg) == expected_recipients


@pytest.mark.asyncio
async def test_email_simple_flow_no_meta(factory_reset, mocker):
    """
    Test simple flow without _mail_meta (Legacy support / Defaults)
    """
    factory = AlertFactory()
    factory.renderer = MagicMock()
    factory.renderer.render.return_value = "Simple Content"

    mock_smtp_send = mocker.patch("aiosmtplib.send", new_callable=AsyncMock)

    message = {
        "provider": "email",
        "template": "alert.html.j2",
        "destination": "user@example.com",
        "data": {
            "subject": "Legacy Subject"  # Should be picked up as fallback
        },
    }

    await factory.process(message)

    mock_smtp_send.assert_called_once()
    call_args, call_kwargs = mock_smtp_send.call_args
    sent_message = call_args[0]

    assert sent_message["Subject"] == "Legacy Subject"
    assert sent_message["To"] == "user@example.com"
    assert sent_message["Cc"] is None
