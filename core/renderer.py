import json
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateError
from typing import Dict, Any, Union
from utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class TemplateRenderer:
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = template_dir
        try:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Jinja2 environment: {e}")
            raise

    def render(
        self, template_name: str, data: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        """
        Render a template from a file with the given data.
        If the template ends with .json.j2, returns a Dict.
        If the template ends with .html.j2 or others, returns a String.
        """
        try:
            template = self.env.get_template(template_name)
            rendered_str = template.render(**data)

            if template_name.endswith(".json.j2"):
                return self._parse_json(rendered_str, template_name)

            return rendered_str

        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise
        except TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during rendering: {e}")
            raise

    def render_from_string(
        self, template_content: str, data: Dict[str, Any], is_json: bool = True
    ) -> Union[Dict[str, Any], str]:
        """
        Render a template from a raw string.
        """
        try:
            template = self.env.from_string(template_content)
            rendered_str = template.render(**data)

            if is_json:
                return self._parse_json(rendered_str, "raw_string_template")

            return rendered_str
        except Exception as e:
            logger.error(f"Error rendering template from string: {e}")
            raise

    def _parse_json(self, rendered_str: str, source_name: str) -> Dict[str, Any]:
        try:
            return json.loads(rendered_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error in {source_name}: {e}")
            logger.debug(f"Rendered Output: {rendered_str}")
            raise ValueError(f"Rendered template is not valid JSON: {e}")
