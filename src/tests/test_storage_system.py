import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from src.storage_providers.models import create_db_and_tables
from src.storage_providers.provider.db_provider import DatabaseProvider
from src.storage_providers.provider.file_provider import FileSystemProvider
from src.storage_providers.storage_manager import TemplateStorageManager


class TestStorageSystem(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_url = "sqlite:///:memory:"

        # Initialize providers
        self.db_provider = DatabaseProvider(db_url=self.db_url, update_check_ttl=1)
        create_db_and_tables(self.db_provider.engine)
        self.fs_provider = FileSystemProvider(template_dir=self.temp_dir)

        # Initialize manager
        self.manager = TemplateStorageManager(
            providers=[self.db_provider, self.fs_provider]
        )

        # Clear caches for a clean test
        for provider in self.manager.providers:
            provider._fetch_template.cache_clear()
            provider._state_cache.clear()

    def tearDown(self):
        """Clean up the test environment."""
        shutil.rmtree(self.temp_dir)
        # Clear caches after each test
        for provider in self.manager.providers:
            provider._fetch_template.cache_clear()
            provider._state_cache.clear()

    def _create_dummy_file(self, key, content):
        """Create a temporary template file."""
        path = os.path.join(self.temp_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_1_push_and_get_from_db(self):
        """Test pushing to and getting from the DB provider."""
        key = "email/db_test.json"
        content = '{"message": "Hello from DB, {{ name }}!"}'

        pushed_dto = self.manager.push(key, content, "tester")
        self.assertIsNotNone(pushed_dto)

        template = self.manager.get_active_version(key)
        self.assertIsNotNone(template)
        self.assertEqual(template.version_id, pushed_dto.version_id)
        self.assertEqual(template.content, content)
        self.assertEqual(template.updated_by, "tester")

    def test_2_fallback_to_filesystem(self):
        """Test if the manager falls back to the filesystem when the DB fails."""
        key = "email/fs_test.json"
        content = '{"message": "Hello from FileSystem, {{ name }}!"}'
        self._create_dummy_file(key, content)

        # Simulate DB provider failure
        with patch.object(
            self.db_provider,
            "get_active_version",
            side_effect=Exception("DB connection failed"),
        ):
            template = self.manager.get_active_version(key)
            self.assertIsNotNone(template)
            self.assertEqual(template.content, content)
            self.assertEqual(template.updated_by, "FileSystem")

    def test_3_state_cache_ttl(self):
        """Test if the state cache (TTL) works correctly."""
        key = "email/cache_test.json"
        self.manager.push(key, "content v1", "tester")

        with patch.object(
            self.db_provider, "update_check", wraps=self.db_provider.update_check
        ) as mock_update_check:
            # First call: cache is empty -> update_check is called
            self.manager.get_active_version(key)
            self.assertEqual(mock_update_check.call_count, 1)

            # Second call within TTL: uses cache -> update_check is not called
            self.manager.get_active_version(key)
            self.assertEqual(mock_update_check.call_count, 1)

            # Wait for TTL to expire (TTL is 1 second in setUp)
            time.sleep(1.5)

            # Third call after TTL expiry: cache is stale -> update_check is called again
            self.manager.get_active_version(key)
            self.assertEqual(mock_update_check.call_count, 2)

    def test_4_lru_cache_for_content(self):
        """Test if the content cache (LRU) works correctly."""
        key = "email/lru_test.json"

        pushed_dto = self.manager.push(key, "lru content", "lru_tester")
        version_id = pushed_dto.version_id

        # Clear cache and check info
        self.db_provider._fetch_template.cache_clear()
        info = self.db_provider._fetch_template.cache_info()
        self.assertEqual(info.hits, 0)
        self.assertEqual(info.misses, 0)

        # First call -> Miss
        self.db_provider._fetch_template(version_id, key)
        info = self.db_provider._fetch_template.cache_info()
        self.assertEqual(info.misses, 1)
        self.assertEqual(info.hits, 0)

        # Second call (same args) -> Hit
        self.db_provider._fetch_template(version_id, key)
        info = self.db_provider._fetch_template.cache_info()
        self.assertEqual(info.misses, 1)
        self.assertEqual(info.hits, 1)

    def test_5_checkout_and_version_change(self):
        """Test if checking out a different version updates the active version."""
        key = "email/checkout_test.json"

        # Push v1 and v2
        v1_dto = self.manager.push(key, "content v1", "tester", checkout=False)
        self.manager.push(key, "content v2", "tester", checkout=True)

        # Active version should be v2
        active_template = self.manager.get_active_version(key)
        self.assertIsNotNone(active_template)
        self.assertEqual(active_template.content, "content v2")

        # Checkout v1
        self.manager.checkout(key, v1_dto.version_id, "checker")

        # Clear the local state cache in the provider to force a re-fetch of the state
        if key in self.db_provider._state_cache:
            del self.db_provider._state_cache[key]

        # Active version should now be v1
        active_template_after_checkout = self.manager.get_active_version(key)
        self.assertIsNotNone(active_template_after_checkout)
        self.assertEqual(active_template_after_checkout.content, "content v1")
        self.assertEqual(active_template_after_checkout.updated_by, "checker")


if __name__ == "__main__":
    unittest.main()
