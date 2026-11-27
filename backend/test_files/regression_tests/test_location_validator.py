
import unittest

from notices.services.location_extractor import (
    extract_property_locations
)

from notices.services.location_validator import (
    canonicalize_location,
    validate_pin_candidates,
    validate_location_candidates
)


class LocationValidatorTests(unittest.TestCase):

    def validate(self, text):

        extracted = extract_property_locations(
            text
        )

        return validate_location_candidates(
            text,
            extracted
        )

    def test_01_bangalore_alias(self):

        self.assertEqual(

            canonicalize_location("Bangalore"),

            "Bengaluru"
        )

    def test_02_rural_district_alias(self):

        self.assertEqual(

            canonicalize_location("Bangalore Rural"),

            "Bengaluru Rural"
        )

    def test_03_urban_district_alias(self):

        self.assertEqual(

            canonicalize_location("Bangalore Urban"),

            "Bengaluru Urban"
        )

    def test_04_kannada_taluk(self):

        self.assertEqual(

            canonicalize_location("ಬೆಂಗಳೂರು ಉತ್ತರ"),

            "Bengaluru North"
        )

    def test_05_kannada_state(self):

        self.assertEqual(

            canonicalize_location("ಕರ್ನಾಟಕ"),

            "Karnataka"
        )

    def test_06_additional_excluded(self):

        self.assertIsNone(

            canonicalize_location("ADDITIONAL")
        )

    def test_07_court_excluded(self):

        self.assertIsNone(

            canonicalize_location("court")
        )

    def test_08_unknown_spelling_preserved(self):

        self.assertEqual(

            canonicalize_location("Benglauru Urban"),

            "Benglauru Urban"
        )

    def test_09_duplicate_district_aliases(self):

        result = self.validate(

            "Bangalore Rural District, "
            "Bengaluru Rural District"
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["district"],

            ["Bengaluru Rural"]
        )

    def test_10_english_pin(self):

        result = self.validate(

            "Bengaluru - 560079"
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["pin_code"],

            ["560079"]
        )

    def test_11_kannada_pin(self):

        result = self.validate(

            "ಬೆಂಗಳೂರು - ೫೬೦೦೭೯"
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["pin_code"],

            ["560079"]
        )

    def test_12_document_not_pin(self):

        result = self.validate(

            "ದಾಖಲೆ ಸಂ. 948333"
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["pin_code"],

            []
        )

    def test_13_document_evidence_preserved(self):

        result = validate_pin_candidates(

            "ದಾಖಲೆ ಸಂ. 948333"
        )

        self.assertEqual(

            result[0]["status"],

            "NON_ADDRESS_IDENTIFIER"
        )

    def test_14_decimal_not_pin(self):

        result = self.validate(

            "ಅಳತೆ 18.288037"
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["pin_code"],

            []
        )

    def test_15_unknown_number_not_pin(self):

        result = self.validate(

            "Reference 112026"
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["pin_code"],

            []
        )

    def test_16_date_fragment_not_pin(self):

        result = self.validate(

            "Date: 1/112026"
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["pin_code"],

            []
        )

    def test_17_multiple_address_pins(self):

        result = self.validate(

            "Bengaluru - 560001, "
            "Bengaluru - 560047"
        )

        self.assertEqual(

            result[
                "normalized_location_candidates"
            ]["pin_code"],

            ["560001", "560047"]
        )

    def test_18_multiple_villages_preserved(self):

        result = self.validate(

            "Kodathi Village, Gunjur Village"
        )

        self.assertIn(

            "village",

            result["ambiguous_location_fields"]
        )

    def test_19_property_address_not_inferred(self):

        result = self.validate(

            "Bengaluru - 560079"
        )

        self.assertIsNone(
            result["property_address"]
        )

    def test_20_manual_review_required(self):

        result = self.validate(

            "Bengaluru - 560079"
        )

        self.assertTrue(
            result["requires_review"]
        )

        self.assertFalse(
            result["verified"]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
