"""Audit the pool against a verified frozen release."""

from pathlib import Path
import networkx

from tools.serialization import digest
from infra.releases import ReleaseStore
from tools.reservations import VERSION, audit


class ReservationService:
    def __init__(self, store: ReleaseStore):
        self.store = store

    def run(self, output=Path("artifacts/releases/v2.1-pool-v1")) -> dict:
        if output.exists():
            raise FileExistsError("Refusing to overwrite an existing pool")
        release = self.store.load()
        membership, report = audit(release.rows)
        report.update(self.provenance(release))
        return self.store.save(output, membership, report)

    def provenance(self, release) -> dict:
        return {
            "version": VERSION, "source_revision": release.metadata["revision"],
            "source_sha256": release.metadata["full_export_sha256"],
            "evaluation_sha256": digest(release.evaluation_raw),
            "networkx_version": networkx.__version__, "membership_file": "membership.jsonl",
            "source_file": release.source_file,
            "usage": "Join candidate_pool membership to frozen records by input_hash; release_partition is historical.",
            "limitations": ["Detected families are heuristic; no new visual or fuzzy-title search.",
                            "Snapshot overlap is allowed; evaluation-family overlap is not."],
        }
