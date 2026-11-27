
import unittest

from notices.services.property_location_associator import (
    associate_property_locations
)


class PropertyLocationAssociatorTests(unittest.TestCase):

    def test_01_explicit_property_section(self):

        result = associate_property_locations(

            "Schedule property: Kodathi Village, "
            "Varthur Hobli, Bangalore South Taluk."
        )

        self.assertEqual(

            result["association_method"],

            "EXPLICIT_PROPERTY_SECTION"
        )

    def test_02_property_village(self):

        result = associate_property_locations(

            "Schedule property: Kodathi Village."
        )

        self.assertEqual(

            result["property_location_candidates"][
                "village"
            ],

            ["Kodathi"]
        )

    def test_03_party_address_excluded(self):

        result = associate_property_locations(

            "Residing at HSR Layout. "
            "Schedule property: Arkavathi Layout, "
            "Site No. 893."
        )

        self.assertEqual(

            result["property_location_candidates"][
                "layout"
            ],

            ["Arkavathi"]
        )

    def test_04_advocate_address_excluded(self):

        result = associate_property_locations(

            "Schedule property: Kodathi Village. "
            "Advocate office: HSR Layout."
        )

        self.assertNotIn(

            "HSR",

            result["property_location_candidates"].get(
                "layout",
                []
            )
        )

    def test_05_bank_address_excluded(self):

        result = associate_property_locations(

            "Registered office: Jayanagar Layout. "
            "Description of immovable property: "
            "Ramasagara Village."
        )

        self.assertEqual(

            result["property_location_candidates"][
                "village"
            ],

            ["Ramasagara"]
        )

    def test_06_kannada_property_layout(self):

        result = associate_property_locations(

            "ವಾಸ ನಂ 42 ನಂದಿನಿ ಲೇಔಟ್. "
            "ಸ್ವತ್ತಿನ ವಿವರ ಅರ್ಕಾವತಿ ಲೇಔಟ್ "
            "ಸೈಟ್ ನಂ. 893."
        )

        self.assertEqual(

            result["property_location_candidates"][
                "layout"
            ],

            ["ಅರ್ಕಾವತಿ"]
        )

    def test_07_kannada_village(self):

        result = associate_property_locations(

            "ಸ್ವತ್ತಿನ ವಿವರ ಮಲ್ಲತ್ತಹಳ್ಳಿ ಗ್ರಾಮ "
            "ಸರ್ವೆ ನಂ. 24/2."
        )

        self.assertEqual(

            result["property_location_candidates"][
                "village"
            ],

            ["ಮಲ್ಲತ್ತಹಳ್ಳಿ"]
        )

    def test_08_boundary_location_excluded(self):

        result = associate_property_locations(

            "Schedule property: Kodathi Village. "
            "Boundaries: Gunjur Village."
        )

        self.assertEqual(

            result["property_location_candidates"][
                "village"
            ],

            ["Kodathi"]
        )

    def test_09_identifier_fallback(self):

        result = associate_property_locations(

            "Kodathi Village, Survey No. 123/4."
        )

        self.assertEqual(

            result["association_method"],

            "IDENTIFIER_PROXIMITY"
        )

    def test_10_identifier_location_recovered(self):

        result = associate_property_locations(

            "Kodathi Village, Survey No. 123/4."
        )

        self.assertEqual(

            result["property_location_candidates"][
                "village"
            ],

            ["Kodathi"]
        )

    def test_11_no_property_context(self):

        result = associate_property_locations(

            "Advocate office: HSR Layout."
        )

        self.assertEqual(

            result["association_method"],

            "NO_PROPERTY_CONTEXT"
        )

        self.assertEqual(

            result["property_location_candidates"],

            {}
        )

    def test_12_multiple_villages_flagged(self):

        result = associate_property_locations(

            "Schedule property: Kodathi Village "
            "and Gunjur Village."
        )

        self.assertIn(

            "village",

            result["ambiguous_location_fields"]
        )

    def test_13_original_locations_preserved(self):

        result = associate_property_locations(

            "Residing at HSR Layout. "
            "Schedule property: Arkavathi Layout."
        )

        self.assertEqual(

            result["all_notice_location_candidates"][
                "layout"
            ],

            ["HSR", "Arkavathi"]
        )

    def test_14_normalized_taluk(self):

        result = associate_property_locations(

            "Schedule property: Bangalore South Taluk."
        )

        self.assertEqual(

            result["property_location_candidates"][
                "taluk"
            ],

            ["Bengaluru South"]
        )

    def test_15_no_verified_address(self):

        result = associate_property_locations(

            "Schedule property: Kodathi Village."
        )

        self.assertIsNone(
            result["property_address"]
        )

        self.assertFalse(
            result["verified"]
        )

        self.assertTrue(
            result["requires_review"]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
