"""Annotate a source-only batch with a fixed model and prompt."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

from infra.annotation_contract import AnnotationContract
from infra.annotation_store import AnnotationStore
from tools.serialization import digest, json_bytes
from infra.model_client import ModelClient
from infra.prompts import PromptStore
from tools.evidence import source_input


class AnnotationService:
    def __init__(self, client: ModelClient, store: AnnotationStore,
                 contract: AnnotationContract, prompts: PromptStore):
        self.client, self.store, self.contract, self.prompts = client, store, contract, prompts

    async def run(self, source: Path, task: str) -> dict:
        self.client.check_configuration()
        if self.client.settings.concurrency < 1:
            raise ValueError("Annotation concurrency must be positive")
        self.prompt, self.prompt_hash = self.prompts.load(task)
        self.task = task
        rows = self.store.start(source, task, self.prompt_hash, self.client.settings)
        items = [source_input(row) for row in rows]
        if len({item["record_id"] for item in items}) != len(items):
            raise ValueError("Annotation input contains duplicate record IDs")
        self.slots = asyncio.Semaphore(self.client.settings.concurrency)
        results = await asyncio.gather(*(self.annotate_product(item) for item in items))
        return self.store.finish(results)

    async def annotate_product(self, item: dict) -> dict:
        key = digest(json_bytes(item))
        cached = self.store.load_success(key)
        if cached is not None:
            self.contract.parse(json.dumps(cached["annotation"]), item)
            return cached
        async with self.slots:
            result = self.new_result(item, key)
            try:
                response = await self.client.complete(self.prompt, item)
                self.store.save_response(key, response)
                choice = response["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise ValueError("Model response did not finish normally")
                result["annotation"] = self.contract.parse(choice["message"]["content"], item)
                result.update(status="success", returned_model=response.get("model"), usage=response.get("usage"))
            except Exception as error:
                # Provider error strings may contain credentials.
                result.update(status="failed", error_type=type(error).__name__)
            self.store.save_result(key, result)
            return result

    def new_result(self, item: dict, key: str) -> dict:
        return {"record_id": item["record_id"], "input_sha256": key,
                "prompt_sha256": self.prompt_hash, "task": self.task, "human_review": None,
                "requested_model": self.client.settings.model, "model_version": None,
                "created_at": datetime.now(timezone.utc).isoformat()}
