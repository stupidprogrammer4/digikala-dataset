"""Raw page checkpoints and collection manifests."""

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from schemas.product import PageReference
from infra.files import FileStore
from tools.serialization import digest, json_bytes


class CollectionStore:
    def __init__(self, root: Path, files: FileStore | None = None):
        self.root = root
        self.files = files if files is not None else FileStore()

    def start(self, settings) -> None:
        path = self.root / "config.json"
        config = json_bytes(asdict(settings))
        if path.exists() and path.read_bytes() != config:
            raise ValueError("Collection configuration changed; choose a new output directory")
        self.files.write_bytes(path, config)

    def path(self, category: int, page: int) -> Path:
        return self.root / "pages" / str(category) / f"{page}.json"

    def load(self, category: int, page: int) -> bytes | None:
        path = self.path(category, page)
        if not path.exists():
            return None
        raw = path.read_bytes()
        receipt = path.with_suffix(".meta.json")
        if not receipt.exists() or self.files.read_json(receipt)["sha256"] != digest(raw):
            raise ValueError("Cached page is missing its receipt or has changed")
        return raw

    def save(self, category: int, page: int, raw: bytes, url: str) -> None:
        path = self.path(category, page)
        self.files.write_bytes(path.with_suffix(".meta.json"), json_bytes({
            "sha256": digest(raw), "url": url, "fetched_at": datetime.now(timezone.utc).isoformat()}))
        self.files.write_bytes(path, raw)

    def reference(self, category: int, page: int, raw: bytes) -> PageReference:
        return PageReference(category, page, str(self.path(category, page)), digest(raw))

    def finish(self, settings, references: list[PageReference]) -> dict:
        report = {"version": "digikala-collection/1.0", "config": asdict(settings),
                  "pages": [asdict(ref) for ref in sorted(references, key=lambda ref: (ref.category_id, ref.page))]}
        self.files.write_bytes(self.root / "manifest.json", json_bytes(report))
        return report
