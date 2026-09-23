"""Opt-in public API checks; no credentials, model calls or uploads.

Run from the repository root with GOLD_DATASET_LIVE=1. Evidence is retained in
artifacts/live-tests; network and source contract failures are test failures.
"""

import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest

from huggingface_hub import HfApi

from infra.collection_store import CollectionStore
from infra.dataset_files import DatasetFiles
from infra.digikala import DigikalaClient
from infra.settings import SettingsLoader
from services.collection import CollectionService
from services.normalization import NormalizationService


@unittest.skipUnless(os.environ.get("GOLD_DATASET_LIVE") == "1", "Set GOLD_DATASET_LIVE=1 for public API calls")
class PublicApiTests(unittest.TestCase):
    def setUp(self):
        parent = Path("artifacts/live-tests")
        parent.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix=self._testMethodName + "-", dir=parent))
        print(f"\nLive evidence: {self.root}", flush=True)

    def test_digikala_one_page_and_normalization(self):
        original = SettingsLoader().load(Path("config.toml.sample")).crawl
        settings = replace(original, category_ids=original.category_ids[:1],
                           pages_per_category=1, concurrency=1,
                           output=str(self.root / "crawl"))
        service = CollectionService(settings, DigikalaClient(settings),
                                    CollectionStore(Path(settings.output)))
        manifest = asyncio.run(service.run())
        self.assertEqual(len(manifest["pages"]), 1)
        page = manifest["pages"][0]
        self.assertEqual(page["category_id"], settings.category_ids[0])
        self.assertEqual(page["page"], 1)
        raw = Path(page["file"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), page["sha256"])
        output = self.root / "products.jsonl"
        report = NormalizationService(DatasetFiles()).run(
            Path(settings.output) / "manifest.json", output)
        rows = DatasetFiles().read(output)
        self.assertGreater(len(rows), 0)
        self.assertEqual(report["products"], len(rows))
        self.assertEqual(len({row["record_id"] for row in rows}), len(rows))
        for row in rows:
            self.assertTrue(row["source"]["title"].strip())
            self.assertEqual(row["currency"], "IRR")
            self.assertEqual(row["observations"][0]["sha256"], page["sha256"])

    def test_pinned_hub_card_and_schema(self):
        freeze = tomllib.loads(Path("releases/v2.1.freeze.toml").read_text())
        names = ["README.md", "schemas/gold-semantic-2.0.schema.json"]
        # Force network downloads into a new destination; do not use cached tokens.
        folder = Path(HfApi(token=False).snapshot_download(
            repo_id=freeze["repo_id"], repo_type="dataset", revision=freeze["revision"],
            allow_patterns=names, local_dir=self.root / "hub", force_download=True,
            max_workers=1))
        for name in names:
            raw = (folder / name).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), freeze["files"][name]["sha256"])
            self.assertEqual(len(raw), freeze["files"][name]["bytes"])
        schema = json.loads((folder / names[1]).read_bytes())
        self.assertEqual(schema["properties"]["schema_version"]["const"], "gold-semantic/2.0")
