from __future__ import annotations

import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Dict, Optional

from src.schema.alert_schema import TemplateDto


class BaseStorageProvider(ABC):
    """
    Abstract base class for all storage providers.
    It defines a common interface for accessing template data and implements a two-layer caching mechanism.
    - Layer 1 (State Cache): Checks if the active version has changed (TTL-based).
    - Layer 2 (Content Cache): Permanently caches the immutable template content (LRU-based).

    Internal time-based logic uses float (Unix timestamp) for timezone safety and performance.
    """

    def __init__(self, update_check_ttl: int = 60):
        """
        Args:
            update_check_ttl: Time-to-live in seconds for the state cache.
        """
        self.update_check_ttl = update_check_ttl
        # [State Cache] Caches the latest known state of a template key.
        # Format: { "key": {"version_id": int, "timestamp": float, "last_checked": float} }
        self._state_cache: Dict[str, dict] = {}

    # --- Read Operations (Template Method Pattern) ---

    def get_active_version(self, key: str) -> Optional[TemplateDto]:
        """
        Gets the active template version for a given key, utilizing a two-layer cache.

        1. Checks the state cache with TTL.
        2. If the cache is stale or missing, calls `update_check()` to get the latest state from the storage.
        3. Once the active version ID is confirmed, retrieves the template content via the LRU cache (`_fetch_template`).
        """
        now = time.time()
        cached_state = self._state_cache.get(key)

        # Check if state cache is stale
        if (
            not cached_state
            or (now - cached_state["last_checked"]) > self.update_check_ttl
        ):
            latest_state = self.update_check(key)
            if latest_state:
                # Update state cache with the latest info and the current check time
                latest_state["last_checked"] = now
                self._state_cache[key] = latest_state
            # If storage returns nothing, and there was a cached state, update its 'last_checked' time
            elif cached_state:
                self._state_cache[key]["last_checked"] = now

        # Use the final confirmed state from the cache
        final_state = self._state_cache.get(key)
        if not final_state:
            return None

        # Retrieve content from the version_id-based LRU cache
        return self._fetch_template(final_state["version_id"], key)

    @abstractmethod
    def update_check(self, key: str) -> Optional[dict]:
        """
        Checks the underlying storage for the latest state of a template.
        This method should be implemented by concrete providers.

        Args:
            key: The template key (e.g., "discord/error_report").

        Returns:
            A dictionary containing the latest state, e.g., `{"version_id": 123, "timestamp": 1672531200.0}`.
            The timestamp represents the last update time in the storage (e.g., `updated_at` or `mtime`).
            Returns `None` if the key is not found.
        """
        pass

    @lru_cache(maxsize=128)
    def _fetch_template(self, version_id: int, key: str) -> Optional[TemplateDto]:
        """
        [Content Cache] Fetches the template content for a given version ID.
        This method is decorated with an LRU cache, so `_perform_fetch` is only called
        if the version ID is not already in the cache.
        """
        return self._perform_fetch(version_id, key)

    @abstractmethod
    def _perform_fetch(self, version_id: int, key: str) -> Optional[TemplateDto]:
        """
        Performs the actual data retrieval from the storage.
        This method should be implemented by concrete providers.

        Args:
            version_id: The unique ID of the template version.
            key: The template key, required by some providers to locate the data.

        Returns:
            A `TemplateDto` object or `None` if not found.
        """
        pass

    # --- Write Operations (Optional) ---

    def push(
        self,
        key: str,
        content: str,
        created_by: str,
        desc: Optional[str] = None,
        checkout: bool = True,
    ) -> TemplateDto:
        """
        Creates a new template version (history) and optionally checks it out as the active version.
        Should only be implemented by the primary provider.
        """
        raise NotImplementedError("This provider is read-only.")

    def checkout(self, key: str, version_id: int, updated_by: str) -> None:
        """
        Sets a specific version as the active version for a given key.
        Should only be implemented by the primary provider.
        """
        raise NotImplementedError("This provider is read-only.")

    def delete_version(self, version_id: int, deleted_by: str) -> None:
        """
        Deletes a specific inactive template version.
        Should only be implemented by the primary provider.
        """
        raise NotImplementedError("This provider is read-only.")
