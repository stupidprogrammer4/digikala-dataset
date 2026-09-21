"""Create a family split using pure grouping tools and release storage."""

from collections import Counter
from importlib.metadata import version
from pathlib import Path

from infra.releases import ReleaseStore
from tools.splitting import SEED, VALIDATION_FRACTION, check_membership, split_membership


class SplitService:
    def __init__(self, store: ReleaseStore):
        self.store = store

    def run(self, pool_dir=Path("artifacts/releases/v2.1-pool-v1"),
            output=Path("artifacts/releases/v2.1-family-split-v1"),
            exports=Path("artifacts/splits/v2.1-family-split-v1")) -> dict:
        if output.exists() or exports.exists():
            raise FileExistsError("Refusing to overwrite existing split artifacts")
        release = self.store.load()
        pool, pool_report = self.store.read_pool(pool_dir)
        if pool_report["source_sha256"] != release.metadata["full_export_sha256"]:
            raise ValueError("Pool belongs to a different frozen source")
        assignments = split_membership(pool)
        keys, checks = check_membership(assignments, pool, release.rows)
        report = self.report(assignments, keys, release, pool_report, checks)
        report["exports"] = self.store.export_splits(exports, release, keys)
        report["export_directory"] = str(exports)
        return self.store.save(output, assignments, report)

    def report(self, assignments, keys, release, pool_report, checks) -> dict:
        rows = {row["input_hash"]: row for row in release.rows}
        return {
            "version": "family-split/1.0", "seed": SEED,
            "validation_family_fraction_target": VALIDATION_FRACTION,
            "validation_product_fraction_actual": len(keys["validation"]) / (len(keys["train"]) + len(keys["validation"])),
            "method": "datasets.Dataset.train_test_split on sorted unique audit_group_id values",
            "datasets_version": version("datasets"), "numpy_version": version("numpy"),
            "source_sha256": release.metadata["full_export_sha256"], "source_revision": release.metadata["revision"],
            "pool_membership_sha256": pool_report["membership_sha256"],
            "counts": {name: len(selected) for name, selected in keys.items()},
            "family_counts": {name: len({item["audit_group_id"] for item in assignments
                                         if item["partition"] == name}) for name in keys},
            "taxonomy_counts": {name: dict(sorted(Counter(
                (rows[key]["label"]["taxonomy"] or {}).get("category") or "unknown" for key in selected).items()))
                for name, selected in keys.items()},
            "detected_overlap_counts": checks,
            "limitations": ["Random family split, not category stratification; rare categories may be absent.",
                            "Only detected families are protected; source release_partition remains historical."],
        }
