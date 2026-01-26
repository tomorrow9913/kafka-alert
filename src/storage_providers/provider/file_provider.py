from __future__ import annotations

import datetime
import os
from typing import Optional

from src.schema.alert_schema import TemplateDto
from src.storage_providers.provider.storage_base import BaseStorageProvider
from src.utils.logger import LogManager

logger = LogManager.get_logger(__name__)


class FileSystemProvider(BaseStorageProvider):
    """
    [Read-Only] A storage provider that uses the local file system as a fallback.
    - Write operations are not supported and will raise `NotImplementedError`.
    - A file's last modification time (mtime) is treated as its version and timestamp.
    """

    def __init__(self, template_dir: str = "src/templates", **kwargs):
        super().__init__(**kwargs)
        self.template_dir = template_dir
        if not os.path.isdir(self.template_dir):
            logger.error(f"Template directory not found: {self.template_dir}")
            raise ValueError(f"Template directory not found: {self.template_dir}")
        logger.info(
            f"FileSystemProvider initialized with directory: {self.template_dir}"
        )

    def _get_path(self, key: str) -> str:
        """Constructs the full file path for a given template key."""
        # Ensure the key is a safe relative path
        safe_key = os.path.normpath(os.path.join("/", key)).lstrip("/\\")
        return os.path.join(self.template_dir, safe_key)

    def update_check(self, key: str) -> Optional[dict]:
        """
        Checks the file's mtime to detect changes. The mtime (float) is used
        as both the version ID (int) and the update timestamp (float).
        """
        file_path = self._get_path(key)
        if not os.path.exists(file_path):
            return None

        try:
            mtime = os.path.getmtime(file_path)  # This is already a float timestamp
            logger.debug(f"Update check for '{key}': mtime is {mtime}.")
            return {"version_id": int(mtime), "timestamp": mtime}
        except OSError as e:
            logger.error(f"Error checking file '{file_path}': {e}")
            return None

    def _perform_fetch(self, version_id: int, key: str) -> Optional[TemplateDto]:
        """
        Reads the template content from the file system, but only if the current
        mtime matches the requested version_id.
        """
        file_path = self._get_path(key)
        logger.debug(
            f"Performing fetch for '{key}' (version: {version_id}) from FileSystem."
        )

        try:
            # Verify that the file hasn't changed since the update_check
            current_mtime = os.path.getmtime(file_path)
            if int(current_mtime) != version_id:
                logger.warning(
                    f"Template '{key}' was modified after the last check. "
                    f"Expected version {version_id}, found {int(current_mtime)}. Cache is stale."
                )
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return TemplateDto(
                version_id=version_id,
                template_key=key,
                content=content,
                updated_at=datetime.datetime.fromtimestamp(current_mtime),
                updated_by="FileSystem",
                description=f"Loaded from {file_path}",
            )
        except FileNotFoundError:
            logger.warning(f"Template file not found at path: {file_path}")
            return None
        except OSError as e:
            logger.error(f"Error reading file '{file_path}': {e}")
            return None
