import unittest

from copy import deepcopy

from notices.services.organization_ocr_validator import (
    validate_organization_candidates,
)


def candidate(
    name,
    suggested_name=None,
    role="SECURED_CREDITOR_CANDIDATE",
):

    return {
        "name": name,
        "suggested_name": suggested_name or name,
        "role": role,
        "entity_kind": "ORGANIZATION",
        "source_text": name,
        "evidence": [name],
    }


class OrganizationOCRValidatorTests(unittest.TestCase):

    def test_01_exact_organization_agreement(self):

        bank = candidate("ICICI Bank")

        result = validate_organization_candidates(
            [bank],
            [deepcopy(bank)],
        )

        self.assertEqual(
            result["status_counts"],
            {"CONSISTENT_UNVERIFIED": 1},
        )

    def test_02_raw_name_agreement(self):

        result = validate_organization_candidates(
            [candidate("ICICI Bank")],
            [candidate("ICICI Bank")],
        )

        self.assertIs(
            result["comparisons"][0]["raw_names_agree"],
            True,
        )

    def test_03_agreement_not_identity_verification(self):

        result = validate_organization_candidates(
            [candidate("ICICI Bank")],
            [candidate("ICICI Bank")],
        )

        self.assertFalse(
            result["organization_identity_verified"]
        )

        self.assertFalse(
            result["comparisons"][0]["verified"]
        )

    def test_04_rbl_multilingual_agreement(self):

        result = validate_organization_candidates(
            [candidate("RBL BANK", "RBL Bank")],
            [candidate("ಆರ್ಬಿಎಲ್ ಬ್ಯಾಂಕ್", "RBL Bank")],
        )

        self.assertEqual(
            result["status_counts"],
            {"CONSISTENT_UNVERIFIED": 1},
        )

    def test_05_rbl_raw_name_difference(self):

        result = validate_organization_candidates(
            [candidate("RBL BANK", "RBL Bank")],
            [candidate("ಆರ್ಬಿಎಲ್ ಬ್ಯಾಂಕ್", "RBL Bank")],
        )

        self.assertEqual(
            result["raw_name_difference_count"],
            1,
        )

        self.assertFalse(
            result["comparisons"][0]["raw_names_agree"]
        )

    def test_06_rbl_kannada_evidence_preserved(self):

        result = validate_organization_candidates(
            [candidate("RBL BANK", "RBL Bank")],
            [candidate("ಆರ್ಬಿಎಲ್ ಬ್ಯಾಂಕ್", "RBL Bank")],
        )

        self.assertEqual(
            result["comparisons"][0][
                "secondary_candidates"
            ][0]["source_text"],
            "ಆರ್ಬಿಎಲ್ ಬ್ಯಾಂಕ್",
        )

    def test_07_baroda_multilingual_agreement(self):

        result = validate_organization_candidates(
            [candidate("Bank of Baroda")],
            [
                candidate(
                    "ಬ್ಯಾಂಕ್ ಆಫ್ ಬರೋಡ",
                    "Bank of Baroda",
                )
            ],
        )

        self.assertEqual(
            result["comparison_count"],
            1,
        )

        self.assertEqual(
            result["raw_name_difference_count"],
            1,
        )

    def test_08_secondary_unavailable(self):

        result = validate_organization_candidates(
            [candidate("ICICI Bank")],
            None,
        )

        self.assertFalse(
            result["secondary_available"]
        )

        self.assertEqual(
            result["status_counts"],
            {"SECONDARY_NOT_AVAILABLE": 1},
        )

    def test_09_missing_ocr_not_disagreement(self):

        result = validate_organization_candidates(
            [candidate("ICICI Bank")],
            None,
        )

        self.assertEqual(
            result["organization_difference_count"],
            0,
        )

        self.assertEqual(
            result["role_difference_count"],
            0,
        )

    def test_10_primary_only_organization(self):

        result = validate_organization_candidates(
            [candidate("ICICI Bank")],
            [],
        )

        self.assertTrue(
            result["secondary_available"]
        )

        self.assertEqual(
            result["status_counts"],
            {"PRIMARY_ONLY": 1},
        )

    def test_11_secondary_only_organization(self):

        result = validate_organization_candidates(
            [],
            [candidate("ICICI Bank")],
        )

        self.assertEqual(
            result["status_counts"],
            {"SECONDARY_ONLY": 1},
        )

    def test_12_different_organizations_separate(self):

        result = validate_organization_candidates(
            [candidate("RBL Bank")],
            [candidate("ICICI Bank")],
        )

        self.assertEqual(
            result["comparison_count"],
            2,
        )

        self.assertEqual(
            result["status_counts"],
            {
                "PRIMARY_ONLY": 1,
                "SECONDARY_ONLY": 1,
            },
        )

    def test_13_organization_difference_detected(self):

        result = validate_organization_candidates(
            [candidate("RBL Bank")],
            [candidate("ICICI Bank")],
        )

        self.assertEqual(
            result["organization_difference_count"],
            1,
        )

        difference = result[
            "organization_differences"
        ][0]

        self.assertEqual(
            difference["primary_only_names"],
            ["rbl bank"],
        )

        self.assertEqual(
            difference["secondary_only_names"],
            ["icici bank"],
        )

    def test_14_different_organizations_not_merged(self):

        result = validate_organization_candidates(
            [candidate("RBL Bank")],
            [candidate("ICICI Bank")],
        )

        for item in result["comparisons"]:

            self.assertFalse(
                item["identity_merged"]
            )

    def test_15_possible_spelling_variation(self):

        result = validate_organization_candidates(
            [candidate("IDBI Bank")],
            [candidate("IDBI B ank")],
        )

        self.assertEqual(
            result["possible_name_variation_count"],
            1,
        )

    def test_16_variations_remain_separate(self):

        result = validate_organization_candidates(
            [candidate("IDBI Bank")],
            [candidate("IDBI B ank")],
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

    def test_17_organization_role_difference(self):

        result = validate_organization_candidates(
            [candidate("ICICI Bank")],
            [
                candidate(
                    "ICICI Bank",
                    role="OTHER_ORGANIZATION",
                )
            ],
        )

        self.assertEqual(
            result["role_difference_count"],
            1,
        )

    def test_18_different_roles_preserved(self):

        result = validate_organization_candidates(
            [candidate("ICICI Bank")],
            [
                candidate(
                    "ICICI Bank",
                    role="OTHER_ORGANIZATION",
                )
            ],
        )

        self.assertEqual(
            {
                item["role"]
                for item in result["comparisons"]
            },
            {
                "SECURED_CREDITOR_CANDIDATE",
                "OTHER_ORGANIZATION",
            },
        )

    def test_19_duplicate_occurrences_preserved(self):

        result = validate_organization_candidates(
            [
                candidate("ICICI Bank"),
                candidate("ICICI Bank"),
            ],
            [candidate("ICICI Bank")],
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

    def test_20_original_inputs_unchanged(self):

        primary = [candidate("ICICI Bank")]
        secondary = [candidate("ICICI BANK")]

        first = deepcopy(primary)
        second = deepcopy(secondary)

        validate_organization_candidates(
            primary,
            secondary,
        )

        self.assertEqual(primary, first)
        self.assertEqual(secondary, second)

    def test_21_original_evidence_preserved(self):

        bank = candidate("Union Bank of India")

        bank["evidence"] = [
            {
                "source_text": "Original newspaper evidence",
                "line_number": 12,
            }
        ]

        result = validate_organization_candidates(
            [bank],
            None,
        )

        self.assertEqual(
            result["comparisons"][0][
                "primary_candidates"
            ][0],
            bank,
        )

    def test_22_output_independent_of_input(self):

        original = [candidate("ICICI Bank")]

        snapshot = deepcopy(original)

        result = validate_organization_candidates(
            original,
            None,
        )

        result["comparisons"][0][
            "primary_candidates"
        ][0]["evidence"].append("Modified")

        self.assertEqual(
            original,
            snapshot,
        )

    def test_23_empty_input(self):

        result = validate_organization_candidates(
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

        self.assertEqual(
            result["organization_difference_count"],
            0,
        )

    def test_24_invalid_similarity_threshold(self):

        for threshold in (-0.1, 1.5):

            with self.subTest(threshold=threshold):

                with self.assertRaises(ValueError):

                    validate_organization_candidates(
                        [],
                        [],
                        similarity_threshold=threshold,
                    )

    def test_25_missing_organization_name(self):

        with self.assertRaises(ValueError):

            validate_organization_candidates(
                [{"name": "", "role": "OTHER"}],
                [],
            )

    def test_26_all_output_safety_flags(self):

        result = validate_organization_candidates(
            [
                candidate("RBL BANK", "RBL Bank"),
                candidate("IDBI Bank"),
                candidate("ICICI Bank"),
            ],
            [
                candidate(
                    "ಆರ್ಬಿಎಲ್ ಬ್ಯಾಂಕ್",
                    "RBL Bank",
                ),
                candidate("IDBI B ank"),
                candidate(
                    "ICICI Bank",
                    role="OTHER_ORGANIZATION",
                ),
            ],
        )

        items = [result]

        for field in (
            "comparisons",
            "raw_name_differences",
            "possible_name_variations",
            "role_differences",
            "organization_differences",
        ):

            self.assertTrue(result[field])

            items.extend(result[field])

        for item in items:

            self.assertIs(
                item["requires_review"],
                True,
            )

            for field in (
                "verified",
                "identity_merged",
                "ownership_verified",
                "legal_entitlement_verified",
                "creditor_rights_verified",
                "mortgage_verified",
                "organization_identity_verified",
                "approved_for_search",
                "eligible_for_alert",
            ):

                self.assertIs(
                    item[field],
                    False,
                )

    def test_27_strict_similarity_threshold(self):

        result = validate_organization_candidates(
            [candidate("IDBI Bank")],
            [candidate("IDBI B ank")],
            similarity_threshold=1.0,
        )

        self.assertEqual(
            result["possible_name_variation_count"],
            0,
        )

    def test_28_name_fallback_without_suggestion(self):

        bank = candidate("ICICI Bank")

        del bank["suggested_name"]

        result = validate_organization_candidates(
            [bank],
            [candidate("ICICI Bank")],
        )

        self.assertEqual(
            result["status_counts"],
            {"CONSISTENT_UNVERIFIED": 1},
        )

    def test_29_multiple_organizations_preserved(self):

        primary = [
            candidate("Union Bank of India"),
            candidate("ICICI Bank"),
            candidate("RBL Bank"),
        ]

        secondary = [
            candidate("ICICI Bank"),
            candidate("RBL Bank"),
            candidate("IDBI Bank"),
        ]

        result = validate_organization_candidates(
            primary,
            secondary,
        )

        self.assertEqual(
            result["status_counts"],
            {
                "CONSISTENT_UNVERIFIED": 2,
                "PRIMARY_ONLY": 1,
                "SECONDARY_ONLY": 1,
            },
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

    def test_30_real_organization_baseline(self):

        pairs = [
            (
                "ಯೂನಿಯನ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ",
                "ಯೂನಿಯನ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ",
                "Union Bank of India",
            ),
            (
                "ಯೂನಿಯನ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ",
                "ಯೂನಿಯನ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ",
                "Union Bank of India",
            ),
            (
                "ಐಸಿಐಸಿಐ ಬ್ಯಾಂಕ್ ಲಿಮಿಟೆಡ್",
                "ಐಸಿಐಸಿಐ ಬ್ಯಾಂಕ್ ಲಿಮಿಟೆಡ್",
                "ICICI Bank",
            ),
            (
                "ಜನ ಸ್ಮಾಲ್ ಫೈನಾನ್ಸ್ ಬ್ಯಾಂಕ್ ಲಿಮಿಟೆಡ್",
                "ಜನ ಸ್ಮಾಲ್ ಫೈನಾನ್ಸ್ ಬ್ಯಾಂಕ್ ಲಿಮಿಟೆಡ್",
                "Jana Small Finance Bank",
            ),
            (
                "ಐಡಿಬಿಐ ಬ್ಯಾಂಕ್ ಲಿಮಿಟೆಡ್",
                "ಐಡಿಬಿಐ ಬ್ಯಾಂಕ್ ಲಿಮಿಟೆಡ್",
                "IDBI Bank",
            ),
            (
                "RBL BANK",
                "ಆರ್ಬಿಎಲ್ ಬ್ಯಾಂಕ್",
                "RBL Bank",
            ),
            (
                "Bank of Baroda",
                "ಬ್ಯಾಂಕ್ ಆಫ್ ಬರೋಡ",
                "Bank of Baroda",
            ),
            (
                "ಯೂನಿಯನ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ",
                "ಯೂನಿಯನ್ ಬ್ಯಾಂಕ್ ಆಫ್ ಇಂಡಿಯಾ",
                "Union Bank of India",
            ),
        ]

        groups = 0
        differences = 0
        occurrences = 0

        for first, second, suggested in pairs:

            with self.subTest(organization=suggested):

                result = validate_organization_candidates(
                    [candidate(first, suggested)],
                    [candidate(second, suggested)],
                )

                self.assertEqual(
                    result["status_counts"],
                    {"CONSISTENT_UNVERIFIED": 1},
                )

                self.assertEqual(
                    result["organization_difference_count"],
                    0,
                )

                groups += result["comparison_count"]

                differences += result[
                    "raw_name_difference_count"
                ]

                occurrences += (
                    result["primary_candidate_count"]
                    + result["secondary_candidate_count"]
                )

        self.assertEqual(groups, 8)
        self.assertEqual(differences, 2)
        self.assertEqual(occurrences, 16)


if __name__ == "__main__":

    unittest.main()
