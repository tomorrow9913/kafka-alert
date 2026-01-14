import pytest
import json
from jinja2 import TemplateNotFound

def test_render_json_success(renderer, temp_template_dir):
    # Create a dummy json template
    p = temp_template_dir / "test.json.j2"
    p.write_text('{"key": "{{ value }}"}', encoding="utf-8")
    
    result = renderer.render("test.json.j2", {"value": "hello"})
    assert isinstance(result, dict)
    assert result["key"] == "hello"

def test_render_string_success(renderer, temp_template_dir):
    # Create a dummy html template
    p = temp_template_dir / "test.html.j2"
    p.write_text("<h1>{{ title }}</h1>", encoding="utf-8")
    
    result = renderer.render("test.html.j2", {"title": "Welcome"})
    assert isinstance(result, str)
    assert result == "<h1>Welcome</h1>"

def test_render_invalid_json(renderer, temp_template_dir):
    # Create a broken json template
    p = temp_template_dir / "broken.json.j2"
    p.write_text('{"key": {{ value }} }', encoding="utf-8") # Missing quotes if value is string
    
    with pytest.raises(ValueError, match="Rendered template is not valid JSON"):
        renderer.render("broken.json.j2", {"value": "hello"})

def test_template_not_found(renderer):
    with pytest.raises(TemplateNotFound):
        renderer.render("non_existent.j2", {})
