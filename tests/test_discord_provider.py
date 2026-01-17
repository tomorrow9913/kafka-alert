import pytest
import json
from core.providers.discord import DiscordProvider


@pytest.fixture
def discord_provider():
    """Fixture to create a DiscordProvider instance."""
    return DiscordProvider()


class TestApplyTemplateRules:
    """Tests for the apply_template_rules method."""

    def test_apply_template_rules_basic(self, discord_provider):
        """Test that apply_template_rules appends correct extension."""
        template_name = "alert"
        result = discord_provider.apply_template_rules(template_name)
        assert result == "alert.json.j2"

    def test_apply_template_rules_with_path(self, discord_provider):
        """Test apply_template_rules with a template name that includes path."""
        template_name = "notifications/alert"
        result = discord_provider.apply_template_rules(template_name)
        assert result == "notifications/alert.json.j2"

    def test_apply_template_rules_empty_string(self, discord_provider):
        """Test apply_template_rules with empty string."""
        template_name = ""
        result = discord_provider.apply_template_rules(template_name)
        assert result == ".json.j2"


class TestFormatPayload:
    """Tests for the format_payload method."""

    def test_format_payload_with_dict(self, discord_provider):
        """Test format_payload when rendered_content is already a dict."""
        rendered_content = {"content": "Hello Discord!"}
        metadata = {}
        result = discord_provider.format_payload(rendered_content, metadata)
        assert result == {"content": "Hello Discord!"}
        assert isinstance(result, dict)

    def test_format_payload_with_json_string(self, discord_provider):
        """Test format_payload when rendered_content is a JSON string."""
        rendered_content = '{"content": "Hello Discord!", "username": "Alert Bot"}'
        metadata = {}
        result = discord_provider.format_payload(rendered_content, metadata)
        assert result == {"content": "Hello Discord!", "username": "Alert Bot"}
        assert isinstance(result, dict)

    def test_format_payload_with_complex_dict(self, discord_provider):
        """Test format_payload with complex nested dict structure."""
        rendered_content = {
            "content": "Alert Message",
            "embeds": [
                {
                    "title": "Error Alert",
                    "description": "Something went wrong",
                    "color": 16711680,
                }
            ],
        }
        metadata = {}
        result = discord_provider.format_payload(rendered_content, metadata)
        assert result == rendered_content
        assert isinstance(result, dict)
        assert "embeds" in result

    def test_format_payload_with_complex_json_string(self, discord_provider):
        """Test format_payload with complex JSON string."""
        rendered_content = json.dumps(
            {
                "content": "Alert",
                "embeds": [{"title": "Test", "fields": [{"name": "Key", "value": "Val"}]}],
            }
        )
        metadata = {}
        result = discord_provider.format_payload(rendered_content, metadata)
        assert isinstance(result, dict)
        assert result["content"] == "Alert"
        assert len(result["embeds"]) == 1


class TestGetFallbackPayload:
    """Tests for the get_fallback_payload method."""

    def test_get_fallback_payload_with_full_context(self, discord_provider):
        """Test get_fallback_payload with complete Kafka context."""
        error = Exception("Template rendering failed")
        context = {
            "topic": "user-events",
            "partition": 3,
            "offset": 12345,
            "key": "user-123",
            "value": {"event": "login", "user_id": "123"},
        }
        result = discord_provider.get_fallback_payload(error, context)

        assert isinstance(result, dict)
        assert "content" in result
        assert "user-events" in result["content"]
        assert "3" in result["content"]
        assert "12345" in result["content"]
        assert "Template rendering failed" in result["content"]
        assert "```json" in result["content"]

    def test_get_fallback_payload_with_partial_context(self, discord_provider):
        """Test get_fallback_payload with partial Kafka context."""
        error = Exception("Connection timeout")
        context = {"topic": "alerts", "data": {"message": "test"}}
        result = discord_provider.get_fallback_payload(error, context)

        assert isinstance(result, dict)
        assert "content" in result
        assert "alerts" in result["content"]
        assert "N/A" in result["content"]  # For missing partition/offset
        assert "Connection timeout" in result["content"]

    def test_get_fallback_payload_with_empty_context(self, discord_provider):
        """Test get_fallback_payload with empty context."""
        error = Exception("Unknown error")
        context = {}
        result = discord_provider.get_fallback_payload(error, context)

        assert isinstance(result, dict)
        assert "content" in result
        assert "N/A" in result["content"]  # Should have N/A for all missing fields
        assert "Unknown error" in result["content"]

    def test_get_fallback_payload_with_unicode_content(self, discord_provider):
        """Test get_fallback_payload handles Unicode characters correctly."""
        error = Exception("エラーが発生しました")
        context = {
            "topic": "日本語トピック",
            "partition": 1,
            "offset": 100,
            "data": {"message": "テストメッセージ", "emoji": "🚨"},
        }
        result = discord_provider.get_fallback_payload(error, context)

        assert isinstance(result, dict)
        assert "content" in result
        assert "日本語トピック" in result["content"]
        assert "エラーが発生しました" in result["content"]
        # Verify that JSON serialization preserved Unicode
        assert "テストメッセージ" in result["content"]

    def test_get_fallback_payload_format(self, discord_provider):
        """Test that get_fallback_payload formats the message correctly."""
        error = Exception("Test error")
        context = {"topic": "test-topic", "partition": 0, "offset": 999}
        result = discord_provider.get_fallback_payload(error, context)

        content = result["content"]
        # Verify the structure of the message
        assert content.startswith("🚨 **Error processing Kafka message:**")
        assert "**Topic:**" in content
        assert "**Partition:**" in content
        assert "**Offset:**" in content
        assert "**Error:**" in content
        assert "**Original Data:**" in content
        assert "```json" in content

    def test_get_fallback_payload_json_serialization(self, discord_provider):
        """Test that context is properly serialized to JSON in fallback payload."""
        error = Exception("Serialization test")
        context = {
            "topic": "test",
            "partition": 1,
            "offset": 50,
            "nested": {"level1": {"level2": {"level3": "value"}}},
            "list": [1, 2, 3],
        }
        result = discord_provider.get_fallback_payload(error, context)

        assert isinstance(result, dict)
        content = result["content"]
        # Verify nested structures are in the JSON
        assert '"nested"' in content
        assert '"level1"' in content
        assert '"list"' in content
