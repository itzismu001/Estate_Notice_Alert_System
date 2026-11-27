"""
Permanent regression tests for unified party,
organization and legal relationship validation.
"""

import unittest

from copy import deepcopy
from unittest.mock import patch

from notices.services.unified_party_extractor import (
    extract_unified_parties,
)

from notices.services.party_ocr_validator import (
    validate_party_candidates,
)

from notices.services.organization_ocr_validator import (
    validate_organization_candidates,
)

from notices.services.legal_relationship_ocr_validator import (
    validate_legal_relationships,
)


VALIDATORS = (

    "party_validation",

    "organization_validation",

    "legal_relationship_validation",

)


def source_result(raw_text):

    return {

        "notice_category": "CONTROLLED_TEST",

        "party_candidates": [

            {

                "name": "Kamalamma",

                "normalized_name": "kamalamma",

                "role": "LEGAL_REPRESENTATIVE",

                "language": "en",

                "module": "LEGAL_REPRESENTATIVE",

                "court_entry_numbers": ["23(a)"],

                "original_candidate": {

                    "source_text":
                        "Kamalamma W/o Late Gopal\u200c",

                },

            },

        ],

        "candidate_count": 1,

        "organization_candidates": [

            {

                "name": "Union Bank",

                "suggested_name": "Union Bank of India",

                "role": "SECURED_CREDITOR_CANDIDATE",

                "entity_kind": "ORGANIZATION",

                "source_text": "Union Bank of India\u200c",

            },

        ],

        "organization_count": 1,

        "legal_representative_associations": [

            {

                "deceased_person": "Gopal",

                "deceased_entry_number": "23",

                "representative_name": "Kamalamma",

                "representative_entry_number": "23(a)",

                "respondent_number": "24",

                "relationship": "WIFE",

                "relationship_uncertain": False,

                "relationship_conflict": False,

                "identity_conflict": False,

                "source_text":
                    "Kamalamma W/o Late Gopal\u200c",

            },

        ],

        "legal_representative_count": 1,

        "module_counts": {

            "GENERAL": 0,

            "INHERITANCE": 0,

            "BANK": 0,

            "LEGAL_REPRESENTATIVE": 1,

        },

        "raw_text": raw_text,

    }


