"""Reservation policy cases with synthetic product identities."""

from copy import deepcopy
import unittest

from tools.reservations import audit


def row(key, split="reserved_context", family=None, snapshot="page-a", title=None, images=None):
    return {
        "input_hash": key,
        "release_partition": {"split": split, "family_id": family or key},
        "product": {
            "source": {"marketplace": "synthetic", "external_product_id": key,
                       "snapshot_id": snapshot},
            "identity": {"title": title or key},
            "images": images or [],
        },
        "samples": [],
    }


class ReservationPolicyTests(unittest.TestCase):
    def test_shared_page_is_released_but_evaluation_family_is_not(self):
        rows = [row("evaluation", split="evaluation", family="protected"),
                row("snapshot-only"), row("family", family="protected"),
                row("candidate", split="train_candidates", snapshot="page-b")]
        original = deepcopy(rows)
        membership, _ = audit(rows)
        decisions = {item["input_hash"]: item["decision"] for item in membership}
        self.assertEqual(decisions, {"evaluation": "frozen_evaluation",
                                    "snapshot-only": "snapshot_only_released",
                                    "family": "evaluation_family",
                                    "candidate": "existing_candidate"})
        self.assertEqual(rows, original)

    def test_transitive_image_and_family_link_stays_reserved(self):
        rows = [row("evaluation", split="evaluation", images=["https://example.org/image.jpg?size=1"]),
                row("bridge", family="linked", images=["https://example.org/image.jpg?size=2"]),
                row("indirect", family="linked")]
        membership, report = audit(rows)
        self.assertEqual(report["counts"], {"reserved_context": 2, "evaluation": 1})
        self.assertEqual(len({item["audit_group_id"] for item in membership}), 1)

    def test_numeric_title_variants_remain_together(self):
        membership, _ = audit([row("evaluation", split="evaluation", title="Pendant model 123"),
                               row("variant", title="Pendant model 456")])
        self.assertEqual(membership[1]["decision"], "additional_evaluation_link")

    def test_identity_link_also_checks_previous_candidates(self):
        candidate = row("candidate", split="train_candidates", snapshot="page-b")
        candidate["product"]["source"]["external_product_id"] = "evaluation"
        membership, _ = audit([row("evaluation", split="evaluation"), candidate])
        self.assertEqual(membership[0]["decision"], "additional_evaluation_link")

    def test_inconsistent_reservation_history_fails(self):
        with self.assertRaisesRegex(ValueError, "Reservation history disagrees"):
            audit([row("evaluation", split="evaluation"),
                   row("incorrect", split="train_candidates")])

    def test_duplicate_input_hash_fails(self):
        with self.assertRaisesRegex(ValueError, "Duplicate input hashes"):
            audit([row("same", split="evaluation"), row("same")])


if __name__ == "__main__":
    unittest.main()
