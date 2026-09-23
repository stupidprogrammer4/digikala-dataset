"""Validate model JSON against the declarative JSON Schema contract."""

from importlib.resources import files
import json

from jsonschema import Draft202012Validator


class AnnotationContract:
    def __init__(self):
        schema = json.loads(files("infra").joinpath("contracts/gold-semantic.json").read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema)

    def parse(self, content: str, item: dict) -> dict:
        response = json.loads(content, parse_constant=self.reject_nonfinite)
        if set(response) != {"record_id", "label"} or response["record_id"] != item["record_id"]:
            raise ValueError("Response identity or envelope mismatch")
        label = response["label"]
        if set(label) != {"schema_version", "taxonomy", "features", "abstentions", "vocabulary_gaps", "quality_flags"}:
            raise ValueError("Response must include exactly the agreed label fields")
        self.validator.validate(label)
        self.check_abstentions(label)
        self.check_quotes(label, item["source"])
        return response

    @staticmethod
    def reject_nonfinite(value: str) -> None:
        raise ValueError(f"Invalid JSON number: {value}")

    def check_abstentions(self, label: dict) -> None:
        if set(label["features"]) != {"audience", "styles", "motifs", "use_cases", "design_details"}:
            raise ValueError("Response must include all feature groups")
        empty = {name for name, values in label["features"].items() if not values}
        if label["taxonomy"] is None:
            empty.add("taxonomy")
        if set(label["abstentions"]) != empty:
            raise ValueError("Abstentions do not match empty fields")
        for field, abstention in label["abstentions"].items():
            if abstention["reason"] == "out_of_vocabulary" and not any(
                    gap["field"] == field for gap in label["vocabulary_gaps"]):
                raise ValueError("An out-of-vocabulary abstention requires a vocabulary gap")

    def check_quotes(self, label: dict, source: dict) -> None:
        texts = [source["title"], source.get("description"), *source.get("alternate_titles", [])]
        texts += [v for attr in source.get("attributes", []) for v in attr["values"]]
        texts = [text for text in texts if text]
        claims = [(field, claim) for field, values in label["features"].items() for claim in values]
        claims += list(label["abstentions"].items())
        claims += [(gap["field"], gap) for gap in label["vocabulary_gaps"]]
        if label["taxonomy"]:
            claims.append(("taxonomy", label["taxonomy"]))
        for field, claim in claims:
            allowed = texts + ([source["category_title"]] if field == "taxonomy" and source.get("category_title") else [])
            if any(not any(quote in text for text in allowed) for quote in claim.get("evidence", [])):
                raise ValueError("Response contains evidence absent from allowed source fields")