class UnifiedValidationIntegrationTests(
    unittest.TestCase
):

    def setUp(self):

        self.primary = source_result(
            "Primary OCR evidence"
        )

        self.secondary = source_result(
            "Secondary OCR evidence"
        )

    def execute(
        self,
        primary,
        secondary=None,
        similarity_threshold=0.80,
    ):

        responses = [primary]

        secondary_text = None

        if secondary is not None:

            responses.append(secondary)

            secondary_text = secondary["raw_text"]

        with patch(

            "notices.services.unified_party_extractor."
            "extract_source_parties",

            side_effect=responses,

        ) as extractor:

            result = extract_unified_parties(

                primary["raw_text"],

                secondary_text,

                notice_category="CONTROLLED_TEST",

                similarity_threshold=similarity_threshold,

            )

            return result, extractor.call_count

    def dual(self):

        return self.execute(
            self.primary,
            self.secondary,
        )[0]

    def assert_safe(self, item):

        self.assertIs(
            item["requires_review"],
            True,
        )

        for key in (

            "verified",

            "identity_merged",

            "ownership_verified",

            "legal_entitlement_verified",

            "approved_for_search",

            "eligible_for_alert",

        ):

            with self.subTest(flag=key):

                self.assertIs(
                    item[key],
                    False,
                )

    def test_01_both_sources_extracted(self):

        _, calls = self.execute(
            self.primary,
            self.secondary,
        )

        self.assertEqual(calls, 2)

    def test_02_all_validators_available(self):

        result = self.dual()

        for key in VALIDATORS:

            self.assertIn(key, result)

    def test_03_pending_flags_disabled(self):

        result = self.dual()

        self.assertIs(
            result["organization_validation_pending"],
            False,
        )

        self.assertIs(
            result["legal_relationship_validation_pending"],
            False,
        )

    def test_04_party_agreement(self):

        self.assertEqual(

            self.dual()["party_validation"][
                "status_counts"
            ],

            {"CONSISTENT_UNVERIFIED": 1},

        )

    def test_05_organization_agreement(self):

        self.assertEqual(

            self.dual()["organization_validation"][
                "status_counts"
            ],

            {"CONSISTENT_UNVERIFIED": 1},

        )

    def test_06_relationship_agreement(self):

        self.assertEqual(

            self.dual()["legal_relationship_validation"][
                "status_counts"
            ],

            {"CONSISTENT_UNVERIFIED": 1},

        )

    def test_07_existing_comparison_contract(self):

        result = self.dual()

        self.assertEqual(

            result["comparison_count"],

            result["party_validation"][
                "comparison_count"
            ],

        )

        self.assertEqual(

            result["status_counts"],

            result["party_validation"][
                "status_counts"
            ],

        )

    def test_08_candidate_counts_preserved(self):

        result = self.dual()

        self.assertEqual(
            result["primary_candidate_count"],
            1,
        )

        self.assertEqual(
            result["secondary_candidate_count"],
            1,
        )

        self.assertEqual(
            result["total_candidate_occurrences"],
            2,
        )

    def test_09_module_counts_preserved(self):

        self.assertEqual(

            self.dual()["module_counts"],

            {

                "GENERAL": 0,

                "INHERITANCE": 0,

                "BANK": 0,

                "LEGAL_REPRESENTATIVE": 2,

            },

        )

    def test_10_primary_source_preserved(self):

        original = deepcopy(self.primary)

        result = self.dual()

        self.assertEqual(
            result["primary"],
            original,
        )

    def test_11_secondary_source_preserved(self):

        original = deepcopy(self.secondary)

        result = self.dual()

        self.assertEqual(
            result["secondary"],
            original,
        )

    def test_12_inputs_not_modified(self):

        primary = deepcopy(self.primary)

        secondary = deepcopy(self.secondary)

        self.dual()

        self.assertEqual(
            self.primary,
            primary,
        )

        self.assertEqual(
            self.secondary,
            secondary,
        )

    def test_13_direct_party_validator_equality(self):

        self.assertEqual(

            self.dual()["party_validation"],

            validate_party_candidates(

                self.primary["party_candidates"],

                self.secondary["party_candidates"],

            ),

        )

    def test_14_direct_organization_validator_equality(self):

        self.assertEqual(

            self.dual()["organization_validation"],

            validate_organization_candidates(

                self.primary["organization_candidates"],

                self.secondary["organization_candidates"],

            ),

        )

    def test_15_direct_relationship_validator_equality(self):

        self.assertEqual(

            self.dual()["legal_relationship_validation"],

            validate_legal_relationships(

                self.primary[
                    "legal_representative_associations"
                ],

                self.secondary[
                    "legal_representative_associations"
                ],

            ),

        )

    def test_16_missing_secondary_source(self):

        result, calls = self.execute(
            self.primary
        )

        self.assertEqual(calls, 1)

        self.assertIsNone(
            result["secondary"]
        )

        self.assertFalse(
            result["secondary_available"]
        )

    def test_17_missing_secondary_all_validators(self):

        result, _ = self.execute(
            self.primary
        )

        for key in VALIDATORS:

            with self.subTest(validator=key):

                self.assertEqual(

                    result[key]["status_counts"],

                    {"SECONDARY_NOT_AVAILABLE": 1},

                )

    def test_18_available_but_empty_secondary(self):

        secondary = deepcopy(
            self.secondary
        )

        for key in (

            "party_candidates",

            "organization_candidates",

            "legal_representative_associations",

        ):

            secondary[key] = []

        for key in (

            "candidate_count",

            "organization_count",

            "legal_representative_count",

        ):

            secondary[key] = 0

        secondary["module_counts"] = {

            key: 0

            for key in secondary["module_counts"]

        }

        result, calls = self.execute(

            self.primary,

            secondary,

        )

        self.assertEqual(calls, 2)

        self.assertTrue(
            result["secondary_available"]
        )

        for key in VALIDATORS:

            self.assertEqual(

                result[key]["status_counts"],

                {"PRIMARY_ONLY": 1},

            )

    def test_19_relationship_conflict(self):

        self.secondary[
            "legal_representative_associations"
        ][0]["relationship"] = "DAUGHTER"

        result = self.dual()

        self.assertEqual(

            result["legal_relationship_validation"][
                "status_counts"
            ],

            {"RELATIONSHIP_CONFLICT": 1},

        )

    def test_20_relationship_conflict_isolation(self):

        original = self.dual()

        self.secondary[
            "legal_representative_associations"
        ][0]["relationship"] = "DAUGHTER"

        updated = self.dual()

        for key in (

            "party_validation",

            "organization_validation",

        ):

            self.assertEqual(

                original[key],

                updated[key],

            )

    def test_21_no_automatic_relationship_selection(self):

        result = self.dual()

        for item in result[
            "legal_relationship_validation"
        ]["comparisons"]:

            self.assertIsNone(
                item["selected_relationship"]
            )

    def test_22_unified_root_safety(self):

        self.assert_safe(
            self.dual()
        )

    def test_23_all_validator_safety(self):

        result = self.dual()

        for key in VALIDATORS:

            self.assert_safe(
                result[key]
            )

            for item in result[key]["comparisons"]:

                self.assert_safe(item)

    def test_24_similarity_threshold_forwarding(self):

        threshold = 0.95

        result, _ = self.execute(

            self.primary,

            self.secondary,

            similarity_threshold=threshold,

        )

        self.assertEqual(

            result["party_validation"],

            validate_party_candidates(

                self.primary["party_candidates"],

                self.secondary["party_candidates"],

                similarity_threshold=threshold,

            ),

        )

        self.assertEqual(

            result["organization_validation"],

            validate_organization_candidates(

                self.primary["organization_candidates"],

                self.secondary["organization_candidates"],

                similarity_threshold=threshold,

            ),

        )

    def test_25_actual_empty_input_smoke_test(self):

        result = extract_unified_parties("")

        self.assertEqual(
            result["primary_candidate_count"],
            0,
        )

        for key in VALIDATORS:

            self.assertEqual(
                result[key]["comparison_count"],
                0,
            )

            self.assert_safe(
                result[key]
            )

        self.assert_safe(result)


if __name__ == "__main__":

    unittest.main()
