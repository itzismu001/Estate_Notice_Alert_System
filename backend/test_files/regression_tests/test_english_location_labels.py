import unittest

from notices.services.location_extractor import (
    extract_property_locations,
)


class EnglishLocationLabelTests(unittest.TestCase):

    def get_candidates(self, text):
        return extract_property_locations(
            text
        )["location_candidates"]

    def test_prefix_without_colon(self):
        result = self.get_candidates(
            "Village Ramanagara\n"
            "District Bengaluru"
        )

        self.assertEqual(
            result["village"], ["Ramanagara"]
        )
        self.assertEqual(
            result["district"], ["Bengaluru"]
        )

    def test_multiword_district(self):
        result = self.get_candidates(
            "Village Devanahalli\n"
            "District Bengaluru Rural"
        )

        self.assertEqual(
            result["village"], ["Devanahalli"]
        )
        self.assertEqual(
            result["district"], ["Bengaluru Rural"]
        )

    def test_prefix_with_colon(self):
        result = self.get_candidates(
            "Village: Devanahalli\n"
            "District: Bengaluru Rural"
        )

        self.assertEqual(
            result["village"], ["Devanahalli"]
        )
        self.assertEqual(
            result["district"], ["Bengaluru Rural"]
        )

    def test_english_suffix(self):
        result = self.get_candidates(
            "Devanahalli village, "
            "Bengaluru Rural district"
        )

        self.assertEqual(
            result["village"], ["Devanahalli"]
        )
        self.assertEqual(
            result["district"], ["Bengaluru Rural"]
        )

    def test_normalized_single_line(self):
        result = self.get_candidates(
            "Village Devanahalli "
            "District Bengaluru Rural "
            "Raise objections within 14 days."
        )

        self.assertEqual(
            result["village"], ["Devanahalli"]
        )
        self.assertEqual(
            result["district"], ["Bengaluru Rural"]
        )

    def test_kannada_suffix_preserved(self):
        result = self.get_candidates(
            "ದೇವನಹಳ್ಳಿ ಗ್ರಾಮ, "
            "ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ ಜಿಲ್ಲೆ"
        )

        self.assertIn(
            "ದೇವನಹಳ್ಳಿ", result["village"]
        )
        self.assertIn(
            "ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ",
            result["district"]
        )


if __name__ == "__main__":
    unittest.main()
