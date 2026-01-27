import json
from typing import Any, Dict, Union

from jinja2 import Environment, TemplateError

from src.storage_providers.storage_manager import TemplateStorageManager
from src.utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class TemplateRenderer:
    """
    Renders templates using Jinja2, sourcing template content from a dynamic TemplateStorageManager.
    """

    def __init__(self, storage_manager: TemplateStorageManager):
        """
        Initializes the renderer with a TemplateStorageManager.

        Args:
            storage_manager: The manager that provides access to the template storage chain (e.g., DB, File).
        """
        self.storage_manager = storage_manager
        # The environment is now simpler, as it only needs to handle string rendering.
        # Loaders are no longer needed here.
        self.env = Environment(autoescape=True, trim_blocks=True, lstrip_blocks=True)
        logger.info(
            "TemplateRenderer initialized with a dynamic TemplateStorageManager."
        )

    def render(
        self, template_key: str, context: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        """
        Renders a template identified by a key.

        1. Fetches the active template content using the TemplateStorageManager.
        2. Renders the content using Jinja2.
        3. Parses the output as JSON if the key indicates a JSON template.
        """
        logger.debug(f"Attempting to render template with key: '{template_key}'")

        # 1. Fetch the template from the storage manager
        template_dto = self.storage_manager.get_active_version(template_key)

        if not template_dto:
            logger.error(f"Template not found for key: '{template_key}'")
            raise TemplateNotFoundError(template_key)

        # 2. Render the content from the DTO
        try:
            template = self.env.from_string(template_dto.content)
            rendered_str = template.render(**context)

            # 3. Parse if it's a JSON template
            # We infer the type from the key, not the filename anymore.
            if template_key.endswith(".json"):
                return self._parse_json(rendered_str, template_key)

            return rendered_str
        except TemplateError as e:
            logger.error(f"Template rendering error for key '{template_key}': {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during rendering of key '{template_key}': {e}"
            )
            raise

    def render_from_string(self, template_content: str, context: Dict[str, Any]) -> str:
        """
        Renders a template from a raw string. This remains useful for previews or direct content.
        """
        try:
            template = self.env.from_string(template_content)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template from string: {e}")
            raise

    def _parse_json(self, rendered_str: str, source_name: str) -> Dict[str, Any]:
        try:
            return json.loads(rendered_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error in {source_name}: {e}")
            logger.debug(f"Rendered Output for {source_name}: {rendered_str}")
            raise ValueError(
                f"Rendered template '{source_name}' is not valid JSON: {e}"
            )


class TemplateNotFoundError(Exception):
    """Custom exception for when a template is not found in any provider."""

    def __init__(self, template_key):
        self.template_key = template_key
        super().__init__(
            f"Template '{template_key}' not found in any storage provider."
        )
