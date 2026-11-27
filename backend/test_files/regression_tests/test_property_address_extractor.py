
import json
import unittest

from pathlib import Path

from notices.services.property_address_extractor import (
    extract_property_address_candidates
)


class PropertyAddressExtractorTests(unittest.TestCase):

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

        return extract_property_address_candidates(

            self.records[
                (page, region)
            ]["raw_text"]
        )

    def test_01_explicit_address(self):

        result = extract_property_address_candidates(

            "Schedule property: Site No. 1157 "
            "situated at Banashankari 6th Stage, "
            "4th Block, Bangalore measuring 54 sq metres."
        )

        self.assertEqual(

            result["property_address_candidates"],

            ["Banashankari 6th Stage, 4th Block, Bangalore"]
        )

    def test_02_stage_extraction(self):

        result = extract_property_address_candidates(

            "Schedule property: Banashankari 6th Stage."
        )

        self.assertEqual(

            result["address_components"]["stage"],

            ["6th Stage"]
        )

    def test_03_block_extraction(self):

        result = extract_property_address_candidates(

            "Schedule property: Banashankari 4th Block."
        )

        self.assertEqual(

            result["address_components"]["block"],

            ["4th Block"]
        )

    def test_04_cross_extraction(self):

        result = extract_property_address_candidates(

            "Schedule property: 17th D Cross, Bengaluru."
        )

        self.assertEqual(

            result["address_components"]["cross"],

            ["17th D Cross"]
        )

    def test_05_kannada_stage(self):

        result = extract_property_address_candidates(

            "ಸ್ವತ್ತಿನ ವಿವರ ಬಿನ್ನಮಂಗಲ 2ನೇ ಹಂತ"
        )

        self.assertEqual(

            result["address_components"]["kannada_stage"],

            ["2ನೇ ಹಂತ"]
        )

    def test_06_kannada_block(self):

        result = extract_property_address_candidates(

            "ಸ್ವತ್ತಿನ ವಿವರ ಅರ್ಕಾವತಿ ಲೇಔಟ್ 8ನೇ ಬ್ಲಾಕ್"
        )

        self.assertEqual(

            result["address_components"]["kannada_block"],

            ["8ನೇ ಬ್ಲಾಕ್"]
        )

    def test_07_kannada_cross(self):

        result = extract_property_address_candidates(

            "ಸ್ವತ್ತಿನ ವಿವರ 17ನೇ ಡಿ ಕ್ರಾಸ್"
        )

        self.assertEqual(

            result["address_components"]["kannada_cross"],

            ["17ನೇ ಡಿ ಕ್ರಾಸ್"]
        )

    def test_08_advocate_address_exclusion(self):

        result = extract_property_address_candidates(

            "Schedule property situated at Seegehalli, "
            "Bengaluru. Advocate office: HSR Layout."
        )

        combined = " ".join(

            result["property_address_candidates"]
        )

        self.assertNotIn(
            "HSR",
            combined
        )

    def test_09_residential_address_exclusion(self):

        result = extract_property_address_candidates(

            "Residing at HSR Layout. "
            "Schedule property situated at Seegehalli."
        )

        self.assertEqual(

            result["property_address_candidates"],

            ["Seegehalli"]
        )

    def test_10_real_banashankari_address(self):

        result = self.real_notice(11, 3)

        combined = " ".join(

            result["property_address_candidates"]
        )

        self.assertIn(
            "Banashankari",
            combined
        )

    def test_11_real_banashankari_stage(self):

        result = self.real_notice(11, 3)

        self.assertIn(

            "6th Stage",

            result["address_components"]["stage"]
        )

    def test_12_real_banashankari_block(self):

        result = self.real_notice(11, 3)

        self.assertIn(

            "4th Block",

            result["address_components"]["block"]
        )

    def test_13_real_seegehalli_address(self):

        result = self.real_notice(10, 14)

        combined = " ".join(

            result["property_address_candidates"]
        )

        self.assertIn(
            "Seegehalli",
            combined
        )

        self.assertNotIn(
            "HSR",
            combined
        )

    def test_14_real_kannada_stage(self):

        result = self.real_notice(7, 3)

        self.assertIn(

            "2ನೇ ಹಂತ",

            result["address_components"]["kannada_stage"]
        )

    def test_15_real_kannada_address(self):

        result = self.real_notice(7, 3)

        combined = " ".join(

            result["property_address_candidates"]
        )

        self.assertIn(
            "ಬಿನ್ನಮಂಗಲ",
            combined
        )

        self.assertNotIn(
            "ಡೊಮ್ಲೂರು",
            combined
        )

    def test_16_no_property_context(self):

        result = extract_property_address_candidates(

            "Advocate office: HSR Layout."
        )

        self.assertEqual(

            result["property_address_candidates"],

            []
        )

    def test_17_manual_review_safety(self):

        result = extract_property_address_candidates(

            "Schedule property situated at Seegehalli."
        )

        self.assertTrue(
            result["requires_review"]
        )

        self.assertFalse(
            result["verified"]
        )

        self.assertFalse(
            result["eligible_for_alert"]
        )

        self.assertIsNone(
            result["property_address"]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
