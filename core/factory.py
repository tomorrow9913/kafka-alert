import os
from typing import Dict, Any, Optional
from .renderer import TemplateRenderer
from .providers.discord import DiscordProvider
from utils.logger import setup_logging

logger = setup_logging(__name__)

class AlertFactory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlertFactory, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        self.renderer = TemplateRenderer()
        self.providers = {
            "discord": DiscordProvider(),
            # "slack": SlackProvider(), # To be implemented
            # "email": EmailProvider()  # To be implemented
        }
        self.initialized = True
    
    async def process(self, message: Dict[str, Any]):
        """
        Process an alert message:
        1. Validate payload.
        2. Select provider.
        3. Render template.
        4. Send message.
        """
        logger.debug(f"Processing message: {message}")
        
        provider_name = message.get("provider")
        template_name = message.get("template")
        data = message.get("data", {})
        destination = message.get("destination")
        
        if not provider_name:
            logger.error("Message missing 'provider' field.")
            return

        if provider_name not in self.providers:
            logger.error(f"Provider '{provider_name}' not supported.")
            return

        provider = self.providers[provider_name]

        # Resolve Destination
        if not destination:
            # Simple Env fallback logic for prototype
            if provider_name == "discord":
                destination = os.getenv("DISCORD_WEBHOOK_URL")
        
        if not destination:
            logger.error(f"No destination (URL/Address) found for provider '{provider_name}'.")
            return

        # Resolve Template
        if not template_name:
            logger.error("Message missing 'template' field.")
            return
            
        full_template_name = template_name
        if not full_template_name.endswith('.j2'):
            if provider_name == 'discord':
                full_template_name += '.json.j2'
            elif provider_name == 'email':
                full_template_name += '.html.j2'
            # Add more defaults if needed

        try:
            rendered_payload = self.renderer.render(full_template_name, data)
            logger.info(f"Sending message via {provider_name} to {destination[:10]}...")
            await provider.send(destination, rendered_payload)
            
        except Exception as e:
            logger.error(f"Error in AlertFactory process: {e}")

# Global instance
factory = AlertFactory()
