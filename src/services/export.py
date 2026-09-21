"""Build a new dataset from complete, validated annotation results."""

import json
from pathlib import Path

from infra.annotation_contract import AnnotationContract
from infra.dataset_files import DatasetFiles
from tools.serialization import digest, json_bytes
from tools.evidence import source_input


class ExportService:
    def __init__(self, files: DatasetFiles, contract: AnnotationContract):
        self.files, self.contract = files, contract

    def run(self, source: Path, run_dir: Path, output: Path) -> dict:
        self.files.require_new(output)
        run = self.files.metadata(run_dir / "run.json")
        if run["task"] != "labeling":
            raise ValueError("Review results are separate proposals, not replacement dataset labels")
        if self.files.sha256(source) != run["input_sha256"]:
            raise ValueError("Annotation source changed")
        rows = self.files.read(source)
        results = self.files.read(run_dir / "results.jsonl")
        by_id = self.index_results(rows, results)
        records = [self.build_record(row, by_id[source_input(row)["record_id"]]) for row in rows]
        report = {"version": "api-dataset-export/1.0", "source_sha256": run["input_sha256"],
                  "prompt_sha256": run["prompt_sha256"], "requested_model": run["settings"]["model"]}
        return self.files.write(output, records, report)

    def index_results(self, rows: list[dict], results: list[dict]) -> dict:
        by_id = {result["record_id"]: result for result in results}
        ids = {source_input(row)["record_id"] for row in rows}
        if len(by_id) != len(results) or len(ids) != len(rows) or set(by_id) != ids:
            raise ValueError("Annotation results do not cover the source exactly once")
        return by_id

    def build_record(self, row: dict, result: dict) -> dict:
        item = source_input(row)
        if result["status"] != "success" or result["input_sha256"] != digest(json_bytes(item)):
            raise ValueError("Incomplete or mismatched annotation results")
        annotation = self.contract.parse(json.dumps(result["annotation"]), item)
        return {"record_id": item["record_id"], "source_record": row,
                "label": annotation["label"], "status": "teacher_only", "human_review": None,
                "provenance": {k: v for k, v in result.items() if k != "annotation"}}
