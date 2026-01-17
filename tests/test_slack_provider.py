import pytest
import json
from core.providers.slack import SlackProvider


class TestSlackProvider:
    """Unit tests for SlackProvider methods."""

    @pytest.fixture
    def provider(self):
        """Create a SlackProvider instance for testing."""
        return SlackProvider()

    def test_apply_template_rules(self, provider):
        """Test that apply_template_rules correctly formats template names."""
        # Test with simple template name
        result = provider.apply_template_rules("alert")
        assert result == "alert.json.j2"

        # Test with different template name
        result = provider.apply_template_rules("notification")
        assert result == "notification.json.j2"

        # Test with empty string
        result = provider.apply_template_rules("")
        assert result == ".json.j2"

    def test_format_payload_with_dict(self, provider):
        """Test format_payload with dict input."""
        # Test with dict input - should return the dict as-is
        rendered_content = {"text": "Hello", "blocks": []}
        metadata = {}
        result = provider.format_payload(rendered_content, metadata)
        assert result == rendered_content
        assert isinstance(result, dict)

    def test_format_payload_with_string(self, provider):
        """Test format_payload with JSON string input."""
        # Test with valid JSON string - should parse to dict
        rendered_content = '{"text": "Test message", "blocks": []}'
        metadata = {}
        result = provider.format_payload(rendered_content, metadata)
        assert isinstance(result, dict)
        assert result["text"] == "Test message"
        assert result["blocks"] == []

    def test_format_payload_with_complex_json(self, provider):
        """Test format_payload with complex JSON structure."""
        # Test with complex Block Kit structure
        rendered_content = json.dumps(
            {
                "text": "Fallback text",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "Hello *World*"},
                    }
                ],
            }
        )
        metadata = {"foo": "bar"}
        result = provider.format_payload(rendered_content, metadata)
        assert isinstance(result, dict)
        assert result["text"] == "Fallback text"
        assert len(result["blocks"]) == 1
        assert result["blocks"][0]["type"] == "section"

    def test_get_fallback_payload_structure(self, provider):
        """Test that get_fallback_payload returns correct Slack Block Kit structure."""
        error = ValueError("Test error message")
        context = {
            "topic": "test-topic",
            "partition": 0,
            "offset": 123,
            "timestamp": 1234567890,
            "key": "test-key",
            "value": {"data": "test"},
        }

        result = provider.get_fallback_payload(error, context)

        # Verify it's a dict
        assert isinstance(result, dict)

        # Verify top-level structure
        assert "text" in result
        assert "blocks" in result

        # Verify text field contains topic info
        assert "test-topic" in result["text"]
        assert "🚨" in result["text"]

        # Verify blocks structure
        blocks = result["blocks"]
        assert isinstance(blocks, list)
        assert len(blocks) == 4  # section, fields, section (error), section (data)

        # Verify first block (section)
        assert blocks[0]["type"] == "section"
        assert blocks[0]["text"]["type"] == "mrkdwn"
        assert "error occurred" in blocks[0]["text"]["text"].lower()

        # Verify second block (fields with Kafka context)
        assert blocks[1]["type"] == "section"
        fields = blocks[1]["fields"]
        assert len(fields) == 3  # topic, partition, offset
        assert any("Topic:" in field["text"] for field in fields)
        assert any("Partition:" in field["text"] for field in fields)
        assert any("Offset:" in field["text"] for field in fields)
        assert any("test-topic" in field["text"] for field in fields)
        assert any("0" in field["text"] for field in fields)
        assert any("123" in field["text"] for field in fields)

        # Verify third block (error message)
        assert blocks[2]["type"] == "section"
        assert "Error:" in blocks[2]["text"]["text"]
        assert "Test error message" in blocks[2]["text"]["text"]

        # Verify fourth block (original data)
        assert blocks[3]["type"] == "section"
        assert "Original Data:" in blocks[3]["text"]["text"]
        assert "test-topic" in blocks[3]["text"]["text"]

    def test_get_fallback_payload_with_minimal_context(self, provider):
        """Test fallback payload with minimal context (missing some fields)."""
        error = Exception("Minimal error")
        context = {}  # Empty context

        result = provider.get_fallback_payload(error, context)

        # Should still return valid structure
        assert isinstance(result, dict)
        assert "text" in result
        assert "blocks" in result

        # Should handle missing fields with 'N/A'
        text_content = json.dumps(result)
        assert "N/A" in text_content

    def test_get_fallback_payload_with_complex_context(self, provider):
        """Test fallback payload with complex context data."""
        error = RuntimeError("Complex error")
        context = {
            "topic": "production-alerts",
            "partition": 5,
            "offset": 999999,
            "nested": {"data": {"level": "critical", "message": "System failure"}},
        }

        result = provider.get_fallback_payload(error, context)

        # Verify the context is properly serialized in the payload
        blocks = result["blocks"]
        data_block = blocks[3]
        data_text = data_block["text"]["text"]

        # Should contain nested data as JSON
        assert "nested" in data_text
        assert "critical" in data_text
        assert "System failure" in data_text

    def test_get_fallback_payload_error_formatting(self, provider):
        """Test that error messages are properly formatted in fallback payload."""
        error = ValueError("This is a test\nerror with multiple\nlines")
        context = {"topic": "test"}

        result = provider.get_fallback_payload(error, context)

        # Find the error block
        error_block = result["blocks"][2]
        error_text = error_block["text"]["text"]

        # Should contain the error message
        assert "This is a test" in error_text
        assert "error with multiple" in error_text
        assert "lines" in error_text
