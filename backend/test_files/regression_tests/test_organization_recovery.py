"""
Permanent regression tests for organization recovery
and original Unicode OCR evidence preservation.
"""

import unittest
from copy import deepcopy

from notices.services.organization_recovery import (
    recover_organization_candidates,
    normalize_organization_text,
)

from notices.services.bank_party_extractor import (
    extract_bank_party_candidates,
    integrate_recovered_organizations,
)

from notices.services.organization_ocr_validator import (
    validate_organization_candidates,
)


CATEGORY = "SECURED_PROPERTY_POSSESSION"

EXPECTED_NAME = (
    "Aptus Value Housing Finance India Limited"
)

PRIMARY_LINE = (
    "ಅಪ್ಪಸ್\u200c ವ್ಯಾಲ್ಯೂ PLOT "
    "ಫೈನಾನ್ಸ್\u200c ಇಂಡಿಯಾ ಲಿಮಿಟೆಡ್\u200cಗೆ"
)

SECONDARY_LINE = (
    "ಅಪ್ಪಸ್\u200c ವ್ಯಾಲ್ಯೂ ಕೌಸಿಂಗ್\u200c "
    "ಫೈನಾನ್ಸ್\u200c ಇಂಡಿಯಾ ಲಿಮಿಟೆಡ್\u200cಗೆ"
)

PRIMARY = "ಸ್ವಾಧೀನ ಸೂಚನೆ\n" + PRIMARY_LINE

SECONDARY = "ಸ್ವಾಧೀನ ಸೂಚನೆ\n" + SECONDARY_LINE


