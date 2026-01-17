from abc import ABC, abstractmethod
from typing import Dict, Any, Union, List


class BaseProvider(ABC):
    @abstractmethod
    def apply_template_rules(self, template_name: str) -> str:
        """
        Apply provider-specific rules to the template name.

        Args:
            template_name: The base name of the template.

        Returns:
            str: The modified template name.
        """
        pass

    @abstractmethod
    def format_payload(
        self, rendered_content: Union[Dict[str, Any], str], metadata: Dict[str, Any]
    ) -> Union[Dict[str, Any], str]:
        """
        Format the rendered content into the final payload.

        Args:
            rendered_content: The content rendered from the template.
            metadata: Additional metadata for formatting.

        Returns:
            Union[Dict[str, Any], str]: The formatted payload.
        """
        pass

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
        pass

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
        pass
