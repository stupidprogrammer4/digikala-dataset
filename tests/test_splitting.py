"""Family integrity and frozen membership requirements."""

from collections import defaultdict
from copy import deepcopy
import unittest

from tools.splitting import split_membership


def membership():
    candidates = [{"input_hash": f"product-{group}-{member}",
                   "audit_group_id": f"family-{group}", "partition": "candidate_pool"}
                  for group in range(10) for member in range(group + 1)]
    return candidates + [
        {"input_hash": "evaluation", "audit_group_id": "protected", "partition": "evaluation"},
        {"input_hash": "reserved", "audit_group_id": "protected", "partition": "reserved_context"},
    ]


class FamilySplitTests(unittest.TestCase):
    def test_whole_families_and_protected_membership_are_preserved(self):
        source = membership()
        before = deepcopy(source)
        result = split_membership(source)
        partitions = {item["input_hash"]: item["partition"] for item in result}
        self.assertEqual(set(partitions), {item["input_hash"] for item in source})
        self.assertEqual(partitions["evaluation"], "evaluation")
        self.assertEqual(partitions["reserved"], "reserved_context")
        family_splits = defaultdict(set)
        for item in result:
            if item["partition"] in ("train", "validation"):
                family_splits[item["audit_group_id"]].add(item["partition"])
        self.assertTrue(all(len(splits) == 1 for splits in family_splits.values()))
        self.assertEqual(set.union(*family_splits.values()), {"train", "validation"})
        self.assertEqual(source, before)

    def test_input_order_does_not_change_the_split(self):
        source = membership()
        self.assertEqual(split_membership(source), split_membership(list(reversed(source))))

    def test_candidate_family_cannot_cross_a_protected_partition(self):
        source = membership()
        source[0]["audit_group_id"] = "protected"
        with self.assertRaisesRegex(ValueError, "Candidate family overlaps"):
            split_membership(source)


if __name__ == "__main__":
    unittest.main()
