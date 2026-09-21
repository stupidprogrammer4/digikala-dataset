"""Infrastructure failures must preserve artifacts and source access policies."""

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import create_autospec, patch

import httpx
from huggingface_hub import HfApi

from infra.digikala import DigikalaClient
from infra.files import FileStore
from infra.hub import HubClient
from schemas.config import CrawlSettings, HubSettings


class FileStoreTests(unittest.TestCase):
    def test_failed_replace_preserves_previous_file_and_removes_temporary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "artifact.json"
            target.write_bytes(b"previous")
            with patch("infra.files.os.replace", side_effect=OSError("Disk error")):
                with self.assertRaises(OSError):
                    FileStore().write_bytes(target, b"replacement")
            self.assertEqual(target.read_bytes(), b"previous")
            self.assertEqual(list(root.iterdir()), [target])

    def test_failed_write_preserves_previous_file_and_removes_temporary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "artifact.json"
            target.write_bytes(b"previous")
            with tempfile.NamedTemporaryFile(dir=root, delete=False) as stream:
                with patch("infra.files.tempfile.NamedTemporaryFile") as open_temporary:
                    opened = open_temporary.return_value.__enter__.return_value
                    opened.name = stream.name
                    opened.write.side_effect = OSError("Disk full")
                    with self.assertRaises(OSError):
                        FileStore().write_bytes(target, b"replacement")
            self.assertEqual(target.read_bytes(), b"previous")
            self.assertEqual(list(root.iterdir()), [target])


class HubClientTests(unittest.TestCase):
    def setUp(self):
        self.api = create_autospec(HfApi, instance=True)
        self.client = HubClient(self.api)

    def test_download_keeps_configured_revision_and_destination(self):
        settings = HubSettings("example/products", "pinned-revision", "artifacts/source")
        self.api.snapshot_download.return_value = settings.local_dir
        self.assertEqual(self.client.download(settings), settings.local_dir)
        self.api.snapshot_download.assert_called_once_with(
            repo_id=settings.repo_id, repo_type="dataset", revision=settings.revision,
            local_dir=settings.local_dir)

    def test_upload_requires_a_new_branch_before_sending_files(self):
        for revision in ("", "main", "master"):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                self.client.upload(Path("artifacts/export"), "example/products", revision)
        self.api.create_branch.assert_not_called()
        self.api.create_branch.side_effect = RuntimeError("Branch already exists")
        with self.assertRaises(RuntimeError):
            self.client.upload(Path("artifacts/export"), "example/products", "existing-release")
        self.api.upload_folder.assert_not_called()

    def test_upload_targets_the_new_dataset_branch(self):
        self.api.upload_folder.return_value = SimpleNamespace(commit_url="https://example.org/commit")
        result = self.client.upload(Path("artifacts/export"), "example/products", "new-release")
        self.api.create_branch.assert_called_once_with(
            repo_id="example/products", repo_type="dataset", branch="new-release", exist_ok=False)
        self.api.upload_folder.assert_called_once_with(
            repo_id="example/products", repo_type="dataset", revision="new-release",
            folder_path="artifacts/export", commit_message="Publish new-release")
        self.assertEqual(result, "https://example.org/commit")


class AccessPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_robots_rate_serializes_collection_and_preserves_configured_delay(self):
        transport = httpx.MockTransport(lambda request: httpx.Response(
            200, text="User-agent: *\nAllow: /\nCrawl-delay: 2\nRequest-rate: 1/4\n"))
        for configured, expected in ((1, 4), (6, 6)):
            settings = CrawlSettings("https://example.org/{category_id}", [123], "unused",
                                     concurrency=3, delay_seconds=configured)
            async with DigikalaClient(settings, transport=transport) as client:
                self.assertEqual(client.concurrency, 1)
                self.assertEqual(client.delay, expected)

    async def test_robots_failure_closes_http_client_without_requesting_products(self):
        calls = []

        def handler(request):
            calls.append(request.url.path)
            return httpx.Response(503)

        settings = CrawlSettings("https://example.org/{category_id}", [123], "unused")
        client = DigikalaClient(settings, transport=httpx.MockTransport(handler))
        with self.assertRaises(httpx.HTTPStatusError):
            async with client:
                self.fail("Collection must not start without access rules")
        self.assertTrue(client.client.is_closed)
        self.assertEqual(calls, ["/robots.txt"])
