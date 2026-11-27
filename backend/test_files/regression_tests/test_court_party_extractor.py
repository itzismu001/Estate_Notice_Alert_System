import json
import unittest

from pathlib import Path

from notices.services.party_name_extractor import (
    extract_party_candidates
)

from notices.services.court_party_extractor import (
    extract_court_party_candidates
)


class CourtPartyExtractorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        data = json.loads(
            Path(
                "test_files/court_party_audit/results.json"
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

    def normalize(self, value):

        return "".join(
            character
            for character in value.casefold()
            if character.isalnum()
        )

    def assert_candidate(self, page, region, name, role):

        candidates = {
            (
                self.normalize(item["name"]),
                item["role"]
            )
            for item in self.results[
                (page, region)
            ]["party_candidates"]
        }

        self.assertIn(
            (self.normalize(name), role),
            candidates
        )

    def test_01_appellant(self):

        self.assert_candidate(
            7, 1, "GAYATHRI", "APPELLANT"
        )

    def test_02_appellant_also_defendant(self):

        self.assert_candidate(
            7, 1, "GAYATHRI", "DEFENDANT"
        )

    def test_03_respondent(self):

        self.assert_candidate(
            7, 1, "GOWRAMMA", "RESPONDENT"
        )

    def test_04_respondent_also_defendant(self):

        self.assert_candidate(
            7, 1, "GOWRAMMA", "DEFENDANT"
        )

    def test_05_numbered_respondent(self):

        self.assert_candidate(
            7, 1, "SARASWATHI", "RESPONDENT"
        )

    def test_06_numbered_respondent_without_space(self):

        self.assert_candidate(
            7, 1, "NIRMALA", "RESPONDENT"
        )

    def test_07_court_appeal_advocate(self):

        self.assert_candidate(
            7, 1,
            "R.A. CHANDRASHEKHAR REDDY",
            "ADVOCATE"
        )

    def test_08_partition_advocate(self):

        self.assert_candidate(
            10, 5,
            "HEMACHANDRA R. RAI",
            "ADVOCATE"
        )

    def test_09_eviction_plaintiff(self):

        self.assert_candidate(
            10, 12, "Prathibha VR", "PLAINTIFF"
        )

    def test_10_eviction_defendant(self):

        self.assert_candidate(
            10, 12, "Gowtham S", "DEFENDANT"
        )

    def test_11_eviction_advocate(self):

        self.assert_candidate(
            10, 12, "Kiran. B", "ADVOCATE"
        )

    def test_12_final_decree_petitioner(self):

        self.assert_candidate(
            10, 13, "Ashwathamma", "PETITIONER"
        )

    def test_13_firm_representative(self):

        self.assert_candidate(
            10, 15,
            "MRUDHULA JOGI",
            "FIRM_REPRESENTATIVE"
        )

    def test_14_firm_advocate(self):

        self.assert_candidate(
            10, 15,
            "T.D. RAMACHANDRA",
            "ADVOCATE"
        )

    def test_15_injunction_plaintiff(self):

        self.assert_candidate(
            11, 4,
            "N.D. SOLOMON RAJU",
            "PLAINTIFF"
        )

    def test_16_addressed_defendant(self):

        self.assert_candidate(
            11, 4,
            "Mahabala K Poojari",
            "DEFENDANT"
        )

    def test_17_injunction_advocate(self):

        self.assert_candidate(
            11, 4,
            "RAMESH BABU .R",
            "ADVOCATE"
        )

    def test_18_partition_plaintiff(self):

        self.assert_candidate(
            11, 5, "Muniyamma", "PLAINTIFF"
        )

    def test_19_partition_defendant(self):

        self.assert_candidate(
            11, 5, "Ramanjinappa", "DEFENDANT"
        )

    def test_20_numbered_defendant_one(self):

        self.assert_candidate(
            11, 5, "G.Pullareddy", "DEFENDANT"
        )

    def test_21_numbered_defendant_two(self):

        self.assert_candidate(
            11, 5, "M.Rajagopal", "DEFENDANT"
        )

    def test_22_numbered_defendant_three(self):

        self.assert_candidate(
            11, 5,
            "A. Ravindra Chowdhary",
            "DEFENDANT"
        )

    def test_23_all_court_notices_covered(self):

        self.assertEqual(len(self.results), 7)

        for key, result in self.results.items():

            self.assertTrue(
                result["party_candidates"],
                f"No candidates in {key}"
            )

    def test_24_non_court_notice_rejected(self):

        text = (
            "PUBLIC NOTICE\n"
            "Our client Mr. Ramesh Kumar "
            "is purchasing Site No. 25.\n"
            "Ravi Sharma, Advocate"
        )

        result = extract_court_party_candidates(text)

        self.assertEqual(result, [])

    def test_25_relative_not_court_party(self):

        result = extract_court_party_candidates(
            "IN THE COURT OF THE CIVIL JUDGE\n"
            "1. SMT. GAYATHRI, W/o Narayanaraju, "
            "aged about 61 years "
            "... DEFENDANT NO.34/APPELLANTNO.1"
        )

        names = {
            self.normalize(item["name"])
            for item in result
        }

        self.assertNotIn(
            "narayanaraju", names
        )

    def test_26_multiple_roles_preserved(self):

        result = extract_court_party_candidates(
            "IN THE COURT OF THE CIVIL JUDGE\n"
            "1. SMT. GAYATHRI, W/o Narayanaraju, "
            "... DEFENDANT NO.34/APPELLANTNO.1"
        )

        roles = {
            item["role"]
            for item in result
            if item["name"] == "GAYATHRI"
        }

        self.assertEqual(
            roles,
            {"DEFENDANT", "APPELLANT"}
        )

    def test_27_numbered_entry_role_boundary(self):

        result = extract_court_party_candidates(
            "IN THE COURT OF THE CIVIL JUDGE\n"
            "1. Sri. Ramesh Kumar, S/o Ravi Kumar, "
            "DEFENDANT NO.1\n"
            "2. Sri. Suresh Rao, S/o Mohan Rao, "
            "RESPONDENT NO.2"
        )

        candidates = {
            (item["name"], item["role"])
            for item in result
        }

        self.assertIn(
            ("Ramesh Kumar", "DEFENDANT"),
            candidates
        )

        self.assertIn(
            ("Suresh Rao", "RESPONDENT"),
            candidates
        )

        self.assertNotIn(
            ("Ramesh Kumar", "RESPONDENT"),
            candidates
        )

        self.assertNotIn(
            ("Suresh Rao", "DEFENDANT"),
            candidates
        )

    def test_28_firm_partner_not_defendant(self):

        result = self.results[(10, 15)]

        candidates = {
            (item["name"], item["role"])
            for item in result["party_candidates"]
        }

        self.assertNotIn(
            ("MRUDHULA JOGI", "DEFENDANT"),
            candidates
        )

    def test_29_court_evidence_preserved(self):

        for result in self.results.values():

            for item in result["party_candidates"]:

                self.assertTrue(item["source_text"])
                self.assertTrue(item["evidence"])
                self.assertTrue(
                    item["extraction_method"]
                )

    def test_30_manual_review_safety(self):

        for result in self.results.values():

            self.assertTrue(result["requires_review"])
            self.assertFalse(result["verified"])
            self.assertFalse(result["approved_for_search"])
            self.assertFalse(result["eligible_for_alert"])

            for item in result["party_candidates"]:

                self.assertTrue(item["requires_review"])
                self.assertFalse(item["verified"])


if __name__ == "__main__":
    unittest.main()
