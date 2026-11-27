import json
import unittest

from copy import deepcopy
from pathlib import Path

from notices.services.party_name_extractor import (
    deduplicate_party_candidates,
    extract_party_candidates
)

from notices.services.party_variant_grouper import (
    group_party_variants,
    normalize_party_name,
    extract_party_entry_numbers
)


def candidate(
    name,
    role="DEFENDANT",
    evidence="Sample evidence",
    method="EXPLICIT_ROLE",
    language="en"
):

    return {
        "name": name,
        "role": role,
        "language": language,
        "source_text": evidence,
        "extraction_method": method,
        "verified": False,
        "requires_review": True
    }


def numbered_candidate(
    entry,
    name="SRINIVASA",
    role="DEFENDANT"
):

    return candidate(
        name,
        role,
        f"{entry}. SRI. {name}, {role} NO.{entry}",
        "COURT_NUMBERED_EXPLICIT_ROLE"
    )


class PartyIdentityTests(unittest.TestCase):

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

    def test_01_punctuation_normalization(self):

        self.assertEqual(
            normalize_party_name("Gowtham. S"),
            normalize_party_name("Gowtham S")
        )

    def test_02_case_normalization(self):

        self.assertEqual(
            normalize_party_name("RAMESH KUMAR"),
            normalize_party_name("Ramesh Kumar")
        )

    def test_03_whitespace_normalization(self):

        self.assertEqual(
            normalize_party_name("Ramesh   Kumar"),
            normalize_party_name("Ramesh Kumar")
        )

    def test_04_kannada_normalization(self):

        self.assertEqual(
            normalize_party_name("ಆರ್. ಸುಚಿತ್ರ"),
            normalize_party_name("ಆರ್ ಸುಚಿತ್ರ")
        )

    def test_05_different_spellings_preserved(self):

        result = group_party_variants([
            candidate("Ramesh Kumar"),
            candidate("Ramesh Kumaar")
        ])

        self.assertEqual(
            result["group_count"], 2
        )

    def test_06_different_roles_preserved(self):

        result = group_party_variants([
            candidate("Gayathri", "DEFENDANT"),
            candidate("Gayathri", "APPELLANT")
        ])

        self.assertEqual(
            result["group_count"], 2
        )

    def test_07_different_languages_preserved(self):

        result = group_party_variants([
            candidate("Ramesh", language="en"),
            candidate("Ramesh", language="mixed")
        ])

        self.assertEqual(
            result["group_count"], 2
        )

    def test_08_variant_grouping(self):

        result = group_party_variants([
            candidate("Gowtham. S"),
            candidate("Gowtham S")
        ])

        self.assertEqual(
            result["group_count"], 1
        )

        self.assertEqual(
            result["possible_variant_groups"], 1
        )

    def test_09_original_candidates_preserved(self):

        items = [
            candidate("Gowtham. S"),
            candidate("Gowtham S")
        ]

        original = deepcopy(items)

        result = group_party_variants(items)

        self.assertEqual(items, original)

        self.assertEqual(
            result["party_groups"][0][
                "original_candidates"
            ],
            original
        )

    def test_10_court_entry_number_extraction(self):

        item = numbered_candidate(13)

        self.assertEqual(
            extract_party_entry_numbers(item),
            {"13"}
        )

    def test_11_distinct_court_entries(self):

        result = deduplicate_party_candidates([
            numbered_candidate(13),
            numbered_candidate(21)
        ])

        self.assertEqual(len(result), 2)

    def test_12_court_entry_metadata(self):

        result = deduplicate_party_candidates([
            numbered_candidate(13),
            numbered_candidate(21)
        ])

        self.assertEqual(
            {
                tuple(item["court_entry_numbers"])
                for item in result
            },
            {("13",), ("21",)}
        )

    def test_13_identity_conflict_flag(self):

        result = deduplicate_party_candidates([
            numbered_candidate(13),
            numbered_candidate(21)
        ])

        self.assertTrue(all(
            item["identity_conflict"]
            for item in result
        ))

    def test_14_same_entry_duplicate_removed(self):

        result = deduplicate_party_candidates([
            numbered_candidate(13),
            numbered_candidate(13)
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(
            len(result[0]["evidence"]), 1
        )

    def test_15_same_entry_evidence_preserved(self):

        first = numbered_candidate(13)

        second = deepcopy(first)

        second["source_text"] = (
            "13. SRI. SRINIVASA, aged 72 years, "
            "DEFENDANT NO.12"
        )

        result = deduplicate_party_candidates([
            first,
            second
        ])

        self.assertEqual(len(result), 1)

        self.assertEqual(
            len(result[0]["evidence"]), 2
        )

    def test_16_numbered_unnumbered_separate(self):

        result = deduplicate_party_candidates([
            numbered_candidate(13),
            candidate("SRINIVASA")
        ])

        self.assertEqual(len(result), 2)

    def test_17_ordinary_deduplication(self):

        result = deduplicate_party_candidates([
            candidate(
                "Ramesh Kumar",
                "OWNER",
                "Owner evidence one"
            ),
            candidate(
                "Ramesh Kumar",
                "OWNER",
                "Owner evidence two"
            )
        ])

        self.assertEqual(len(result), 1)

        self.assertEqual(
            len(result[0]["evidence"]), 2
        )

    def test_18_distinct_person_group(self):

        items = deduplicate_party_candidates([
            numbered_candidate(13),
            numbered_candidate(21)
        ])

        result = group_party_variants(items)

        self.assertEqual(
            result["possible_distinct_person_groups"],
            1
        )

        self.assertEqual(
            result["party_groups"][0][
                "grouping_status"
            ],
            "POSSIBLE_DISTINCT_PERSONS"
        )

    def test_19_real_srinivasa_defendants(self):

        items = [
            item
            for item in self.results[(7, 1)][
                "party_candidates"
            ]
            if item["name"].casefold() == "srinivasa"
            and item["role"] == "DEFENDANT"
        ]

        self.assertEqual(len(items), 2)

        self.assertEqual(
            {
                tuple(item["court_entry_numbers"])
                for item in items
            },
            {("13",), ("21",)}
        )

    def test_20_real_srinivasa_respondents(self):

        items = [
            item
            for item in self.results[(7, 1)][
                "party_candidates"
            ]
            if item["name"].casefold() == "srinivasa"
            and item["role"] == "RESPONDENT"
        ]

        self.assertEqual(len(items), 2)

        self.assertEqual(
            {
                tuple(item["court_entry_numbers"])
                for item in items
            },
            {("13",), ("21",)}
        )

    def test_21_real_gowtham_variants(self):

        result = group_party_variants(
            self.results[(10, 12)][
                "party_candidates"
            ]
        )

        groups = [
            group
            for group in result["party_groups"]
            if group["normalized_name"] == "gowtham s"
            and group["role"] == "DEFENDANT"
        ]

        self.assertEqual(len(groups), 1)

        self.assertEqual(
            set(groups[0]["name_variants"]),
            {"Gowtham. S", "Gowtham S"}
        )

        self.assertFalse(
            groups[0]["identity_merged"]
        )

    def test_22_all_candidate_keys_unique(self):

        for key, result in self.results.items():

            keys = [
                (
                    item["name"].casefold(),
                    item["role"],
                    item["language"],
                    tuple(sorted(
                        item["court_entry_numbers"]
                    ))
                )
                for item in result["party_candidates"]
            ]

            self.assertEqual(
                len(keys),
                len(set(keys)),
                f"Duplicate candidate in {key}"
            )

    def test_23_all_original_evidence_preserved(self):

        for result in self.results.values():

            items = result["party_candidates"]

            grouped = group_party_variants(items)

            recovered = {}

            for group in grouped["party_groups"]:

                for index, item in zip(
                    group["candidate_indices"],
                    group["original_candidates"]
                ):

                    self.assertNotIn(
                        index, recovered
                    )

                    recovered[index] = item

            self.assertEqual(
                [
                    recovered[index]
                    for index in sorted(recovered)
                ],
                items
            )

    def test_24_all_identity_safety_flags(self):

        for result in self.results.values():

            grouped = group_party_variants(
                result["party_candidates"]
            )

            for item in result["party_candidates"]:

                self.assertFalse(item["verified"])
                self.assertFalse(item["identity_merged"])
                self.assertTrue(item["requires_review"])

            for group in grouped["party_groups"]:

                self.assertFalse(group["verified"])
                self.assertFalse(group["identity_merged"])
                self.assertFalse(group["approved_for_search"])
                self.assertFalse(group["eligible_for_alert"])
                self.assertTrue(group["requires_review"])

    def test_25_empty_candidate_list(self):

        result = group_party_variants([])

        self.assertEqual(
            result["original_candidate_count"], 0
        )

        self.assertEqual(
            result["group_count"], 0
        )

        self.assertEqual(
            result["party_groups"], []
        )

        self.assertFalse(result["verified"])


if __name__ == "__main__":
    unittest.main()
