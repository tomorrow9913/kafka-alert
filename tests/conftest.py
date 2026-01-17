import pytest
from core.renderer import TemplateRenderer


@pytest.fixture
def temp_template_dir(tmp_path):
    d = tmp_path / "templates"
    d.mkdir()
    return d


@pytest.fixture
def renderer(temp_template_dir):
    return TemplateRenderer(template_dir=str(temp_template_dir))
