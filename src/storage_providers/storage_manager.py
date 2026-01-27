from typing import List, Optional

from src.schema.alert_schema import TemplateDto
from src.storage_providers.provider.storage_base import BaseStorageProvider
from src.utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class TemplateStorageManager:
    """
    Manages a chain of storage providers to retrieve and manage templates.

    This class implements the "Chain of Responsibility" and "Fallback" patterns.
    - Read Strategy: First-Win. It iterates through providers in order and returns
      the first successful result. This allows for seamless fallback (e.g., from DB to FileSystem).
    - Write Strategy: Primary-Only. All write operations are delegated exclusively
      to the first provider in the chain.
    """

    def __init__(self, providers: List[BaseStorageProvider]):
        if not providers:
            raise ValueError("At least one storage provider must be configured.")

        self.providers = providers
        self.primary_provider = providers[0]
        logger.info(
            f"Initialized TemplateStorageManager with providers: {[p.__class__.__name__ for p in providers]}"
        )

    # --- Read Operation (First-Win Strategy) ---
    def get_active_version(self, key: str) -> Optional[TemplateDto]:
        """
        Retrieves the active template by querying providers sequentially.
        It returns the result from the first provider that finds the template.
        """
        for provider in self.providers:
            try:
                template = provider.get_active_version(key)
                if template:
                    logger.debug(
                        f"Template '{key}' found in {provider.__class__.__name__}"
                    )
                    return template
            except Exception as e:
                # Log the error and try the next provider in the chain.
                logger.error(
                    f"Provider {provider.__class__.__name__} failed for key '{key}': {e}",
                    exc_info=True,
                )
                continue

        logger.warning(f"Template '{key}' not found in any available provider.")
        return None

    # --- Write Operations (Primary-Only Strategy) ---
    def push(
        self,
        key: str,
        content: str,
        created_by: str,
        desc: Optional[str] = None,
        checkout: bool = True,
    ) -> TemplateDto:
        """Delegates the 'push' operation to the primary provider."""
        logger.info(
            f"Pushing template '{key}' via {self.primary_provider.__class__.__name__}."
        )
        try:
            return self.primary_provider.push(key, content, created_by, desc, checkout)
        except NotImplementedError:
            logger.error(
                f"Primary provider {self.primary_provider.__class__.__name__} does not support 'push'."
            )
            raise

    def checkout(self, key: str, version_id: int, updated_by: str) -> None:
        """Delegates the 'checkout' operation to the primary provider."""
        logger.info(
            f"Checking out v{version_id} for '{key}' via {self.primary_provider.__class__.__name__}."
        )
        try:
            self.primary_provider.checkout(key, version_id, updated_by)
        except NotImplementedError:
            logger.error(
                f"Primary provider {self.primary_provider.__class__.__name__} does not support 'checkout'."
            )
            raise

    def delete_version(self, version_id: int, deleted_by: str) -> None:
        """Delegates the 'delete_version' operation to the primary provider."""
        logger.warning(
            f"Deleting template v{version_id} by '{deleted_by}' via {self.primary_provider.__class__.__name__}."
        )
        try:
            self.primary_provider.delete_version(version_id, deleted_by)
        except NotImplementedError:
            logger.error(
                f"Primary provider {self.primary_provider.__class__.__name__} does not support 'delete_version'."
            )
            raise
