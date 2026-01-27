import pytest
from unittest.mock import MagicMock
import datetime

# Import the actual classes
from src.storage_providers.storage_manager import TemplateStorageManager
from src.sender_providers.renderer import TemplateRenderer
from src.schema.alert_schema import TemplateDto


@pytest.fixture
def mock_storage_manager():
    """Provides a mock TemplateStorageManager for testing."""
    manager = MagicMock(spec=TemplateStorageManager)
    # Configure mock behavior for get_active_version
    # This mock behavior will be generic, individual tests can override it if needed.
    manager.get_active_version.return_value = TemplateDto(
        version_id=1,
        template_key="default/key",
        content="Default template content: {{ var }}",
        updated_at=datetime.datetime.now(),
        updated_by="mock_system",
        description="Mock template",
    )
    return manager


@pytest.fixture
def renderer(mock_storage_manager):
    """Provides a TemplateRenderer instance initialized with a mock storage manager."""
    return TemplateRenderer(storage_manager=mock_storage_manager)


# The temp_template_dir fixture is no longer directly used by the renderer,
# but might be used by FileSystemProvider if I ever test it directly.
# Keeping it for potential future use or other tests.
@pytest.fixture
def temp_template_dir(tmp_path):
    d = tmp_path / "templates"
    d.mkdir()
    return d
