"""
Permanent regression tests for legal relationship
dual-OCR validation and evidence preservation.
"""

import unittest
from copy import deepcopy

from notices.services.legal_relationship_ocr_validator import (
    validate_legal_relationships,
)


def association(**changes):

    item = {

        "deceased_person": "Gopal",
        "deceased_entry_number": "23",
        "representative_name": "Kamalamma",
        "representative_entry_number": "23(a)",
        "respondent_number": "24",
        "relationship": "WIFE",
        "relationship_uncertain": False,
        "relationship_conflict": False,
        "identity_conflict": False,
        "source_text": "Kamalamma W/o Late Gopal",
        "parent_source_text": "Gopal represented by legal representatives",
        "requires_review": True,
        "verified": False,
        "identity_merged": False,
        "ownership_verified": False,
        "legal_entitlement_verified": False,
        "approved_for_search": False,
        "eligible_for_alert": False,

    }

    item.update(changes)

    return item


class LegalRelationshipOCRValidatorTests(
    unittest.TestCase
):

    def compare(self, primary, secondary=None):

        return validate_legal_relationships(
            primary,
            secondary,
        )

    def status(self, primary, secondary=None):

        return self.compare(
            primary,
            secondary,
        )["comparisons"][0]["status"]

    def assert_safe(self, item):

        self.assertIs(
            item["requires_review"],
            True,
        )

        for key in (

            "verified",
            "identity_merged",
            "relationship_verified",
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

    def test_01_empty_input(self):

        result = self.compare([])

        self.assertEqual(
            result["comparison_count"],
            0,
        )

        self.assertEqual(
            result["status_counts"],
            {},
        )

    def test_02_secondary_not_available(self):

        result = self.compare(
            [association()]
        )

        self.assertFalse(
            result["secondary_available"]
        )

        self.assertEqual(
            result["status_counts"],
            {"SECONDARY_NOT_AVAILABLE": 1},
        )

    def test_03_primary_only(self):

        self.assertEqual(
            self.status([association()], []),
            "PRIMARY_ONLY",
        )

    def test_04_secondary_only(self):

        self.assertEqual(
            self.status([], [association()]),
            "SECONDARY_ONLY",
        )

    def test_05_consistent_unverified(self):

        self.assertEqual(
            self.status(
                [association()],
                [association()],
            ),
            "CONSISTENT_UNVERIFIED",
        )

    def test_06_name_normalization(self):

        self.assertEqual(
            self.status(
                [association()],
                [association(
                    deceased_person=" GOPAL ",
                    representative_name=" KAMALAMMA ",
                )],
            ),
            "CONSISTENT_UNVERIFIED",
        )

    def test_07_court_entry_normalization(self):

        self.assertEqual(
            self.status(
                [association()],
                [association(
                    representative_entry_number="23 (A)"
                )],
            ),
            "CONSISTENT_UNVERIFIED",
        )

    def test_08_relationship_conflict(self):

        self.assertEqual(
            self.status(
                [association()],
                [association(
                    relationship="DAUGHTER"
                )],
            ),
            "RELATIONSHIP_CONFLICT",
        )

    def test_09_missing_secondary_relationship(self):

        self.assertEqual(
            self.status(
                [association()],
                [association(
                    relationship=None
                )],
            ),
            "RELATIONSHIP_INCOMPLETE",
        )

    def test_10_both_relationships_unknown(self):

        self.assertEqual(
            self.status(
                [association(relationship=None)],
                [association(relationship=None)],
            ),
            "RELATIONSHIP_INCOMPLETE",
        )

    def test_11_uncertain_relationship(self):

        self.assertEqual(
            self.status(
                [association()],
                [association(
                    relationship_uncertain=True
                )],
            ),
            "RELATIONSHIP_INCOMPLETE",
        )

    def test_12_existing_relationship_conflict(self):

        self.assertEqual(
            self.status(
                [association(
                    relationship_conflict=True
                )],
                [association()],
            ),
            "RELATIONSHIP_CONFLICT",
        )

    def test_13_multiple_relationship_candidates(self):

        self.assertEqual(
            self.status(
                [association(
                    relationship_candidates=[
                        "WIFE",
                        "DAUGHTER",
                    ]
                )],
                [association()],
            ),
            "RELATIONSHIP_CONFLICT",
        )

    def test_14_respondent_number_conflict(self):

        result = self.compare(
            [association()],
            [association(
                respondent_number="25"
            )],
        )

        group = result["comparisons"][0]

        self.assertTrue(
            group["respondent_number_conflict"]
        )

        self.assertEqual(
            group["status"],
            "IDENTITY_CONFLICT",
        )

    def test_15_existing_identity_conflict(self):

        self.assertEqual(
            self.status(
                [association(
                    identity_conflict=True
                )],
                [association()],
            ),
            "IDENTITY_CONFLICT",
        )

    def test_16_same_entry_conflicting_names(self):

        result = self.compare(
            [association()],
            [association(
                representative_name="Manjula"
            )],
        )

        self.assertEqual(
            result["court_entry_conflict_count"],
            1,
        )

        self.assertEqual(
            result["identity_conflict_count"],
            2,
        )

    def test_17_same_name_different_entries(self):

        result = self.compare(

            [

                association(),

                association(
                    representative_entry_number="23(b)",
                    respondent_number="25",
                ),

            ],

            [],

        )

        self.assertEqual(
            result["comparison_count"],
            2,
        )

        self.assertEqual(
            result["court_entry_conflict_count"],
            0,
        )

    def test_18_identity_conflict_priority(self):

        result = self.compare(

            [association()],

            [association(
                respondent_number="25",
                relationship="DAUGHTER",
            )],

        )

        group = result["comparisons"][0]

        self.assertEqual(
            group["status"],
            "IDENTITY_CONFLICT",
        )

        self.assertTrue(
            group["relationship_conflict"]
        )

    def test_19_primary_unicode_evidence(self):

        primary = [

            association(
                source_text="Original evidence\u200c",
                parent_source_text="Parent evidence\u200c",
            )

        ]

        result = self.compare(
            primary,
            [association()],
        )

        self.assertEqual(

            result["comparisons"][0][
                "primary_associations"
            ],

            primary,

        )

    def test_20_secondary_unicode_evidence(self):

        secondary = [

            association(
                source_text="Secondary evidence\u200c"
            )

        ]

        result = self.compare(
            [association()],
            secondary,
        )

        self.assertEqual(

            result["comparisons"][0][
                "secondary_associations"
            ],

            secondary,

        )

    def test_21_input_records_unchanged(self):

        primary = [association()]

        secondary = [association()]

        original_primary = deepcopy(primary)

        original_secondary = deepcopy(secondary)

        self.compare(primary, secondary)

        self.assertEqual(
            primary,
            original_primary,
        )

        self.assertEqual(
            secondary,
            original_secondary,
        )

    def test_22_deep_copy_isolation(self):

        primary = [association()]

        original = deepcopy(primary)

        result = self.compare(primary)

        result["comparisons"][0][
            "primary_associations"
        ][0]["source_text"] = "Modified output"

        self.assertEqual(
            primary,
            original,
        )

    def test_23_no_automatic_relationship_selection(self):

        result = self.compare(
            [association()],
            [association()],
        )

        self.assertIsNone(
            result["comparisons"][0][
                "selected_relationship"
            ]
        )

    def test_24_root_safety(self):

        self.assert_safe(
            self.compare(
                [association()],
                [association()],
            )
        )

    def test_25_comparison_safety(self):

        result = self.compare(
            [association()],
            [association()],
        )

        for item in result["comparisons"]:

            self.assert_safe(item)

    def test_26_conflict_safety(self):

        result = self.compare(
            [association()],
            [association(
                representative_name="Manjula"
            )],
        )

        self.assertEqual(
            result["court_entry_conflict_count"],
            1,
        )

        for item in result["court_entry_conflicts"]:

            self.assert_safe(item)

        for item in result["comparisons"]:

            self.assert_safe(item)

    def test_27_invalid_deceased_name_rejected(self):

        with self.assertRaises(ValueError):

            self.compare([
                association(
                    deceased_person=""
                )
            ])

    def test_28_duplicate_occurrences_preserved(self):

        result = self.compare(

            [
                association(),
                association(),
            ],

            [association()],

        )

        self.assertEqual(
            result["comparison_count"],
            1,
        )

        self.assertEqual(

            result["comparisons"][0][
                "primary_occurrence_count"
            ],

            2,

        )

    def test_29_invalid_representative_name_rejected(self):

        with self.assertRaises(ValueError):

            self.compare([
                association(
                    representative_name=""
                )
            ])

    def test_30_unknown_relationship_without_secondary(self):

        result = self.compare([

            association(
                representative_name="Manjula",
                representative_entry_number="23(b)",
                respondent_number="25",
                relationship=None,
                relationship_uncertain=True,
            )

        ])

        group = result["comparisons"][0]

        self.assertEqual(
            group["status"],
            "SECONDARY_NOT_AVAILABLE",
        )

        self.assertEqual(
            group["relationship_candidates"],
            [],
        )

        self.assertTrue(
            group["relationship_incomplete"]
        )

        self.assertIsNone(
            group["selected_relationship"]
        )

        self.assert_safe(group)


if __name__ == "__main__":

    unittest.main()
