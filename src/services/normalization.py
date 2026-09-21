"""Normalize a collected dataset while keeping all raw-page observations."""

from dataclasses import asdict
from pathlib import Path

from infra.dataset_files import DatasetFiles
from infra.listing_parser import ListingParser
from tools.normalization import normalize_product


class NormalizationService:
    def __init__(self, files: DatasetFiles, parser: ListingParser | None = None):
        self.files = files
        self.parser = parser if parser is not None else ListingParser()

    def run(self, manifest: Path, output: Path) -> dict:
        self.files.require_new(output)
        products = self.read_products(manifest)
        report = {"version": "digikala-compact/1.0", "source_manifest_sha256": self.files.sha256(manifest),
                  "duplicate_policy": "First category/page observation supplies facts; retain every observation."}
        return self.files.write(output, [asdict(products[key]) for key in sorted(products)], report)

    def read_products(self, manifest: Path) -> dict:
        products = {}
        for reference, payload in self.files.replay_pages(manifest):
            listing = self.parser.parse(payload, reference.category_id, reference.page)
            for item in listing.products:
                product = normalize_product(item, listing, reference)
                if product.record_id in products:
                    products[product.record_id].observations.append(reference)
                else:
                    products[product.record_id] = product
        return products
