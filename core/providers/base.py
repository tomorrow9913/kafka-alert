from abc import ABC, abstractmethod
from typing import Dict, Any, Union

class BaseProvider(ABC):
    @abstractmethod
    async def send(self, destination: str, payload: Union[Dict[str, Any], str]) -> bool:
        """
        Send a message to the provider.
        
        Args:
            destination: The target address (e.g., Webhook URL, Email address).
            payload: The message content (Dict for JSON APIs, str for others).
            
        Returns:
            bool: True if successful, False otherwise.
        """
        pass
