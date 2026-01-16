from abc import ABC, abstractmethod
from typing import Dict, Any, Union, List


class BaseProvider(ABC):
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
