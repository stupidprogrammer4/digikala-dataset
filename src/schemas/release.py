"""Loaded frozen release data, independent of storage implementation."""

from dataclasses import dataclass


@dataclass
class FrozenRelease:
    metadata: dict
    raw: bytes
    evaluation_raw: bytes
    rows: list[dict]
    source_file: str
