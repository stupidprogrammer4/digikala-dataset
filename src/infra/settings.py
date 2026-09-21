"""Read runtime configuration using the standard library."""

from pathlib import Path
import tomllib

from schemas.config import AnnotationSettings, CrawlSettings, HubSettings, Settings


class SettingsLoader:
    def load(self, path: Path) -> Settings:
        with path.open("rb") as stream:
            values = tomllib.load(stream)
        return Settings(CrawlSettings(**values["crawl"]),
                        AnnotationSettings(**values.get("annotation", {})),
                        HubSettings(**values["hub"]))
