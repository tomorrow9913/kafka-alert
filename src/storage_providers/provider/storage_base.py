from __future__ import annotations

import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Dict, Optional

from src.schema.alert_schema import TemplateDto
from src.utils.logger import LogManager

logger = LogManager.get_logger(__name__)


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

        1. Checks the state cache. If a valid, non-stale entry exists, returns the cached content immediately.
        2. If the cache is stale or missing, performs a lightweight check (`get_latest_state`) on the storage.
        3. Compares the storage state with the cached state.
        4. If states match, updates the timestamp and returns the cached content.
        5. If states differ (or cache is missing), it fetches the full content, updates both caches, and returns the new content.
        """
        now = time.time()
        cached_state = self._state_cache.get(key)

        # 1. Memory First & TTL Check
        if (
            cached_state
            and (now - cached_state["last_checked"]) <= self.update_check_ttl
        ):
            logger.debug(f"State for '{key}' is fresh. Using memory cache.")
            return self._fetch_template(cached_state["version_id"], key)

        # 2. Lazy Validation: TTL expired or cache miss, perform lightweight check
        logger.debug(f"State for '{key}' is stale or missing. Checking storage.")
        latest_state = self.get_latest_state(key)

        # 3. Conditional Update
        if (
            cached_state
            and latest_state
            and cached_state["version_id"] == latest_state["version_id"]
            and cached_state["timestamp"] == latest_state["timestamp"]
        ):
            # State is the same, just update the check time and use cached content
            self._state_cache[key]["last_checked"] = now
            logger.debug(f"State for '{key}' unchanged. Refreshed timestamp.")
            return self._fetch_template(cached_state["version_id"], key)

        if latest_state:
            # State has changed or was missing. Update cache with the latest info.
            logger.info(f"State for '{key}' has changed or is new. Updating cache.")
            latest_state["last_checked"] = now
            self._state_cache[key] = latest_state
            # Invalidate the content cache for the new version_id to force a fresh fetch
            self._fetch_template.cache_clear()  # A bit aggressive, but ensures consistency
        elif key in self._state_cache:
            # The template was deleted from storage. Invalidate the cache.
            logger.info(f"Template '{key}' not found in storage. Invalidating cache.")
            del self._state_cache[key]
            self._fetch_template.cache_clear()

        # 4. Use the final confirmed state from the cache (or lack thereof)
        final_state = self._state_cache.get(key)
        if not final_state:
            return None

        # Retrieve content from the version_id-based LRU cache
        return self._fetch_template(final_state["version_id"], key)

    @abstractmethod
    def get_latest_state(self, key: str) -> Optional[dict]:
        """
        [Lightweight Check] Checks the underlying storage for the latest state of a template.
        This method should be implemented by concrete providers and be highly efficient.

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
    def _invalidate_cache(self, key: str):
        """Invalidates both state and content cache for a given key."""
        if key in self._state_cache:
            del self._state_cache[key]
            logger.info(f"Invalidated state cache for key '{key}'.")
        self._fetch_template.cache_clear()
        logger.info("Cleared content cache (LRU).")

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
