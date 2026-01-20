from abc import ABC, abstractmethod
from typing import Dict, Any, Union, List, Optional
import json
from core.renderer import TemplateRenderer


class BaseProvider(ABC):
    def __init__(self, template_dir: str = "templates"):
        self.renderer = TemplateRenderer(template_dir)

    @property
    def default_destination(self) -> Optional[str]:
        """
        Get the default destination for the provider.

        Returns:
            Optional[str]: The default destination.
        """
        return None

    def render(
        self,
        template_path: Optional[str],
        template_content: Optional[str],
        context: Dict[str, Any],
    ) -> str:
        """
        Renders a template from a file or a string and ensures the output is a string.
        If rendering a .json.j2 template results in a dict, it's dumped to a JSON string.
        """
        if template_content:
            return self.renderer.render_from_string(template_content, context)

        if template_path:
            rendered_output = self.renderer.render(template_path, context)
            if isinstance(rendered_output, dict):
                return json.dumps(rendered_output)
            return str(rendered_output)

        raise ValueError("Either template_path or template_content must be provided.")

    @abstractmethod
    def apply_template_rules(self, template_name: str) -> str:
        """
        Apply provider-specific rules to the template name.

        Args:
            template_name: The base name of the template.

        Returns:
            str: The modified template name.
        """

    @abstractmethod
    def format_payload(
        self, rendered_content: str, metadata: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        """
        Format the rendered content into the final payload.

        Args:
            rendered_content: The content rendered from the template.
            metadata: Additional metadata for formatting.

        Returns:
            Union[Dict[str, Any], str]: The formatted payload.
        """

    @abstractmethod
    def get_fallback_payload(
        self, error: Exception, context: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        """
        Generate a fallback payload for when an error occurs.

        Args:
            error: The exception that occurred.
            context: The context of the error.

        Returns:
            Union[Dict[str, Any], str]: The fallback payload.
        """

    @abstractmethod
    async def send(
        self, destination: Union[str, List[str]], payload: Union[Dict[str, Any], str]
    ) -> bool:
        """
        Send a message to the provider.

        Args:
            destination: The target address (e.g., Webhook URL, Email address).
            payload: The message content (Dict for JSON APIs, str for others).

        Returns:
            bool: True if successful, False otherwise.
        """
