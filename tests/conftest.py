import pytest
import os
from core.renderer import TemplateRenderer
from core.factory import AlertFactory

@pytest.fixture
def temp_template_dir(tmp_path):
    d = tmp_path / "templates"
    d.mkdir()
    return d

@pytest.fixture
def renderer(temp_template_dir):
    return TemplateRenderer(template_dir=str(temp_template_dir))

@pytest.fixture
def factory_reset():
    AlertFactory._instance = None
    yield
    AlertFactory._instance = None
