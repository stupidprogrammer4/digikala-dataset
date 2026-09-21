"""Per-run annotation checkpoints and raw provider responses."""

from dataclasses import asdict
from pathlib import Path

from infra.files import FileStore
from tools.serialization import digest, json_bytes


class AnnotationStore:
    def __init__(self, root: Path, files: FileStore | None = None):
        self.root = root
        self.files = files if files is not None else FileStore()

    def start(self, source: Path, task: str, prompt_hash: str, settings) -> list[dict]:
        run = {"version": "api-annotation/1.0", "task": task,
               "input_sha256": digest(source.read_bytes()), "prompt_sha256": prompt_hash,
               "settings": asdict(settings)}
        path = self.root / "run.json"
        if path.exists() and self.files.read_json(path) != run:
            raise ValueError("Inputs, model or prompt changed; choose a new run directory")
        self.files.write_bytes(path, json_bytes(run))
        return self.files.read_jsonl(source)

    def load_success(self, key: str) -> dict | None:
        path = self.root / "records" / f"{key}.json"
        if path.exists():
            result = self.files.read_json(path)
            if result["status"] == "success":
                return result
        return None

    def save_response(self, key: str, response: dict) -> None:
        self.files.write_bytes(self.root / "responses" / f"{key}.json", json_bytes(response))

    def save_result(self, key: str, result: dict) -> None:
        self.files.write_bytes(self.root / "records" / f"{key}.json", json_bytes(result))

    def finish(self, results: list[dict]) -> dict:
        self.files.write_bytes(self.root / "results.jsonl", b"".join(json_bytes(result) for result in results))
        summary = {"products": len(results), "succeeded": sum(r["status"] == "success" for r in results),
                   "failed": sum(r["status"] == "failed" for r in results)}
        self.files.write_bytes(self.root / "summary.json", json_bytes(summary))
        return summary
