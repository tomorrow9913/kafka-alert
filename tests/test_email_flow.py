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


def test_apply_template_rules():
    """
    Test that apply_template_rules correctly appends the .html.j2 extension.
    """
    email_provider = EmailProvider()

    # Test with simple template name
    result = email_provider.apply_template_rules("alert")
    assert result == "alert.html.j2"

    # Test with template name containing path
    result = email_provider.apply_template_rules("notifications/error")
    assert result == "notifications/error.html.j2"

    # Test with empty string
    result = email_provider.apply_template_rules("")
    assert result == ".html.j2"


def test_format_payload_with_subject_in_metadata():
    """
    Test format_payload when subject is provided in metadata.
    """
    email_provider = EmailProvider()

    rendered_content = "<html><body>Email body content</body></html>"
    metadata = {
        "subject": "Test Subject",
        "cc": ["cc@example.com"],
        "bcc": ["bcc@example.com"],
    }

    result = email_provider.format_payload(rendered_content, metadata)

    assert result["subject"] == "Test Subject"
    assert result["body"] == "<html><body>Email body content</body></html>"
    assert result["meta"]["subject"] == "Test Subject"
    assert result["meta"]["cc"] == ["cc@example.com"]
    assert result["meta"]["bcc"] == ["bcc@example.com"]


def test_format_payload_uses_default_subject_from_config():
    """
    Test format_payload uses default subject from config when not in metadata.
    """
    email_provider = EmailProvider()

    rendered_content = (
        "Alert: System Error\n<html><body>Error details here</body></html>"
    )
    metadata = {}

    result = email_provider.format_payload(rendered_content, metadata)

    from core.config import settings

    assert result["subject"] == settings.EMAIL_CONFIG.DEFAULT_SUBJECT
    assert result["body"] == rendered_content
    assert result["meta"] == {}


def test_format_payload_uses_hardcoded_fallback_when_config_is_empty(mocker):
    """
    Test format_payload uses hardcoded subject when config default is empty.
    """
    mocker.patch("core.providers.email.settings.EMAIL_CONFIG.DEFAULT_SUBJECT", "")
    email_provider = EmailProvider()

    rendered_content = "Single Line Subject"
    metadata = {}

    result = email_provider.format_payload(rendered_content, metadata)

    assert result["subject"] == "Kafka Alert"
    assert result["body"] == rendered_content
    assert result["meta"] == {}


def test_format_payload_body_is_not_split():
    """
    Test format_payload does not split the body and uses default subject.
    """
    email_provider = EmailProvider()

    rendered_content = "  Subject with spaces  \n  Body with spaces  "
    metadata = {}

    result = email_provider.format_payload(rendered_content, metadata)

    from core.config import settings

    assert result["subject"] == settings.EMAIL_CONFIG.DEFAULT_SUBJECT
    assert result["body"] == rendered_content


def test_format_payload_invalid_type():
    """
    Test format_payload handles non-string rendered content.
    """
    email_provider = EmailProvider()

    # Test with dict instead of string
    rendered_content = {"key": "value"}
    metadata = {"subject": "Test"}

    result = email_provider.format_payload(rendered_content, metadata)

    assert result["subject"] == "Error"
    assert result["body"] == ""


def test_get_fallback_payload_basic():
    """
    Test get_fallback_payload generates correct error notification.
    """
    email_provider = EmailProvider()

    error = Exception("Template rendering failed")
    context = {
        "topic": "alerts",
        "partition": 0,
        "offset": 12345,
        "key": "test-key",
        "value": {"alert": "data"},
    }

    result = email_provider.get_fallback_payload(error, context)

    assert "subject" in result
    assert "body" in result
    assert result["subject"] == "🚨 Kafka Alert Error on Topic alerts"
    assert "alerts" in result["body"]
    assert "0" in result["body"]
    assert "12345" in result["body"]
    assert "Template rendering failed" in result["body"]
    assert "Original Data:" in result["body"]


def test_get_fallback_payload_missing_context_fields():
    """
    Test get_fallback_payload handles missing context fields gracefully.
    """
    email_provider = EmailProvider()

    error = Exception("Unknown error")
    context = {}  # Empty context

    result = email_provider.get_fallback_payload(error, context)

    assert result["subject"] == "🚨 Kafka Alert Error on Topic N/A"
    assert "N/A" in result["body"]
    assert "Unknown error" in result["body"]


def test_get_fallback_payload_unicode_handling():
    """
    Test get_fallback_payload handles unicode characters in context.
    """
    email_provider = EmailProvider()

    error = Exception("Error with émojis 🎉")
    context = {
        "topic": "unicode-topic",
        "partition": 1,
        "offset": 999,
        "data": {"message": "Hello 世界 🌍"},
    }

    result = email_provider.get_fallback_payload(error, context)

    assert result["subject"] == "🚨 Kafka Alert Error on Topic unicode-topic"
    assert "Error with émojis 🎉" in result["body"]
    assert "世界" in result["body"]
    assert "🌍" in result["body"]


def test_get_fallback_payload_html_structure():
    """
    Test get_fallback_payload generates valid HTML structure.
    """
    email_provider = EmailProvider()

    error = Exception("Test error")
    context = {
        "topic": "test-topic",
        "partition": 5,
        "offset": 100,
    }

    result = email_provider.get_fallback_payload(error, context)

    body = result["body"]
    assert "<h1>" in body
    assert "</h1>" in body
    assert "<p>" in body
    assert "</p>" in body
    assert "<strong>" in body
    assert "<pre>" in body
    assert "</pre>" in body
    assert "<h2>" in body
    assert "</h2>" in body
