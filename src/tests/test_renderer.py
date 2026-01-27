import pytest
import json  # Added missing import
import datetime

from src.schema.alert_schema import TemplateDto
from src.sender_providers.renderer import TemplateNotFoundError  # Added missing import


def test_render_json_success(renderer, mock_storage_manager):
    template_key = "test.json"
    mock_storage_manager.get_active_version.return_value = TemplateDto(
        version_id=1,
        template_key=template_key,
        content='{"key": "{{ value }}"}',
        updated_at=datetime.datetime.now(),
        updated_by="test_user",
        description="Test JSON template",
    )

    result = renderer.render(template_key, {"value": "hello"})
    mock_storage_manager.get_active_version.assert_called_once_with(template_key)
    assert isinstance(result, dict)
    assert result["key"] == "hello"


def test_render_string_success(renderer, mock_storage_manager):
    template_key = "test.html"
    mock_storage_manager.get_active_version.return_value = TemplateDto(
        version_id=1,
        template_key=template_key,
        content="<h1>{{ title }}</h1>",
        updated_at=datetime.datetime.now(),
        updated_by="test_user",
        description="Test HTML template",
    )

    result = renderer.render(template_key, {"title": "Welcome"})
    mock_storage_manager.get_active_version.assert_called_once_with(template_key)
    assert isinstance(result, str)
    assert result == "<h1>Welcome</h1>"


def test_render_invalid_json(renderer, mock_storage_manager):
    template_key = "broken.json"
    mock_storage_manager.get_active_version.return_value = TemplateDto(
        version_id=1,
        template_key=template_key,
        content='{"key": {{ value }} }',  # Malformed JSON
        updated_at=datetime.datetime.now(),
        updated_by="test_user",
        description="Broken JSON template",
    )

    with pytest.raises(ValueError, match=r"Rendered template '.*?' is not valid JSON"):
        renderer.render(template_key, {"value": "hello"})
    mock_storage_manager.get_active_version.assert_called_once_with(template_key)


def test_template_not_found(renderer, mock_storage_manager):
    template_key = "non_existent.json"
    mock_storage_manager.get_active_version.return_value = None  # Simulate not found

    with pytest.raises(TemplateNotFoundError):
        renderer.render(template_key, {})
    mock_storage_manager.get_active_version.assert_called_once_with(template_key)


def test_render_from_string_json(renderer):
    content = '{"hello": "{{ name }}"}'
    # The TemplateRenderer's _parse_json method is private, and render_from_string
    # does not check for .json suffix. So we manually check if the output is JSON.
    rendered_str = renderer.render_from_string(content, {"name": "world"})
    assert isinstance(rendered_str, str)
    assert json.loads(rendered_str) == {"hello": "world"}


def test_render_from_string_text(renderer):
    content = "Hello {{ name }}!"
    result = renderer.render_from_string(content, {"name": "world"})
    assert isinstance(result, str)
    assert result == "Hello world!"
