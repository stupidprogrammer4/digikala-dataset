"""Release snapshot-only reservations without modifying the frozen dataset."""

from collections import Counter
import re
import unicodedata
from urllib.parse import urlsplit

import networkx as nx


VERSION = "snapshot-reservation-pool/1.0"


def normalized(title: str) -> str:
    title = unicodedata.normalize("NFKC", title).casefold()
    title = title.translate(str.maketrans({"\u064a": "\u06cc", "\u0643": "\u06a9", "\u200c": " "}))
    title = "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in title)
    return " ".join(re.findall(r"\w+", title))


def snapshots(row: dict) -> set[tuple[str, str]]:
    """Retain the original snapshot rule for auditing, not family grouping."""
    result = {("snapshot", row["product"]["source"]["snapshot_id"])}
    for sample in row.get("samples", []):
        for field in ("collection_snapshot_id", "content_hash"):
            if sample.get(field):
                result.add((field, sample[field]))
    return result


def audit(rows: list[dict]) -> tuple[list[dict], dict]:
    by_key = {row["input_hash"]: row for row in rows}
    if len(by_key) != len(rows):
        raise ValueError("Duplicate input hashes in source dataset")
    evaluation = {key for key, row in by_key.items()
                  if row["release_partition"]["split"] == "evaluation"}
    eval_families = {by_key[key]["release_partition"]["family_id"] for key in evaluation}
    eval_snapshots = set().union(*(snapshots(by_key[key]) for key in evaluation))
    graph = nx.Graph()
    graph.add_nodes_from(by_key)
    owners = {}
    links = Counter()
    for key, row in sorted(by_key.items()):
        product = row["product"]
        source = product["source"]
        market = source["marketplace"]
        title = normalized(product["identity"]["title"])
        signatures = [("family", row["release_partition"]["family_id"]),
                      ("product_identity", market, source["external_product_id"])]
        if title:
            signatures += [("exact_title", market, title),
                           ("numeric_variant_title", market, re.sub(r"\d+", "#", title))]
        for image in product.get("images", []):
            url = urlsplit(image)
            if url.netloc and url.path:
                signatures.append(("shared_image", market, url.netloc + url.path))
        for signature in signatures:
            if signature in owners:
                graph.add_edge(key, owners[signature])
                links[signature[0]] += 1
            else:
                owners[signature] = key

    group_by_key = {}
    connected_to_eval = set()
    for component in nx.connected_components(graph):
        group = min(component)
        group_by_key.update(dict.fromkeys(component, group))
        if component & evaluation:
            connected_to_eval.update(component)

    membership = []
    for key, row in sorted(by_key.items()):
        previous = row["release_partition"]
        family_reserved = previous["family_id"] in eval_families
        snapshot_reserved = bool(snapshots(row) & eval_snapshots)
        old_reasons = []
        if key not in evaluation:
            if family_reserved:
                old_reasons.append("evaluation_family")
            if snapshot_reserved:
                old_reasons.append("evaluation_listing_snapshot")
            expected = "reserved_context" if old_reasons else "train_candidates"
            if previous["split"] != expected:
                raise ValueError(f"Reservation history disagrees for {key}")
        if key in evaluation:
            disposition, reason = "evaluation", "frozen_evaluation"
        elif key in connected_to_eval:
            disposition = "reserved_context"
            reason = "evaluation_family" if family_reserved else "additional_evaluation_link"
        else:
            disposition = "candidate_pool"
            reason = "snapshot_only_released" if old_reasons else "existing_candidate"
        membership.append({"input_hash": key,
                           "product_id": row["product"]["source"]["external_product_id"],
                           "source_split": previous["split"],
                           "source_reservation_reasons": old_reasons,
                           "audit_group_id": group_by_key[key],
                           "partition": disposition, "decision": reason})

    return membership, {
        "counts": dict(Counter(item["partition"] for item in membership)),
        "decisions": dict(Counter(item["decision"] for item in membership)),
        "source_reservation_reasons": dict(Counter(
            "+".join(item["source_reservation_reasons"]) for item in membership
            if item["source_split"] == "reserved_context")),
        "connected_components": nx.number_connected_components(graph),
        "matching_signatures": dict(sorted(links.items())),
    }
