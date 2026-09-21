"""Direct calls to the optional LiteLLM SDK."""

import os

from schemas.config import AnnotationSettings
from tools.serialization import json_bytes


class ModelClient:
    def __init__(self, settings: AnnotationSettings):
        self.settings = settings

    def check_configuration(self) -> None:
        if not self.settings.model or not os.environ.get(self.settings.api_key_env):
            raise ValueError("Configure a model and its API-key environment variable")

    async def complete(self, prompt: str, item: dict) -> dict:
        from litellm import acompletion

        options = {}
        if self.settings.api_base:
            options["api_base"] = self.settings.api_base
        if self.settings.json_mode:
            options["response_format"] = {"type": "json_object"}
        response = await acompletion(
            model=self.settings.model, api_key=os.environ[self.settings.api_key_env],
            messages=[{"role": "system", "content": prompt},
                      {"role": "user", "content": json_bytes(item).decode()}],
            timeout=self.settings.timeout_seconds, max_tokens=self.settings.max_tokens,
            num_retries=0, **options)
        return response.model_dump(mode="json")
