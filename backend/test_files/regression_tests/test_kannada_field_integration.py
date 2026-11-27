
import json
import unittest

from pathlib import Path

from notices.services.kannada_field_extractor import (
    extract_kannada_fields
)

from notices.services.multilingual_processor import (
    process_multilingual_notice
)


class KannadaFieldIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        path = Path(
            "test_files/integrated_policy_test/results.json"
        )

        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        cls.records = {

            (
                item["page_number"],
                item["region_number"]
            ): item["result"]

            for item in data["results"]
        }

    def real_fields(self, page, region):

        return extract_kannada_fields(

            self.records[
                (page, region)
            ]["raw_text"]
        )

    # ==============================================
    # EXISTING EXTRACTION REGRESSION
    # ==============================================

    def test_01_existing_site(self):

        fields = self.real_fields(7, 3)

        self.assertEqual(
            fields["site_number"],
            "1006/8"
        )

    def test_02_existing_document(self):

        fields = self.real_fields(7, 3)

        self.assertEqual(
            fields["document_numbers"],
            ["1823/1984-85"]
        )

    def test_03_existing_property_area(self):

        fields = self.real_fields(7, 3)

        self.assertEqual(
            fields["property_area"],
            "1200"
        )

        self.assertEqual(
            fields["property_area_unit"],
            "square_feet"
        )

    def test_04_existing_deadline(self):

        fields = self.real_fields(7, 3)

        self.assertEqual(
            fields["response_deadline"],
            "7"
        )

        self.assertEqual(
            fields["response_deadline_unit"],
            "day"
        )

    # ==============================================
    # LOST-WILL NOTICE
    # ==============================================

    def test_05_lost_will_survey(self):

        fields = self.real_fields(10, 11)

        self.assertEqual(
            fields["survey_number"],
            "34/2"
        )

    def test_06_lost_will_site(self):

        fields = self.real_fields(10, 11)

        self.assertEqual(
            fields["site_number"],
            "893"
        )

    def test_07_lost_will_boundary(self):

        fields = self.real_fields(10, 11)

        self.assertEqual(

            fields["boundary_identifiers"][
                "site_numbers"
            ],

            ["56", "802", "894"]
        )

    def test_08_boundary_not_subject(self):

        fields = self.real_fields(10, 11)

        self.assertEqual(
            fields["site_numbers"],
            ["893"]
        )

    # ==============================================
    # INVALID IDENTIFIER SAFETY
    # ==============================================

    def test_09_truncated_survey(self):

        fields = self.real_fields(10, 17)

        self.assertNotIn(
            "90",
            fields["survey_numbers"]
        )

    def test_10_invalid_evidence_preserved(self):

        fields = self.real_fields(10, 17)

        self.assertTrue(

            any(

                item["value"] == "90/"

                for item in
                fields["invalid_subject_identifiers"]
            )
        )

    # ==============================================
    # MULTIPLE IDENTIFIERS
    # ==============================================

    def test_11_multiple_surveys(self):

        fields = self.real_fields(11, 13)

        self.assertIn(
            "108/4",
            fields["survey_numbers"]
        )

        self.assertIn(
            "108/2",
            fields["survey_numbers"]
        )

    def test_12_multiple_scalar_not_selected(self):

        fields = extract_kannada_fields(

            "ಸರ್ವೆ ನಂ. 108/4, 108/2"
        )

        self.assertIsNone(
            fields["survey_number"]
        )

    # ==============================================
    # ADDITIONAL IDENTIFIERS
    # ==============================================

    def test_13_assessment_evidence(self):

        fields = extract_kannada_fields(

            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/104"
        )

        self.assertEqual(

            fields["identifier_candidates"][
                "assessment_numbers"
            ],

            ["27/104"]
        )

        self.assertEqual(
            fields["assessment_numbers"],
            []
        )

    def test_14_registration_number(self):

        fields = extract_kannada_fields(

            "ನೋಂದಣಿ ನಂ. 123/2026"
        )

        self.assertEqual(
            fields["registration_number"],
            "123/2026"
        )

    def test_15_pid_slash(self):

        fields = extract_kannada_fields(

            "ಪಿ.ಐ.ಡಿ. ಸಂಖ್ಯೆ 96-49-54/9"
        )

        self.assertEqual(
            fields["pid_number"],
            "96-49-54/9"
        )

    # ==============================================
    # FALSE-POSITIVE PREVENTION
    # ==============================================

    def test_16_website_excluded(self):

        fields = extract_kannada_fields(

            "ವೆಬ್ಸೈಟ್ ನಂ. 25"
        )

        self.assertEqual(
            fields["site_numbers"],
            []
        )

    def test_17_loan_account_excluded(self):

        fields = extract_kannada_fields(

            "ಸಾಲದ ಖಾತಾ ಸಂ. 550/63"
        )

        self.assertEqual(
            fields["khata_numbers"],
            []
        )

    # ==============================================
    # MULTILINGUAL PROCESSOR INTEGRATION
    # ==============================================

    def process_real_notice(self, page, region):

        original = self.records[
            (page, region)
        ]

        return process_multilingual_notice(

            original["raw_text"],

            secondary_text=original.get(
                "secondary_raw_text"
            ),

            primary_ocr_language=original.get(
                "primary_ocr_language"
            ),

            secondary_ocr_language=original.get(
                "secondary_ocr_language"
            )
        )

    def test_18_pid_conflict_preserved(self):

        result = self.process_real_notice(10, 1)

        self.assertIn(

            "pid_numbers",

            result["ocr_validation"][
                "conflicting_fields"
            ]
        )

    def test_19_conflicting_pid_blocked(self):

        result = self.process_real_notice(10, 1)

        self.assertIsNone(
            result["fields"]["pid_number"]
        )

        self.assertEqual(
            result["fields"]["pid_numbers"],
            []
        )

    def test_20_subject_site_preserved(self):

        result = self.process_real_notice(10, 1)

        self.assertEqual(
            result["fields"]["site_number"],
            "3"
        )

    def test_21_boundary_site_preserved(self):

        result = self.process_real_notice(10, 1)

        self.assertEqual(

            result["fields"][
                "boundary_identifiers"
            ]["site_numbers"],

            ["2"]
        )

    def test_22_manual_review_required(self):

        result = self.process_real_notice(10, 11)

        self.assertTrue(
            result["requires_review"]
        )

    def test_23_automatic_alert_disabled(self):

        result = self.process_real_notice(10, 11)

        self.assertFalse(
            result["eligible_for_alert"]
        )

    def test_24_original_evidence_preserved(self):

        result = self.process_real_notice(10, 11)

        self.assertIn(

            "893",

            result["primary_result"][
                "fields"
            ]["site_numbers"]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
