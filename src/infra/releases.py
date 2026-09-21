"""Read frozen release inputs and write new membership artifacts."""

import json
from pathlib import Path
import tomllib

from infra.files import FileStore
from tools.serialization import digest, json_bytes
from schemas.release import FrozenRelease


class ReleaseStore:
    def __init__(self, freeze_file=Path("releases/v2.1.freeze.toml"), files: FileStore | None = None):
        self.freeze_file = freeze_file
        self.files = files if files is not None else FileStore()

    def load(self) -> FrozenRelease:
        with self.freeze_file.open("rb") as stream:
            metadata = tomllib.load(stream)
        source = Path(metadata["local_snapshot"]) / "auryx-radar-gold-v2.1.jsonl"
        raw = source.read_bytes()
        evaluation = (Path(metadata["local_snapshot"]) / "hub/data/evaluation.jsonl").read_bytes()
        if digest(raw) != metadata["full_export_sha256"]:
            raise ValueError("Frozen dataset hash mismatch")
        if digest(evaluation) != metadata["files"]["data/evaluation.jsonl"]["sha256"]:
            raise ValueError("Frozen evaluation hash mismatch")
        rows = [json.loads(line) for line in raw.splitlines()]
        expected = {row["input_hash"]: row for row in map(json.loads, evaluation.splitlines())}
        if expected != {r["input_hash"]: r for r in rows if r["release_partition"]["split"] == "evaluation"}:
            raise ValueError("Evaluation records disagree with the frozen export")
        return FrozenRelease(metadata, raw, evaluation, rows, str(source))

    def read_pool(self, folder: Path) -> tuple[list[dict], dict]:
        report = self.files.read_json(folder / "manifest.json")
        raw = (folder / "membership.jsonl").read_bytes()
        if digest(raw) != report["membership_sha256"]:
            raise ValueError("Pool membership hash mismatch")
        return [json.loads(line) for line in raw.splitlines()], report

    def save(self, folder: Path, membership: list[dict], report: dict) -> dict:
        folder.mkdir(parents=True, exist_ok=False)
        raw = b"".join(json_bytes(item) for item in membership)
        report = {**report, "membership_sha256": digest(raw)}
        self.files.write_bytes(folder / "membership.jsonl", raw)
        self.files.write_bytes(folder / "manifest.json", json_bytes(report))
        return report

    def export_splits(self, folder: Path, release: FrozenRelease, keys: dict) -> dict:
        folder.mkdir(parents=True, exist_ok=False)
        lines = [(json.loads(line)["input_hash"], line) for line in release.raw.splitlines(keepends=True)]
        exports = {name: b"".join(line for key, line in lines if key in keys[name]) for name in ("train", "validation")}
        exports["evaluation"] = release.evaluation_raw
        for name, raw in exports.items():
            self.files.write_bytes(folder / f"{name}.jsonl", raw)
        return {f"{name}.jsonl": {"sha256": digest(raw), "bytes": len(raw)} for name, raw in exports.items()}
