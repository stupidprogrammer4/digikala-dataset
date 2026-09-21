"""Create a source-only evidence view for model requests."""

from dataclasses import asdict
from schemas.product import Attribute, Evidence


def source_input(row: dict) -> dict:
    if "source_record" in row:
        return source_input(row["source_record"])
    if "product" in row:
        product = row["product"]
        evidence = Evidence(
            title=product["identity"]["title"],
            category_title=product["identity"].get("source_category_title"),
            description=product["text"].get("description"),
            alternate_titles=product["text"].get("searchable_fragments", []),
            attributes=[Attribute(a["name_raw"], a["values_raw"]) for a in product["explicit_attributes"]],
            brand=product["identity"].get("brand_raw"))
        return {"record_id": row["input_hash"], "source": asdict(evidence)}
    source = row["source"]
    evidence = Evidence(title=source["title"], category_title=source.get("category_title"),
                        description=source.get("description"), alternate_titles=source.get("alternate_titles", []),
                        attributes=[Attribute(a["name"], a["values"]) for a in source.get("attributes", [])],
                        brand=source.get("brand"))
    return {"record_id": row["record_id"], "source": asdict(evidence)}
