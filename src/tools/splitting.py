"""Split the audited pool by family while preserving the frozen evaluation."""

from itertools import combinations

from datasets import Dataset


SEED = 42
VALIDATION_FRACTION = 0.2


def split_membership(membership: list[dict]) -> list[dict]:
    candidates = [item for item in membership if item["partition"] == "candidate_pool"]
    families = sorted({item["audit_group_id"] for item in candidates})
    protected = {item["audit_group_id"] for item in membership
                 if item["partition"] != "candidate_pool"}
    if set(families) & protected:
        raise ValueError("Candidate family overlaps a protected partition")
    split = Dataset.from_dict({"family": families}).train_test_split(
        test_size=VALIDATION_FRACTION, seed=SEED
    )
    validation = set(split["test"]["family"])
    result = []
    for item in sorted(membership, key=lambda item: item["input_hash"]):
        partition = item["partition"]
        if partition == "candidate_pool":
            partition = "validation" if item["audit_group_id"] in validation else "train"
        result.append({"input_hash": item["input_hash"],
                       "audit_group_id": item["audit_group_id"], "partition": partition})
    return result


def check_membership(assignments: list[dict], pool: list[dict], rows: list[dict]) -> tuple[dict, dict]:
    by_key = {row["input_hash"]: row for row in rows}
    keys = {name: {item["input_hash"] for item in assignments if item["partition"] == name}
            for name in ("train", "validation", "evaluation", "reserved_context")}
    if len(assignments) != len(by_key) or set.union(*keys.values()) != set(by_key):
        raise ValueError("Split membership does not cover the source exactly once")
    for name in ("evaluation", "reserved_context"):
        if keys[name] != {item["input_hash"] for item in pool if item["partition"] == name}:
            raise ValueError("Protected membership changed")
    overlap_checks = {}
    components = {item["input_hash"]: item["audit_group_id"] for item in assignments}
    identities = {
        "input_hash": lambda key: key,
        "source_family": lambda key: by_key[key]["release_partition"]["family_id"],
        "product_identity": lambda key: (by_key[key]["product"]["source"]["marketplace"],
                                         by_key[key]["product"]["source"]["external_product_id"]),
        "audit_group": lambda key: components[key],
    }
    for left, right in combinations(("train", "validation", "evaluation"), 2):
        for name, identity in identities.items():
            overlap = {identity(key) for key in keys[left]} & {identity(key) for key in keys[right]}
            if overlap:
                raise ValueError(f"{name} leakage between {left} and {right}")
            overlap_checks[f"{left}/{right}/{name}"] = 0
    return keys, overlap_checks
