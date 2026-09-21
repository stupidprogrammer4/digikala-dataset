"""Small application settings; no provider configuration framework."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlSettings:
    endpoint: str
    category_ids: list[int]
    output: str
    pages_per_category: int = 50
    concurrency: int = 2
    delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    user_agent: str = "digikala-dataset/0.1"


@dataclass(frozen=True)
class AnnotationSettings:
    model: str = ""
    api_key_env: str = "LLM_API_KEY"
    api_base: str = ""
    concurrency: int = 2
    timeout_seconds: float = 60.0
    max_tokens: int = 2048
    json_mode: bool = False


@dataclass(frozen=True)
class HubSettings:
    repo_id: str
    revision: str
    local_dir: str


@dataclass(frozen=True)
class Settings:
    crawl: CrawlSettings
    annotation: AnnotationSettings
    hub: HubSettings
