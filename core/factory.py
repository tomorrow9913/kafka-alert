import json
from typing import Dict, Any

from .renderer import TemplateRenderer
from .providers.discord import DiscordProvider
from .providers.slack import SlackProvider
from .providers.email import EmailProvider
from utils.logger import LogManager
from core.config import settings

logger = LogManager.get_logger(__name__)

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
            "slack": SlackProvider(),
            "email": EmailProvider()
        }
        self.initialized = True
    
    async def process(self, message: Dict[str, Any]):
        """
        Process an alert message:
        1. Validate payload.
        2. Select provider.
        3. Render template (from file or string).
        4. Send message.
        """
        logger.debug(f"Processing message: {message}")
        
        provider_name = message.get("provider")
        template_name = message.get("template")
        template_content = message.get("template_content")
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
                destination = settings.DISCORD_WEBHOOK_URL
        
        if not destination:
            logger.error(f"No destination (URL/Address) found for provider '{provider_name}'.")
            return

        try:
            # Resolve Template & Render
            if template_content:
                # Direct UI structure rendering
                is_json = provider_name in ["discord", "slack"]
                rendered_payload = self.renderer.render_from_string(template_content, data, is_json=is_json)
            elif template_name:
                # File-based template rendering
                full_template_name = template_name
                if not full_template_name.endswith('.j2'):
                    if provider_name == 'discord':
                        full_template_name += '.json.j2'
                    elif provider_name == 'email':
                        full_template_name += '.html.j2'
                rendered_payload = self.renderer.render(full_template_name, data)
            else:
                logger.error("Neither 'template' nor 'template_content' provided.")
                return

            logger.info(f"Sending message via {provider_name} to {destination[:10]}...")
            await provider.send(destination, rendered_payload)
            
        except Exception as e:
            logger.error(f"Error in AlertFactory process: {e}")
            logger.info("Attempting to send fallback notification...")
            
            try:
                fallback_payload = self._create_fallback_payload(provider_name, e, data)
                if fallback_payload:
                    await provider.send(destination, fallback_payload)
                else:
                    logger.warning(f"No fallback payload created for provider {provider_name}")
            except Exception as fallback_error:
                logger.error(f"Failed to send fallback notification: {fallback_error}")

    def _create_fallback_payload(self, provider: str, error: Exception, data: Any) -> Any:
        """
        Generates a generic error message payload when rendering fails.
        """
        data_json = json.dumps(data, indent=2, default=str)
        error_msg = (
            f"⚠️ **Alert Rendering Failed**\n"
            f"Error: `{str(error)}`\n"
            f"Raw Data:\n```json\n{data_json}\n```"
        )

        if provider == "discord":
            return {"content": error_msg}
        elif provider == "slack":
            return {"text": error_msg}
        elif provider == "email":
            return {
                "subject": "[Error] Alert Rendering Failed",
                "body": error_msg
            }
        
        return None

# Global instance
factory = AlertFactory()