import json
import unittest

from pathlib import Path

from notices.services.party_name_extractor import (
    extract_party_candidates
)


class TransactionPartyExtractorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        data = json.loads(
            Path(
                "test_files/party_extraction_audit/results.json"
            ).read_text(encoding="utf-8")
        )

        cls.results = {

            (
                record["page_number"],
                record["region_number"]
            ): extract_party_candidates(
                record["raw_text"]
            )

            for record in data["results"]
        }

    def keys(self, result):

        return {
            (item["name"], item["role"])
            for item in result["party_candidates"]
        }

    def assert_candidate(self, page, region, name, role):

        self.assertIn(
            (name, role),
            self.keys(
                self.results[(page, region)]
            )
        )

    def test_01_real_owner_with_relationship(self):

        self.assert_candidate(
            7, 4,
            "Bavadeep Reddy",
            "OWNER"
        )

    def test_02_real_kannada_owner(self):

        self.assert_candidate(
            10, 1,
            "ಅರ್. ಶೋಭಾರಾಣಿ ಆರ್.",
            "OWNER"
        )

    def test_03_real_attorney(self):

        self.assert_candidate(
            10, 3,
            "ANIL SHARMA",
            "ATTORNEY"
        )

    def test_04_real_vendor(self):

        self.assert_candidate(
            10, 4,
            "Santhosh Kumar K.V.",
            "VENDOR"
        )

    def test_05_real_first_joint_owner(self):

        self.assert_candidate(
            10, 7,
            "ABDUL AJEED KHAN",
            "OWNER"
        )

    def test_06_real_second_joint_owner(self):

        self.assert_candidate(
            10, 7,
            "ABDUL MALIK KHAN",
            "OWNER"
        )

    def test_07_real_third_joint_owner(self):

        self.assert_candidate(
            10, 7,
            "ABDUL RAZAQ KHAN",
            "OWNER"
        )

    def test_08_real_fourth_joint_owner(self):

        self.assert_candidate(
            10, 7,
            "ABDUL KHALIO KHAN",
            "OWNER"
        )

    def test_09_real_fifth_joint_owner(self):

        self.assert_candidate(
            10, 7,
            "JAMEELA MATHEEN KHAN",
            "OWNER"
        )

    def test_10_real_first_owner_seller(self):

        for role in ("OWNER", "SELLER"):

            self.assert_candidate(
                10, 9,
                "Sudhi Tandon",
                role
            )

    def test_11_real_second_owner_seller(self):

        for role in ("OWNER", "SELLER"):

            self.assert_candidate(
                10, 9,
                "Raj Kumar Tandon",
                role
            )

    def test_12_real_intending_buyer(self):

        self.assert_candidate(
            10, 9,
            "Balasubramanya Hanagal Manjunath",
            "INTENDING_BUYER"
        )

    def test_13_real_owner_without_honorific_space(self):

        self.assert_candidate(
            11, 1,
            "SHWETA NADIG",
            "OWNER"
        )

    def test_14_father_not_owner(self):

        candidates = self.keys(
            self.results[(7, 4)]
        )

        self.assertFalse(
            any(
                "byya reddy" in name.casefold()
                and role == "OWNER"

                for name, role in candidates
            )
        )

    def test_15_father_not_attorney(self):

        candidates = self.keys(
            self.results[(10, 3)]
        )

        self.assertFalse(
            any(
                "sukh dev sharma" in name.casefold()
                and role == "ATTORNEY"

                for name, role in candidates
            )
        )

    def test_16_father_not_vendor(self):

        candidates = self.keys(
            self.results[(10, 4)]
        )

        self.assertFalse(
            any(
                "venkatesh" in name.casefold()
                and role == "VENDOR"

                for name, role in candidates
            )
        )

    def test_17_relative_not_seller(self):

        candidates = self.keys(
            self.results[(10, 9)]
        )

        self.assertFalse(
            any(
                "srinath tandon" in name.casefold()
                and role in ("OWNER", "SELLER")

                for name, role in candidates
            )
        )

    def test_18_husband_not_automatically_owner(self):

        candidates = self.keys(
            self.results[(11, 1)]
        )

        self.assertFalse(
            any(
                "chetan" in name.casefold()
                and role == "OWNER"

                for name, role in candidates
            )
        )

    def test_19_buyer_not_automatically_owner(self):

        candidates = self.keys(
            self.results[(10, 9)]
        )

        self.assertNotIn(
            (
                "Balasubramanya Hanagal Manjunath",
                "OWNER"
            ),
            candidates
        )

    def test_20_multiple_owner_evidence(self):

        owners = [

            item

            for item in self.results[
                (10, 7)
            ]["party_candidates"]

            if item["role"] == "OWNER"
        ]

        self.assertEqual(len(owners), 5)

        for item in owners:

            self.assertIn(
                "owners",
                item["source_text"].casefold()
            )

            self.assertIn(
                item["name"],
                item["source_text"]
            )

    def test_21_synthetic_multiple_owners(self):

        result = extract_party_candidates(
            "Purchased from its owners "
            "Mr. Ramesh Kumar, "
            "Mrs. Sunitha Rao and "
            "Mr. Ravi Sharma, residing at Bengaluru."
        )

        candidates = self.keys(result)

        for name in (
            "Ramesh Kumar",
            "Sunitha Rao",
            "Ravi Sharma"
        ):

            self.assertIn(
                (name, "OWNER"),
                candidates
            )

    def test_22_numbered_section_boundary(self):

        result = extract_party_candidates(
            "OWNERS / SELLERS:\n"
            "1.Mr. Ramesh Kumar, S/o Ravi Kumar\n"
            "INTENDING BUYER:\n"
            "1.Mr. Suresh Rao, residing at Bengaluru"
        )

        candidates = self.keys(result)

        self.assertIn(
            ("Ramesh Kumar", "OWNER"),
            candidates
        )

        self.assertNotIn(
            ("Suresh Rao", "OWNER"),
            candidates
        )

        self.assertNotIn(
            ("Suresh Rao", "SELLER"),
            candidates
        )

    def test_23_all_previous_candidates_preserved(self):

        data = json.loads(
            Path(
                "test_files/transaction_party_extraction/results.json"
            ).read_text(encoding="utf-8")
        )

        for record in data["results"]:

            key = (
                record["page_number"],
                record["region_number"]
            )

            previous = self.keys(
                record["updated"]
            )

            current = self.keys(
                self.results[key]
            )

            self.assertTrue(
                previous.issubset(current),
                f"Previous candidates lost in {key}: "
                f"{previous - current}"
            )

            court_regions = {
                (7, 1),
                (10, 5),
                (10, 12),
                (10, 13),
                (10, 15),
                (11, 4),
                (11, 5)
            }

            allowed_court_roles = {
                "PLAINTIFF",
                "DEFENDANT",
                "PETITIONER",
                "RESPONDENT",
                "APPELLANT",
                "ADVOCATE",
                "FIRM_REPRESENTATIVE"
            }

            added = current - previous

            if key not in court_regions:

                self.assertFalse(
                    added,
                    f"Unexpected non-court additions "
                    f"in {key}: {added}"
                )

            else:

                unexpected = {
                    (name, role)
                    for name, role in added
                    if role not in allowed_court_roles
                }

                self.assertFalse(
                    unexpected,
                    f"Unexpected court roles "
                    f"in {key}: {unexpected}"
                )

    def test_24_no_duplicate_candidates(self):

        from notices.services.party_variant_grouper import (
            extract_party_entry_numbers
        )

        for result in self.results.values():

            keys = []

            for item in result["party_candidates"]:

                entries = tuple(sorted(
                    item.get("court_entry_numbers", [])
                ))

                expected_entries = tuple(sorted(
                    extract_party_entry_numbers(item)
                ))

                self.assertEqual(
                    entries,
                    expected_entries
                )

                keys.append((
                    item["name"].casefold(),
                    item["role"],
                    item["language"],
                    entries
                ))

            self.assertEqual(
                len(keys),
                len(set(keys))
            )


    def test_25_manual_review_safety(self):

        for result in self.results.values():

            self.assertTrue(result["requires_review"])
            self.assertFalse(result["verified"])
            self.assertFalse(result["approved_for_search"])
            self.assertFalse(result["eligible_for_alert"])

            for item in result["party_candidates"]:

                self.assertTrue(item["requires_review"])
                self.assertFalse(item["verified"])
                self.assertTrue(item["source_text"])
                self.assertTrue(item["evidence"])


if __name__ == "__main__":
    unittest.main()
