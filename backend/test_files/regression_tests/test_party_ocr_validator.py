import unittest

from copy import deepcopy

from notices.services.party_ocr_validator import (
    normalize_party_name,
    validate_party_candidates,
)


def candidate(
    name,
    role="OWNER",
    language="en",
    entries=None,
):

    return {
        "name": name,
        "role": role,
        "language": language,
        "court_entry_numbers": entries or [],
        "source_text": f"Original evidence: {name}",
    }


class PartyOCRValidatorTests(unittest.TestCase):

    def test_01_english_normalization(self):

        self.assertEqual(
            normalize_party_name("  G.N. Ramesh  "),
            "g n ramesh",
        )

    def test_02_kannada_normalization(self):

        self.assertEqual(
            normalize_party_name("ಜಿ.ಎನ್. ರಮೇಶ್"),
            "ಜಿ ಎನ್ ರಮೇಶ್",
        )

    def test_03_unicode_joiner_normalization(self):

        self.assertEqual(
            normalize_party_name("ರ\u200dಮೇಶ್"),
            normalize_party_name("ರಮೇಶ್"),
        )

    def test_04_exact_agreement(self):

        result = validate_party_candidates(
            [candidate("Gopal")],
            [candidate("GOPAL")],
        )

        self.assertEqual(
            result["status_counts"],
            {"CONSISTENT_UNVERIFIED": 1},
        )

    def test_05_agreement_not_verification(self):

        result = validate_party_candidates(
            [candidate("Gopal")],
            [candidate("Gopal")],
        )

        self.assertFalse(
            result["comparisons"][0]["verified"]
        )

    def test_06_secondary_unavailable(self):

        result = validate_party_candidates(
            [candidate("Gopal")],
            None,
        )

        self.assertFalse(
            result["secondary_available"]
        )

        self.assertEqual(
            result["status_counts"],
            {"SECONDARY_NOT_AVAILABLE": 1},
        )

    def test_07_primary_only(self):

        result = validate_party_candidates(
            [candidate("Gopal")],
            [],
        )

        self.assertTrue(
            result["secondary_available"]
        )

        self.assertEqual(
            result["status_counts"],
            {"PRIMARY_ONLY": 1},
        )

    def test_08_secondary_only(self):

        result = validate_party_candidates(
            [],
            [candidate("Gopal")],
        )

        self.assertEqual(
            result["status_counts"],
            {"SECONDARY_ONLY": 1},
        )

    def test_09_possible_name_variation(self):

        result = validate_party_candidates(
            [candidate("Narayanappa")],
            [candidate("Narayenappa")],
        )

        self.assertEqual(
            result["possible_name_variation_count"],
            1,
        )

    def test_10_name_variations_remain_separate(self):

        result = validate_party_candidates(
            [candidate("Narayanappa")],
            [candidate("Narayenappa")],
        )

        self.assertEqual(
            result["comparison_count"],
            2,
        )

        self.assertFalse(
            result["possible_name_variations"][0][
                "identity_merged"
            ]
        )

    def test_11_role_difference(self):

        result = validate_party_candidates(
            [candidate("Ramesh", "OWNER")],
            [candidate("Ramesh", "BORROWER")],
        )

        self.assertEqual(
            result["role_difference_count"],
            1,
        )

    def test_12_role_preservation(self):

        result = validate_party_candidates(
            [candidate("Ramesh", "OWNER")],
            [candidate("Ramesh", "BORROWER")],
        )

        self.assertEqual(
            {
                item["role"]
                for item in result["comparisons"]
            },
            {"OWNER", "BORROWER"},
        )

    def test_13_multiple_roles_agree(self):

        parties = [
            candidate("Ramesh", "OWNER"),
            candidate("Ramesh", "BORROWER"),
        ]

        result = validate_party_candidates(
            parties,
            deepcopy(parties),
        )

        self.assertEqual(
            result["role_difference_count"],
            0,
        )

        self.assertEqual(
            result["comparison_count"],
            2,
        )

    def test_14_court_entry_difference(self):

        result = validate_party_candidates(
            [
                candidate(
                    "Srinivasa",
                    "DEFENDANT",
                    entries=["13"],
                )
            ],
            [
                candidate(
                    "Srinivasa",
                    "DEFENDANT",
                    entries=["21"],
                )
            ],
        )

        self.assertEqual(
            result["entry_number_difference_count"],
            1,
        )

    def test_15_distinct_court_entries_preserved(self):

        result = validate_party_candidates(
            [
                candidate(
                    "Srinivasa",
                    "DEFENDANT",
                    entries=["13"],
                ),
                candidate(
                    "Srinivasa",
                    "DEFENDANT",
                    entries=["21"],
                ),
            ],
            None,
        )

        self.assertEqual(
            result["comparison_count"],
            2,
        )

        self.assertEqual(
            {
                tuple(item["court_entry_numbers"])
                for item in result["comparisons"]
            },
            {("13",), ("21",)},
        )

    def test_16_entry_difference_blocks_fuzzy_pairing(self):

        result = validate_party_candidates(
            [
                candidate(
                    "Narayanappa",
                    "DEFENDANT",
                    entries=["13"],
                )
            ],
            [
                candidate(
                    "Narayenappa",
                    "DEFENDANT",
                    entries=["21"],
                )
            ],
        )

        self.assertEqual(
            result["possible_name_variation_count"],
            0,
        )

    def test_17_missing_entry_number(self):

        result = validate_party_candidates(
            [
                candidate(
                    "Gopal",
                    "DEFENDANT",
                    entries=["23"],
                )
            ],
            [
                candidate(
                    "Gopal",
                    "DEFENDANT",
                )
            ],
        )

        self.assertEqual(
            result["entry_number_difference_count"],
            1,
        )

    def test_18_matching_entry_numbers(self):

        party = candidate(
            "Gopal",
            "DEFENDANT",
            entries=["23"],
        )

        result = validate_party_candidates(
            [party],
            [deepcopy(party)],
        )

        self.assertEqual(
            result["entry_number_difference_count"],
            0,
        )

        self.assertEqual(
            result["comparison_count"],
            1,
        )

    def test_19_entry_number_order_normalization(self):

        result = validate_party_candidates(
            [
                candidate(
                    "Gopal",
                    "DEFENDANT",
                    entries=["23", "24"],
                )
            ],
            [
                candidate(
                    "Gopal",
                    "DEFENDANT",
                    entries=["24", "23"],
                )
            ],
        )

        self.assertEqual(
            result["status_counts"],
            {"CONSISTENT_UNVERIFIED": 1},
        )

    def test_20_cross_language_pairing_blocked(self):

        result = validate_party_candidates(
            [candidate("Gopal", language="en")],
            [candidate("ಗೋಪಾಲ್", language="kn")],
        )

        self.assertEqual(
            result["comparison_count"],
            2,
        )

        self.assertEqual(
            result["possible_name_variation_count"],
            0,
        )

    def test_21_short_names_excluded(self):

        result = validate_party_candidates(
            [candidate("Anu")],
            [candidate("Ani")],
        )

        self.assertEqual(
            result["possible_name_variation_count"],
            0,
        )

    def test_22_duplicate_occurrences_preserved(self):

        result = validate_party_candidates(
            [
                candidate("Ramesh"),
                candidate("Ramesh"),
            ],
            [candidate("Ramesh")],
        )

        group = result["comparisons"][0]

        self.assertEqual(
            group["primary_occurrence_count"],
            2,
        )

        self.assertEqual(
            group["secondary_occurrence_count"],
            1,
        )

    def test_23_original_input_unchanged(self):

        primary = [candidate("Ramesh")]
        secondary = [candidate("RAMESH")]

        first_snapshot = deepcopy(primary)
        second_snapshot = deepcopy(secondary)

        validate_party_candidates(
            primary,
            secondary,
        )

        self.assertEqual(
            primary,
            first_snapshot,
        )

        self.assertEqual(
            secondary,
            second_snapshot,
        )

    def test_24_original_evidence_preserved(self):

        primary = candidate("Ramesh")

        primary["original_candidate"] = {
            "source_text": "Original newspaper text",
            "extraction_method": "TEST_METHOD",
        }

        result = validate_party_candidates(
            [primary],
            None,
        )

        self.assertEqual(
            result["comparisons"][0][
                "primary_candidates"
            ][0],
            primary,
        )

    def test_25_output_independent_of_input(self):

        primary = [candidate("Ramesh")]

        result = validate_party_candidates(
            primary,
            None,
        )

        result["comparisons"][0][
            "primary_candidates"
        ][0]["name"] = "Modified"

        self.assertEqual(
            primary[0]["name"],
            "Ramesh",
        )

    def test_26_all_output_safety_flags(self):

        result = validate_party_candidates(
            [
                candidate("Narayanappa"),
                candidate("Ramesh", "OWNER"),
                candidate(
                    "Gopal",
                    "DEFENDANT",
                    entries=["23"],
                ),
            ],
            [
                candidate("Narayenappa"),
                candidate("Ramesh", "BORROWER"),
                candidate(
                    "Gopal",
                    "DEFENDANT",
                    entries=["24"],
                ),
            ],
        )

        items = [result]

        for field in (
            "comparisons",
            "possible_name_variations",
            "role_differences",
            "entry_number_differences",
        ):

            self.assertTrue(result[field])

            items.extend(result[field])

        for item in items:

            self.assertIs(
                item["requires_review"],
                True,
            )

            for field in (
                "identity_merged",
                "verified",
                "ownership_verified",
                "legal_entitlement_verified",
                "approved_for_search",
                "eligible_for_alert",
            ):

                self.assertIs(
                    item[field],
                    False,
                )

    def test_27_empty_input(self):

        result = validate_party_candidates(
            [],
            [],
        )

        self.assertEqual(
            result["comparison_count"],
            0,
        )

        self.assertEqual(
            result["status_counts"],
            {},
        )

    def test_28_invalid_threshold(self):

        for threshold in (-0.1, 1.5):

            with self.subTest(threshold=threshold):

                with self.assertRaises(ValueError):

                    validate_party_candidates(
                        [],
                        [],
                        similarity_threshold=threshold,
                    )

    def test_29_strict_similarity_threshold(self):

        result = validate_party_candidates(
            [candidate("Narayanappa")],
            [candidate("Narayenappa")],
            similarity_threshold=1.0,
        )

        self.assertEqual(
            result["possible_name_variation_count"],
            0,
        )

    def test_30_total_occurrence_preservation(self):

        primary = [
            candidate("Gopal"),
            candidate("Gopal"),
            candidate("Narayanappa"),
            candidate("Ramesh", "OWNER"),
        ]

        secondary = [
            candidate("Gopal"),
            candidate("Narayenappa"),
            candidate("Ramesh", "BORROWER"),
            candidate("Lakshmi"),
        ]

        result = validate_party_candidates(
            primary,
            secondary,
        )

        self.assertEqual(
            sum(
                item["primary_occurrence_count"]
                for item in result["comparisons"]
            ),
            len(primary),
        )

        self.assertEqual(
            sum(
                item["secondary_occurrence_count"]
                for item in result["comparisons"]
            ),
            len(secondary),
        )


if __name__ == "__main__":

    unittest.main()
