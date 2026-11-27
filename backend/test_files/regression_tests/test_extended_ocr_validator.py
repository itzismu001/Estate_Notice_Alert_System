
import unittest

from notices.services.ocr_validator import (
    compare_ocr_values,
    compare_identifier_values,
    validate_extracted_fields
)

from notices.services.kannada_field_extractor import (
    extract_kannada_fields
)

from notices.services.multilingual_processor import (
    build_review_fields
)


class ExtendedOCRValidatorTests(unittest.TestCase):

    def validate(self, text_a, text_b):

        fields_a = extract_kannada_fields(
            text_a
        )

        fields_b = extract_kannada_fields(
            text_b
        )

        validation = validate_extracted_fields(
            fields_a,
            fields_b
        )

        consolidated = build_review_fields(
            fields_a,
            validation
        )

        return validation, consolidated

    # ==============================================
    # EXISTING VALIDATION REGRESSION
    # ==============================================

    def test_01_matching_identifier(self):

        result = compare_ocr_values(
            ["123/4"],
            ["123/4"]
        )

        self.assertEqual(
            result["status"],
            "CONSISTENT_UNVERIFIED"
        )

    def test_02_conflicting_identifier(self):

        result = compare_ocr_values(
            ["123/4"],
            ["123/5"]
        )

        self.assertEqual(
            result["status"],
            "CONFLICT"
        )

    def test_03_single_source(self):

        result = compare_ocr_values(
            ["123/4"],
            []
        )

        self.assertEqual(
            result["status"],
            "SINGLE_SOURCE"
        )

    def test_04_multiple_candidates(self):

        result = compare_ocr_values(
            ["123/4", "123/5"],
            ["123/5", "123/4"]
        )

        self.assertEqual(
            result["status"],
            "MULTIPLE_CANDIDATES"
        )

    def test_05_not_found(self):

        result = compare_ocr_values(
            [],
            []
        )

        self.assertEqual(
            result["status"],
            "NOT_FOUND"
        )

    def test_06_numeral_normalization(self):

        result = compare_ocr_values(
            ["೧೨೩/೪"],
            ["123/4"]
        )

        self.assertEqual(
            result["status"],
            "CONSISTENT_UNVERIFIED"
        )

    # ==============================================
    # ASSESSMENT NUMBER VALIDATION
    # ==============================================

    def test_07_assessment_agreement(self):

        validation, fields = self.validate(

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/104",

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/104"
        )

        self.assertEqual(

            validation["validations"][
                "assessment_numbers"
            ]["status"],

            "CONSISTENT_UNVERIFIED"
        )

        self.assertEqual(
            fields["assessment_number"],
            "27/104"
        )

    def test_08_assessment_conflict(self):

        validation, fields = self.validate(

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/104",

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/109"
        )

        self.assertIn(

            "assessment_numbers",

            validation["conflicting_fields"]
        )

        self.assertIsNone(
            fields["assessment_number"]
        )

    def test_09_assessment_single_source(self):

        validation, fields = self.validate(

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/104",

            "ಸಾರ್ವಜನಿಕ ಪ್ರಕಟಣೆ"
        )

        self.assertIn(

            "assessment_numbers",

            validation["single_source_fields"]
        )

        self.assertEqual(
            fields["assessment_numbers"],
            []
        )

    def test_10_assessment_evidence_preserved(self):

        validation, fields = self.validate(

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/104",

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/109"
        )

        self.assertEqual(

            validation["validations"][
                "assessment_numbers"
            ]["all_candidates"],

            ["27/104", "27/109"]
        )

    def test_11_assessment_without_secondary(self):

        original = extract_kannada_fields(

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/104"
        )

        fields = build_review_fields(
            original,
            None
        )

        self.assertIsNone(
            fields["assessment_number"]
        )

    # ==============================================
    # INVALID IDENTIFIER VALIDATION
    # ==============================================

    def test_12_matching_incomplete_identifiers(self):

        result = compare_identifier_values(
            ["90/"],
            ["90/"]
        )

        self.assertEqual(
            result["status"],
            "INVALID_IDENTIFIER"
        )

        self.assertIsNone(
            result["selected_value"]
        )

    def test_13_invalid_parser_evidence(self):

        validation, fields = self.validate(

            "ಸರ್ವೆ ನಂ. 90/",

            "ಸರ್ವೆ ನಂ. 90/"
        )

        self.assertIn(

            "survey_numbers",

            validation["invalid_fields"]
        )

    def test_14_invalid_and_valid_conflict(self):

        validation, fields = self.validate(

            "ಸರ್ವೆ ನಂ. 90/",

            "ಸರ್ವೆ ನಂ. 90/2"
        )

        self.assertEqual(

            validation["validations"][
                "survey_numbers"
            ]["status"],

            "INVALID_IDENTIFIER"
        )

        self.assertIsNone(
            fields["survey_number"]
        )

    def test_15_invalid_evidence_preserved(self):

        validation, fields = self.validate(

            "ಸರ್ವೆ ನಂ. 90/",

            "ಸರ್ವೆ ನಂ. 90/2"
        )

        self.assertIn(

            "90/",

            validation["validations"][
                "survey_numbers"
            ]["invalid_candidates"]
        )

    def test_16_repeated_separator(self):

        result = compare_identifier_values(
            ["90//2"],
            ["90//2"]
        )

        self.assertEqual(
            result["status"],
            "INVALID_IDENTIFIER"
        )

    def test_17_invalid_single_ocr_blocked(self):

        original = extract_kannada_fields(

            "ಸರ್ವೆ ನಂ. 90/ ಮತ್ತು ಸರ್ವೆ ನಂ. 90"
        )

        fields = build_review_fields(
            original,
            None
        )

        self.assertEqual(
            fields["survey_numbers"],
            []
        )

    # ==============================================
    # BOUNDARY VALIDATION
    # ==============================================

    def test_18_boundary_separation(self):

        validation, fields = self.validate(

            "ಸೈಟ್ ನಂ. 893 ಚಕ್ಕುಬಂದಿ ಸೈಟ್ ನಂ. 894",

            "ಸೈಟ್ ನಂ. 893 ಚಕ್ಕುಬಂದಿ ಸೈಟ್ ನಂ. 894"
        )

        self.assertEqual(
            fields["site_numbers"],
            ["893"]
        )

        self.assertEqual(

            validation["boundary_validations"][
                "site_numbers"
            ]["selected_value"],

            "894"
        )

    def test_19_boundary_conflict(self):

        validation, fields = self.validate(

            "ಸೈಟ್ ನಂ. 893 ಚಕ್ಕುಬಂದಿ ಸೈಟ್ ನಂ. 894",

            "ಸೈಟ್ ನಂ. 893 ಚಕ್ಕುಬಂದಿ ಸೈಟ್ ನಂ. 895"
        )

        self.assertEqual(

            validation["boundary_validations"][
                "site_numbers"
            ]["status"],

            "CONFLICT"
        )

        self.assertEqual(
            fields["site_number"],
            "893"
        )

    def test_20_boundary_invalid_identifier(self):

        validation, fields = self.validate(

            "ಸೈಟ್ ನಂ. 893 ಚಕ್ಕುಬಂದಿ ಸರ್ವೆ ನಂ. 90/",

            "ಸೈಟ್ ನಂ. 893 ಚಕ್ಕುಬಂದಿ ಸರ್ವೆ ನಂ. 90/"
        )

        self.assertEqual(

            validation["boundary_validations"][
                "survey_numbers"
            ]["status"],

            "INVALID_IDENTIFIER"
        )

    # ==============================================
    # MANUAL REVIEW SAFETY
    # ==============================================

    def test_21_unverified_agreement(self):

        validation, fields = self.validate(

            "ಸರ್ವೆ ನಂ. 123/4",

            "ಸರ್ವೆ ನಂ. 123/4"
        )

        self.assertFalse(
            validation["verified"]
        )

        self.assertFalse(
            fields["verified"]
        )

        self.assertTrue(
            fields["requires_review"]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
