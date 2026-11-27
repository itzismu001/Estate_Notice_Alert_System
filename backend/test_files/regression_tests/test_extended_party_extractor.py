import json
import unittest

from pathlib import Path

from notices.services.party_name_extractor import (
    extract_party_candidates
)


class ExtendedPartyExtractorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        data = json.loads(
            Path(
                "test_files/party_extraction_audit/results.json"
            ).read_text(encoding="utf-8")
        )

        cls.results = {}

        for record in data["results"]:

            key = (
                record["page_number"],
                record["region_number"]
            )

            cls.results[key] = extract_party_candidates(
                record["raw_text"]
            )

    def assert_candidate(self, page, region, name, role):

        candidates = {
            (item["name"], item["role"])
            for item in self.results[
                (page, region)
            ]["party_candidates"]
        }

        self.assertIn((name, role), candidates)

    def test_01_real_kannada_client(self):

        self.assert_candidate(
            7, 3,
            "ಆರ್. ಸುಚಿತ್ರ",
            "CLIENT"
        )

    def test_02_real_kannada_advocate(self):

        self.assert_candidate(
            7, 3,
            "ಚಂದ್ರಿಕಾ ಪಿ. ಶೆಟ್ಟಿ",
            "ADVOCATE"
        )

    def test_03_real_english_client(self):

        self.assert_candidate(
            7, 4,
            "Bavadeep Reddy",
            "CLIENT"
        )

    def test_04_real_signed_advocate(self):

        self.assert_candidate(
            7, 4,
            "Leelaraju",
            "ADVOCATE"
        )

    def test_05_real_kannada_client_initial(self):

        self.assert_candidate(
            10, 1,
            "ಸಂಧ್ಯಾ ಹೆಚ್",
            "CLIENT"
        )

    def test_06_real_uppercase_client(self):

        self.assert_candidate(
            10, 3,
            "A. RAJESH",
            "CLIENT"
        )

    def test_07_real_client_surname_initial(self):

        self.assert_candidate(
            10, 4,
            "Lisha R",
            "CLIENT"
        )

    def test_08_real_uppercase_advocate(self):

        self.assert_candidate(
            11, 1,
            "BAYYA REDDY. M",
            "ADVOCATE"
        )

    def test_09_real_reverse_owner(self):

        self.assert_candidate(
            11, 7,
            "N. Sanjana Reddy",
            "OWNER"
        )

    def test_10_multiline_client(self):

        result = extract_party_candidates(
            "our client\nMr. Ramesh Kumar, "
            "residing at Bengaluru"
        )

        candidates = {
            (item["name"], item["role"])
            for item in result["party_candidates"]
        }

        self.assertIn(
            ("Ramesh Kumar", "CLIENT"),
            candidates
        )

    def test_11_honorific_without_space(self):

        result = extract_party_candidates(
            "my client Smt.GAYATHRI, "
            "residing at Bengaluru"
        )

        candidates = {
            (item["name"], item["role"])
            for item in result["party_candidates"]
        }

        self.assertIn(
            ("GAYATHRI", "CLIENT"),
            candidates
        )

    def test_12_multiple_initials(self):

        result = extract_party_candidates(
            "my client Mr. N.D. Solomon Raju, "
            "residing at Bengaluru"
        )

        candidates = {
            (item["name"], item["role"])
            for item in result["party_candidates"]
        }

        self.assertIn(
            ("N.D. Solomon Raju", "CLIENT"),
            candidates
        )

    def test_13_kannada_owner_variation(self):

        result = extract_party_candidates(
            "ಮೂಲ ಮಾಲಕರಾದ ಶ್ರೀಮತಿ ಶೋಭಾರಾಣಿ, "
            "ವಾಸ ಬೆಂಗಳೂರು"
        )

        candidates = {
            (item["name"], item["role"])
            for item in result["party_candidates"]
        }

        self.assertIn(
            ("ಶೋಭಾರಾಣಿ", "OWNER"),
            candidates
        )

    def test_14_client_not_automatically_owner(self):

        result = extract_party_candidates(
            "my client Mr. Ramesh Kumar, "
            "intends to purchase the property."
        )

        candidates = {
            (item["name"], item["role"])
            for item in result["party_candidates"]
        }

        self.assertIn(
            ("Ramesh Kumar", "CLIENT"),
            candidates
        )

        self.assertNotIn(
            ("Ramesh Kumar", "OWNER"),
            candidates
        )

    def test_15_organization_exclusion(self):

        result = extract_party_candidates(
            "Sd/- Nandi Associates, Advocate"
        )

        self.assertEqual(
            result["candidate_count"], 0
        )

    def test_16_sentence_fragment_exclusion(self):

        result = extract_party_candidates(
            "our client of properties in Kodathi Village,"
        )

        self.assertEqual(
            result["candidate_count"], 0
        )

    def test_17_no_duplicate_name_role_pairs(self):

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


    def test_18_candidate_evidence_preserved(self):

        for result in self.results.values():

            for item in result["party_candidates"]:

                self.assertTrue(item["source_text"])
                self.assertTrue(item["evidence"])
                self.assertTrue(item["extraction_method"])

    def test_19_no_automatic_verification(self):

        for result in self.results.values():

            self.assertFalse(result["verified"])
            self.assertFalse(result["approved_for_search"])
            self.assertFalse(result["eligible_for_alert"])
            self.assertTrue(result["requires_review"])

            for item in result["party_candidates"]:

                self.assertFalse(item["verified"])
                self.assertTrue(item["requires_review"])

    def test_20_existing_candidates_preserved(self):

        data = json.loads(
            Path(
                "test_files/extended_party_extraction/results.json"
            ).read_text(encoding="utf-8")
        )

        for record in data["results"]:

            key = (
                record["page_number"],
                record["region_number"]
            )

            previous = {
                (item["name"], item["role"])
                for item in record[
                    "previous"
                ]["party_candidates"]
            }

            current = {
                (item["name"], item["role"])
                for item in self.results[
                    key
                ]["party_candidates"]
            }

            self.assertTrue(
                previous.issubset(current),
                f"Existing candidates lost in {key}"
            )


if __name__ == "__main__":
    unittest.main()
