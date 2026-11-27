
import json
import unittest

from pathlib import Path

from notices.services.location_extractor import (
    extract_property_locations
)

from notices.services.location_validator import (
    validate_location_candidates
)

from notices.services.property_location_associator import (
    associate_property_locations
)


class LocationCorrectionTests(unittest.TestCase):

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

    def locations(self, text):

        return extract_property_locations(
            text
        )["location_candidates"]

    def real_association(self, page, region):

        text = self.records[
            (page, region)
        ]["raw_text"]

        return associate_property_locations(
            text
        )["property_location_candidates"]

    def test_01_damaged_hobli_label(self):

        result = self.locations(
            "ಯಶವಂತಪುರ ಹೋಬಳ."
        )

        self.assertEqual(

            result["hobli"],

            ["ಯಶವಂತಪುರ"]
        )

    def test_02_alternate_hobli_label(self):

        result = self.locations(
            "ಯಶವಂತಪುರ ಹೋಬಖಳ."
        )

        self.assertEqual(

            result["hobli"],

            ["ಯಶವಂತಪುರ"]
        )

    def test_03_village_suffix(self):

        result = self.locations(
            "ಕಾಂಚನಾಯನಹಳ್ಳಿ ಗ್ರಾಮದಲ್ಲಿರುವ"
        )

        self.assertEqual(

            result["village"],

            ["ಕಾಂಚನಾಯನಹಳ್ಳಿ"]
        )

    def test_04_rural_district(self):

        text = "ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ ಜಿಲ್ಲೆ"

        result = validate_location_candidates(

            text,

            extract_property_locations(text)
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["district"],

            ["Bengaluru Rural"]
        )

    def test_05_urban_district(self):

        text = "ಬೆಂಗಳೂರು ನಗರ ಜಿಲ್ಲೆ"

        result = validate_location_candidates(

            text,

            extract_property_locations(text)
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["district"],

            ["Bengaluru Urban"]
        )

    def test_06_panchayat_not_village(self):

        result = self.locations(
            "ಸೋಲಿಕೆರೆ ಗ್ರಾಮ ಪಂಚಾಯತ್"
        )

        self.assertEqual(
            result["village"],
            []
        )

        self.assertEqual(

            result["gram_panchayat"],

            ["ಸೋಲಿಕೆರೆ"]
        )

    def test_07_real_residential_layout_excluded(self):

        result = self.real_association(7, 3)

        self.assertNotIn(

            "ಡೊಮ್ಲೂರು",

            result.get("layout", [])
        )

    def test_08_real_advocate_layout_excluded(self):

        result = self.real_association(10, 14)

        self.assertNotIn(

            "HSR",

            result.get("layout", [])
        )

    def test_09_real_advocate_pin_excluded(self):

        result = self.real_association(10, 14)

        self.assertNotIn(

            "560102",

            result.get("pin_code", [])
        )

    def test_10_real_property_hobli_preserved(self):

        result = self.real_association(10, 14)

        self.assertIn(

            "Bidarahalli",

            result.get("hobli", [])
        )

    def test_11_real_kannada_hobli_recovered(self):

        result = self.real_association(10, 1)

        self.assertIn(

            "ಯಶವಂತಪುರ",

            result.get("hobli", [])
        )

    def test_12_real_panchayat_not_village(self):

        result = self.real_association(10, 20)

        self.assertNotIn(

            "ಸೋಲಿಕೆರೆ",

            result.get("village", [])
        )

        self.assertIn(

            "ಕೊಮ್ಮಘಟ್ಟ",

            result.get("village", [])
        )

    def test_13_real_village_recovered(self):

        result = self.real_association(11, 13)

        self.assertIn(

            "ಕಾಂಚನಾಯನಹಳ್ಳಿ",

            result.get("village", [])
        )

    def test_14_lost_will_layout_preserved(self):

        result = self.real_association(10, 11)

        self.assertEqual(

            result.get("layout", []),

            ["ಅರ್ಕಾವತಿ"]
        )

    def test_15_location_remains_unverified(self):

        result = associate_property_locations(

            "Schedule property: Kodathi Village."
        )

        self.assertFalse(
            result["verified"]
        )

        self.assertTrue(
            result["requires_review"]
        )

        self.assertIsNone(
            result["property_address"]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
