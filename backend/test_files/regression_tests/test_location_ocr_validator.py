
import json
import unittest

from pathlib import Path

from notices.services.location_ocr_validator import (
    validate_property_locations,
    compare_location_candidates
)


class LocationOCRValidatorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        data = json.loads(

            Path(
                "test_files/integrated_policy_test/results.json"
            ).read_text(encoding="utf-8")
        )

        cls.records = {

            (
                item["page_number"],
                item["region_number"]
            ): item["result"]

            for item in data["results"]
        }

    def real_notice(self, page, region):

        notice = self.records[
            (page, region)
        ]

        return validate_property_locations(

            notice["raw_text"],

            notice.get("secondary_raw_text")
        )

    def test_01_matching_location(self):

        result = compare_location_candidates(

            ["Kodathi"],

            ["Kodathi"]
        )

        self.assertEqual(

            result["status"],

            "CONSISTENT_UNVERIFIED"
        )

    def test_02_case_insensitive_comparison(self):

        result = compare_location_candidates(

            ["RAMASAGARA"],

            ["Ramasagara"]
        )

        self.assertEqual(

            result["status"],

            "CONSISTENT_UNVERIFIED"
        )

    def test_03_location_alias_comparison(self):

        result = compare_location_candidates(

            ["Bangalore South"],

            ["Bengaluru South"],

            use_aliases=True
        )

        self.assertEqual(

            result["status"],

            "CONSISTENT_UNVERIFIED"
        )

    def test_04_kannada_alias_comparison(self):

        result = compare_location_candidates(

            ["ಬೆಂಗಳೂರು ಉತ್ತರ"],

            ["Bengaluru North"],

            use_aliases=True
        )

        self.assertEqual(

            result["status"],

            "CONSISTENT_UNVERIFIED"
        )

    def test_05_conflicting_villages(self):

        result = compare_location_candidates(

            ["Kodathi"],

            ["Gunjur"]
        )

        self.assertEqual(

            result["status"],

            "CONFLICT"
        )

        self.assertIsNone(
            result["selected_value"]
        )

    def test_06_single_source(self):

        result = compare_location_candidates(

            ["Varthur"],

            []
        )

        self.assertEqual(

            result["status"],

            "SINGLE_SOURCE"
        )

    def test_07_missing_secondary(self):

        result = compare_location_candidates(

            ["Kodathi"],

            [],

            secondary_available=False
        )

        self.assertEqual(

            result["status"],

            "SECONDARY_NOT_AVAILABLE"
        )

    def test_08_multiple_candidates(self):

        result = compare_location_candidates(

            ["Kodathi", "Gunjur"],

            ["Gunjur", "Kodathi"]
        )

        self.assertEqual(

            result["status"],

            "MULTIPLE_CANDIDATES"
        )

    def test_09_missing_location(self):

        result = compare_location_candidates(
            [],
            []
        )

        self.assertEqual(

            result["status"],

            "NOT_FOUND"
        )

    def test_10_matching_property_address(self):

        text = (

            "Schedule property situated at "

            "Banashankari 6th Stage, "

            "4th Block, Bangalore."
        )

        result = validate_property_locations(
            text,
            text
        )

        self.assertEqual(

            result["validations"][
                "property_address"
            ]["status"],

            "CONSISTENT_UNVERIFIED"
        )

    def test_11_conflicting_addresses(self):

        result = validate_property_locations(

            "Schedule property situated at Seegehalli.",

            "Schedule property situated at Kodathi."
        )

        self.assertIn(

            "property_address",

            result["conflicting_fields"]
        )

    def test_12_address_not_confirmed(self):

        text = (

            "Schedule property situated at Seegehalli."
        )

        result = validate_property_locations(
            text,
            text
        )

        self.assertIsNone(
            result["property_address"]
        )

        self.assertFalse(
            result["verified"]
        )

    def test_13_original_spelling_preserved(self):

        result = compare_location_candidates(

            ["RAMASAGARA"],

            ["Ramasagara"]
        )

        self.assertEqual(

            result[
                "original_source_a_candidates"
            ],

            ["RAMASAGARA"]
        )

    def test_14_real_lost_will_location(self):

        result = self.real_notice(10, 11)

        self.assertEqual(

            result["agreed_location_candidates"].get(
                "layout"
            ),

            "ಅರ್ಕಾವತಿ"
        )

    def test_15_real_property_village_association(self):

        result = self.real_notice(10, 1)

        comparison = result["validations"]["village"]

        self.assertEqual(
            comparison["status"],
            "CONSISTENT_UNVERIFIED"
        )

        self.assertEqual(
            comparison["original_source_a_candidates"],
            ["ಮಲ್ಲತ್ತಹಳ್ಳಿ"]
        )

        self.assertEqual(
            comparison["original_source_b_candidates"],
            ["ಮಲ್ಲತ್ತಹಳ್ಳಿ"]
        )

        self.assertEqual(
            result["agreed_location_candidates"].get(
                "village"
            ),
            "ಮಲ್ಲತ್ತಹಳ್ಳಿ"
        )

        self.assertNotIn(
            "village",
            result["multiple_candidate_fields"]
        )

        self.assertFalse(
            comparison["verified"]
        )

        self.assertFalse(
            comparison["approved_for_search"]
        )

        self.assertTrue(
            result["requires_review"]
        )

        self.assertFalse(
            result["eligible_for_alert"]
        )

    def test_16_real_advocate_exclusion(self):

        result = self.real_notice(10, 14)

        candidates = result[
            "agreed_location_candidates"
        ]

        self.assertNotEqual(
            candidates.get("layout"),
            "HSR"
        )

        self.assertNotEqual(
            candidates.get("pin_code"),
            "560102"
        )

    def test_17_real_banashankari_address(self):

        result = self.real_notice(11, 3)

        address = result[
            "primary_result"
        ]["property_address_candidates"]

        self.assertIn(

            "Banashankari",

            " ".join(address)
        )

    def test_18_real_court_missing_secondary(self):

        result = self.real_notice(7, 1)

        self.assertFalse(
            result["secondary_available"]
        )

        self.assertIn(

            "taluk",

            result["secondary_unavailable_fields"]
        )

    def test_19_no_automatic_search_approval(self):

        text = "Schedule property: Kodathi Village."

        result = validate_property_locations(
            text,
            text
        )

        self.assertFalse(
            result["approved_for_search"]
        )

    def test_20_no_automatic_alerts(self):

        text = "Schedule property: Kodathi Village."

        result = validate_property_locations(
            text,
            text
        )

        self.assertFalse(
            result["eligible_for_alert"]
        )

        self.assertTrue(
            result["requires_review"]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
