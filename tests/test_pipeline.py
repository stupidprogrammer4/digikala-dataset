"""Offline collection, normalization and API annotation contracts."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from services.annotation import AnnotationService
from services.collection import CollectionService
from services.normalization import NormalizationService
from services.export import ExportService
from infra.annotation_store import AnnotationStore
from infra.annotation_contract import AnnotationContract
from infra.collection_store import CollectionStore
from infra.dataset_files import DatasetFiles
from infra.digikala import DigikalaClient
from infra.model_client import ModelClient
from infra.prompts import PromptStore
from infra.listing_parser import ListingParser
from infra.settings import SettingsLoader
from schemas.config import AnnotationSettings, CrawlSettings
from tools.evidence import source_input
from infra.files import FileStore
from tools.serialization import json_bytes
from fixtures.prompt_examples import examples


def listing(category=321, page=1, total_pages=2):
    return {"status": 200, "data": {"widgets": [{"type": "vertical_product_listing", "data": {
        "category": {"id": category, "title_fa": "Gold rings"},
        "pager": {"current_page": page, "total_pages": total_pages, "total_items": 2},
        "widgets": [{"type": "product", "data": {
            "id": 123, "title_fa": "Minimal gold ring for women",
            "url": {"uri": "/product/dkp-123/ring"}, "status": "marketable",
            "default_variant": {"status": "out_of_stock", "price": {"selling_price": 120000},
                                "themes": [{"label": "Gold weight", "value": {"title": "1 gram"}}]},
            "images": {"main": {"url": ["https://example.org/ring.jpg"]}},
        }}]}}]}}


async def collect(settings, *, transport):
    service = CollectionService(settings, DigikalaClient(settings, transport=transport),
                                CollectionStore(Path(settings.output)))
    return await service.run()


def normalize(manifest, output):
    return NormalizationService(DatasetFiles()).run(manifest, output)


async def annotate(source, output, settings, task):
    service = AnnotationService(ModelClient(settings), AnnotationStore(output),
                                AnnotationContract(), PromptStore())
    return await service.run(source, task)


def export_dataset(source, run, output):
    return ExportService(DatasetFiles(), AnnotationContract()).run(source, run, output)


class CollectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_configured_categories_resume_and_normalize(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = CrawlSettings("https://example.org/categories/{category_id}/products",
                                     [321], str(root / "crawl"), delay_seconds=0)
            calls = []

            def handler(request):
                calls.append(str(request.url))
                if request.url.path == "/robots.txt":
                    return httpx.Response(404)
                return httpx.Response(200, json=listing(page=int(request.url.params["page"])))

            transport = httpx.MockTransport(handler)
            first = await collect(settings, transport=transport)
            second = await collect(settings, transport=transport)
            self.assertEqual(first, second)
            self.assertEqual(sum('/categories/321/' in call for call in calls), 2)
            output = root / "products.jsonl"
            report = normalize(root / "crawl/manifest.json", output)
            self.assertEqual(report["products"], 1)
            product = FileStore().read_jsonl(output)[0]
            self.assertEqual(product["price"], 120000)
            self.assertEqual(product["currency"], "IRR")
            self.assertIsNone(product["available"])
            self.assertEqual(len(product["observations"]), 2)
            self.assertEqual(product["source"]["attributes"][0]["values"], ["1 gram"])
            with self.assertRaisesRegex(ValueError, "configuration changed"):
                await collect(replace(settings, category_ids=[999]), transport=transport)

    async def test_access_restriction_stops_without_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings = CrawlSettings("https://example.org/{category_id}", [321], temporary, delay_seconds=0)
            calls = []

            def handler(request):
                if request.url.path == "/robots.txt":
                    return httpx.Response(404)
                calls.append(str(request.url))
                return httpx.Response(429)

            with self.assertRaises(ExceptionGroup):
                await collect(settings, transport=httpx.MockTransport(handler))
            self.assertEqual(len(calls), 1)
            self.assertFalse((Path(temporary) / "manifest.json").exists())

    async def test_robots_disallow_prevents_product_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            calls = []

            def handler(request):
                calls.append(request.url.path)
                return httpx.Response(200, text="User-agent: *\nDisallow: /\n")

            settings = CrawlSettings("https://example.org/{category_id}", [321], temporary, delay_seconds=0)
            with self.assertRaises(ExceptionGroup):
                await collect(settings, transport=httpx.MockTransport(handler))
            self.assertEqual(calls, ["/robots.txt"])


class PromptContractTests(unittest.TestCase):
    def test_all_synthetic_examples_satisfy_schema_and_evidence_checks(self):
        for case in examples():
            with self.subTest(case=case["case"]):
                self.assertEqual(AnnotationContract().parse(json.dumps(case["expected"]), case["input"]), case["expected"])
        for task in ("labeling", "blind_review"):
            prompt, _ = PromptStore().load(task)
            self.assertLess(len(prompt.split()), 650)

    def test_wrong_identity_and_unsupported_quote_fail(self):
        case = examples()[0]
        invalid = deepcopy(case["expected"])
        invalid["record_id"] = "different-product"
        with self.assertRaises(ValueError):
            AnnotationContract().parse(json.dumps(invalid), case["input"])
        invalid = deepcopy(case["expected"])
        invalid["label"]["features"]["styles"][0]["evidence"] = ["Nonexistent words"]
        with self.assertRaisesRegex(ValueError, "evidence absent"):
            AnnotationContract().parse(json.dumps(invalid), case["input"])

    def test_input_drops_labels_and_keeps_only_source_fields(self):
        source = deepcopy(examples()[0]["input"])
        source["label"] = {"teacher_secret": "must not leak"}
        source["source"]["teacher_label"] = "must not leak"
        self.assertNotIn("must not leak", json.dumps(source_input(source)))

    def test_pagination_mismatch_is_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError, "different category or page"):
            ListingParser().parse(listing(), 999, 1)

    def test_category_ids_come_from_toml(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "settings.toml"
            config.write_text('[crawl]\nendpoint="https://example.org/{category_id}"\ncategory_ids=[123]\noutput="local"\n'
                              '[hub]\nrepo_id="example/data"\nrevision="pinned"\nlocal_dir="local"\n')
            self.assertEqual(SettingsLoader().load(config).crawl.category_ids, [123])


class AnnotationTests(unittest.IsolatedAsyncioTestCase):
    async def test_resume_export_and_changed_model(self):
        case = examples()[0]
        response = {"model": "reported-model", "usage": {"total_tokens": 100}, "choices": [
            {"finish_reason": "stop", "message": {"content": json.dumps(case["expected"])}}]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.jsonl"
            source.write_bytes(json_bytes(case["input"]))
            settings = AnnotationSettings(model="test/model")
            with patch.dict('os.environ', {"LLM_API_KEY": "not-a-real-secret"}), \
                    patch('infra.model_client.ModelClient.complete', new=AsyncMock(return_value=response)) as complete:
                summary = await annotate(source, root / "run", settings, "labeling")
                self.assertEqual(summary["succeeded"], 1)
                await annotate(source, root / "run", settings, "labeling")
                self.assertEqual(complete.await_count, 1)
                with self.assertRaisesRegex(ValueError, "changed"):
                    await annotate(source, root / "run", replace(settings, model="other"), "labeling")
            self.assertNotIn("not-a-real-secret", (root / "run/run.json").read_text())
            report = export_dataset(source, root / "run", root / "dataset.jsonl")
            self.assertEqual(report["products"], 1)
            exported = FileStore().read_jsonl(root / "dataset.jsonl")[0]
            self.assertEqual(exported["label"], case["expected"]["label"])
            self.assertIsNone(exported["human_review"])

    async def test_invalid_model_json_is_failure_and_cannot_be_exported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.jsonl"
            source.write_bytes(json_bytes(examples()[0]["input"]))
            response = {"choices": [{"finish_reason": "stop", "message": {"content": "not JSON"}}]}
            with patch.dict('os.environ', {"LLM_API_KEY": "not-a-real-secret"}), \
                    patch('infra.model_client.ModelClient.complete', new=AsyncMock(return_value=response)):
                result = await annotate(source, root / "run", AnnotationSettings(model="test/model"), "labeling")
                self.assertEqual(result["failed"], 1)
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                export_dataset(source, root / "run", root / "dataset.jsonl")
            self.assertFalse((root / "dataset.jsonl").exists())
