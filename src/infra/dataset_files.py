"""Dataset files, raw-page replay and completed output artifacts."""

import json
from pathlib import Path

from schemas.product import PageReference
from infra.files import FileStore
from tools.serialization import digest, json_bytes


class DatasetFiles:
    def __init__(self, files: FileStore | None = None):
        self.files = files if files is not None else FileStore()

    def read(self, path: Path) -> list[dict]:
        return self.files.read_jsonl(path)

    def metadata(self, path: Path) -> dict:
        return self.files.read_json(path)

    def sha256(self, path: Path) -> str:
        return digest(path.read_bytes())

    def replay_pages(self, manifest: Path):
        for page in sorted(self.metadata(manifest)["pages"], key=lambda page: (page["category_id"], page["page"])):
            reference = PageReference(**page)
            raw = Path(reference.file).read_bytes()
            if digest(raw) != reference.sha256:
                raise ValueError("Raw page changed since collection")
            yield reference, json.loads(raw)

    def require_new(self, output: Path) -> None:
        if output.exists() or output.with_suffix(".manifest.json").exists():
            raise FileExistsError("Choose a new dataset output file")

    def write(self, output: Path, rows: list[dict], report: dict) -> dict:
        self.require_new(output)
        raw = b"".join(json_bytes(row) for row in rows)
        report = {**report, "products": len(rows), "sha256": digest(raw)}
        self.files.write_bytes(output, raw)
        self.files.write_bytes(output.with_suffix(".manifest.json"), json_bytes(report))
        return report