class OrganizationRecoveryTests(unittest.TestCase):

    def recover(self, text, category=CATEGORY):

        return recover_organization_candidates(
            text,
            category,
        )

    def candidate(self, text):

        result = self.recover(text)

        self.assertEqual(
            result["organization_count"],
            1,
        )

        return result["organization_candidates"][0]

    def test_01_primary_ocr_recovery(self):

        self.assertEqual(
            self.recover(PRIMARY)["organization_count"],
            1,
        )

    def test_02_secondary_ocr_recovery(self):

        self.assertEqual(
            self.recover(SECONDARY)["organization_count"],
            1,
        )

    def test_03_correct_suggested_name(self):

        self.assertEqual(
            self.candidate(PRIMARY)["suggested_name"],
            EXPECTED_NAME,
        )

    def test_04_correct_kannada_spelling(self):

        text = (
            "ಸ್ವಾಧೀನ ಸೂಚನೆ\n"
            "ಆಪ್ಟಸ್ ವ್ಯಾಲ್ಯೂ ಹೌಸಿಂಗ್ "
            "ಫೈನಾನ್ಸ್ ಇಂಡಿಯಾ ಲಿಮಿಟೆಡ್"
        )

        self.assertEqual(
            self.recover(text)["organization_count"],
            1,
        )

    def test_05_incomplete_name_rejected(self):

        self.assertEqual(
            self.recover(
                "ಸ್ವಾಧೀನ ಸೂಚನೆ ಅಪ್ಪಸ್ ಫೈನಾನ್ಸ್"
            )["organization_count"],
            0,
        )

    def test_06_unrelated_organization_rejected(self):

        self.assertEqual(
            self.recover(
                "ಸ್ವಾಧೀನ ಸೂಚನೆ ಐಸಿಐಸಿಐ ಬ್ಯಾಂಕ್ ಲಿಮಿಟೆಡ್"
            )["organization_count"],
            0,
        )

    def test_07_missing_legal_context_rejected(self):

        self.assertEqual(
            self.recover(
                SECONDARY_LINE
            )["organization_count"],
            0,
        )

    def test_08_non_secured_category_rejected(self):

        self.assertEqual(
            self.recover(
                PRIMARY,
                "ESTATE_PROPERTY_NOTICE",
            )["organization_count"],
            0,
        )

    def test_09_empty_text(self):

        self.assertEqual(
            self.recover("")["organization_count"],
            0,
        )

    def test_10_none_text(self):

        self.assertEqual(
            self.recover(None)["organization_count"],
            0,
        )

    def test_11_primary_original_evidence(self):

        candidate = self.candidate(PRIMARY)

        self.assertEqual(
            candidate["source_text"],
            PRIMARY_LINE,
        )

        self.assertEqual(
            candidate["evidence"][0]["source_text"],
            PRIMARY_LINE,
        )

    def test_12_secondary_original_evidence(self):

        candidate = self.candidate(SECONDARY)

        self.assertEqual(
            candidate["source_text"],
            SECONDARY_LINE,
        )

        self.assertEqual(
            candidate["evidence"][0]["source_text"],
            SECONDARY_LINE,
        )

    def test_13_unicode_non_joiners_preserved(self):

        primary = self.candidate(PRIMARY)

        secondary = self.candidate(SECONDARY)

        self.assertEqual(
            primary["source_text"].count("\u200c"),
            3,
        )

        self.assertEqual(
            secondary["source_text"].count("\u200c"),
            4,
        )

    def test_14_normalization_for_matching(self):

        normalized = normalize_organization_text(
            SECONDARY_LINE
        )

        self.assertNotIn(
            "\u200c",
            normalized,
        )

        self.assertIn(
            "\u200c",
            SECONDARY_LINE,
        )

    def test_15_original_line_number(self):

        text = (
            "ಸ್ವಾಧೀನ ಸೂಚನೆ\n\n"
            "Additional information\n"
            + PRIMARY_LINE
        )

        candidate = self.candidate(text)

        self.assertEqual(
            candidate["evidence"][0]["line_number"],
            4,
        )

    def test_16_duplicate_occurrences_grouped(self):

        result = self.recover(
            PRIMARY + "\n" + PRIMARY_LINE
        )

        self.assertEqual(
            result["organization_count"],
            1,
        )

        self.assertEqual(
            len(
                result["organization_candidates"][0][
                    "evidence"
                ]
            ),
            2,
        )

    def test_17_different_raw_variants_preserved(self):

        candidate = self.candidate(
            PRIMARY + "\n" + SECONDARY_LINE
        )

        self.assertEqual(
            len(candidate["name_variants"]),
            2,
        )

        self.assertEqual(
            len(candidate["evidence"]),
            2,
        )

    def test_18_confidence_and_uncertainty(self):

        candidate = self.candidate(PRIMARY)

        self.assertEqual(
            candidate["confidence"],
            "LOW",
        )

        self.assertTrue(
            candidate["name_uncertain"]
        )

        self.assertTrue(
            candidate["ocr_correction_applied"]
        )

    def test_19_candidate_role_and_entity_kind(self):

        candidate = self.candidate(PRIMARY)

        self.assertEqual(
            candidate["role"],
            "SECURED_CREDITOR_CANDIDATE",
        )

        self.assertEqual(
            candidate["entity_kind"],
            "ORGANIZATION",
        )

    def test_20_safety_restrictions(self):

        candidate = self.candidate(PRIMARY)

        self.assertTrue(
            candidate["requires_review"]
        )

        for key in (

            "verified",
            "identity_merged",
            "organization_identity_verified",
            "creditor_rights_verified",
            "mortgage_verified",
            "ownership_verified",
            "legal_entitlement_verified",
            "approved_for_search",
            "eligible_for_alert",

        ):

            with self.subTest(flag=key):

                self.assertIs(
                    candidate[key],
                    False,
                )

    def test_21_primary_bank_integration(self):

        result = extract_bank_party_candidates(
            PRIMARY,
            CATEGORY,
        )

        candidates = [

            item for item in result[
                "organization_candidates"
            ]

            if item.get("extraction_method")
            == "APTUS_KANNADA_OCR_RECOVERY"

        ]

        self.assertEqual(
            len(candidates),
            1,
        )

        self.assertEqual(
            candidates[0],
            self.candidate(PRIMARY),
        )

    def test_22_secondary_bank_integration(self):

        result = extract_bank_party_candidates(
            SECONDARY,
            CATEGORY,
        )

        candidates = [

            item for item in result[
                "organization_candidates"
            ]

            if item.get("extraction_method")
            == "APTUS_KANNADA_OCR_RECOVERY"

        ]

        self.assertEqual(
            len(candidates),
            1,
        )

        self.assertEqual(
            candidates[0],
            self.candidate(SECONDARY),
        )

    def test_23_existing_candidate_preserved(self):

        existing = [

            {
                "name": "Union Bank of India",
                "suggested_name": "Union Bank of India",
                "role": "SECURED_CREDITOR_CANDIDATE",
                "entity_kind": "ORGANIZATION",
                "verified": False,
            }

        ]

        original = deepcopy(existing)

        updated = integrate_recovered_organizations(
            existing,
            PRIMARY,
            CATEGORY,
        )

        self.assertEqual(
            len(updated),
            2,
        )

        self.assertEqual(
            updated[0],
            original[0],
        )

        self.assertEqual(
            existing,
            original,
        )

    def test_24_duplicate_suggestion_prevented(self):

        existing = [

            {
                "name": EXPECTED_NAME,
                "suggested_name": EXPECTED_NAME,
                "role": "SECURED_CREDITOR_CANDIDATE",
                "entity_kind": "ORGANIZATION",
                "verified": False,
            }

        ]

        original = deepcopy(existing)

        updated = integrate_recovered_organizations(
            existing,
            PRIMARY,
            CATEGORY,
        )

        self.assertEqual(
            updated,
            original,
        )

        self.assertEqual(
            existing,
            original,
        )

    def test_25_dual_ocr_organization_validation(self):

        primary = self.recover(PRIMARY)[
            "organization_candidates"
        ]

        secondary = self.recover(SECONDARY)[
            "organization_candidates"
        ]

        result = validate_organization_candidates(
            primary,
            secondary,
        )

        self.assertEqual(
            result["comparison_count"],
            1,
        )

        self.assertEqual(
            result["status_counts"],
            {"CONSISTENT_UNVERIFIED": 1},
        )

        self.assertEqual(
            result["raw_name_difference_count"],
            1,
        )

        self.assertFalse(
            result["verified"]
        )

        self.assertFalse(
            result["eligible_for_alert"]
        )


if __name__ == "__main__":

    unittest.main()
