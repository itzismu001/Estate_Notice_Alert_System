
import json
from pathlib import Path
import unittest

from notices.services.kannada_identifier_parser import (
    parse_kannada_identifiers
)


class KannadaIdentifierParserTests(unittest.TestCase):

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

    def check_identifier(self, text, field, expected):

        result = parse_kannada_identifiers(text)

        self.assertEqual(
            result["subject_identifiers"][field],
            expected
        )

    # ==============================================
    # CONTROLLED IDENTIFIER TESTS
    # ==============================================

    def test_01_site_label(self):

        self.check_identifier(
            "ಸೈಟ್ ನಂ. 893",
            "site_numbers",
            ["893"]
        )

    def test_02_short_site_label(self):

        self.check_identifier(
            "ನಿವೇಶನ ಸಂ.9",
            "site_numbers",
            ["9"]
        )

    def test_03_short_survey_label(self):

        self.check_identifier(
            "ಸರ್ವೆ ಸಂ. 217/1",
            "survey_numbers",
            ["217/1"]
        )

    def test_04_multiple_surveys(self):

        self.check_identifier(
            "ಸರ್ವೆ ನಂ. 108/4, 108/2 ಮತ್ತು 108/3",
            "survey_numbers",
            ["108/4", "108/2", "108/3"]
        )

    def test_05_short_khata_label(self):

        self.check_identifier(
            "ಖಾತಾ ಸಂ. 290",
            "khata_numbers",
            ["290"]
        )

    def test_06_assessment_number(self):

        self.check_identifier(
            "ಅಸೆಸ್ಮೆಂಟ್ ನಂ. 27/104",
            "assessment_numbers",
            ["27/104"]
        )

    def test_07_pid_slash(self):

        self.check_identifier(
            "ಪಿ.ಐ.ಡಿ. ಸಂಖ್ಯೆ 96-49-54/9",
            "pid_numbers",
            ["96-49-54/9"]
        )

    def test_08_property_number(self):

        self.check_identifier(
            "ಆಸ್ತಿ ನಂ. 235",
            "property_numbers",
            ["235"]
        )

    def test_09_registration_number(self):

        self.check_identifier(
            "ನೋಂದಣಿ ನಂ. 123/2026",
            "registration_numbers",
            ["123/2026"]
        )

    def test_10_flat_number(self):

        self.check_identifier(
            "ಫ್ಲಾಟ್ ನಂ. 19",
            "flat_numbers",
            ["19"]
        )

    def test_11_kannada_numerals(self):

        self.check_identifier(
            "ಸರ್ವೆ ನಂ. ೧೨೩/೪",
            "survey_numbers",
            ["123/4"]
        )

    def test_12_loan_account_exclusion(self):

        self.check_identifier(
            "ಸಾಲದ ಖಾತಾ ಸಂ. 550/63",
            "khata_numbers",
            []
        )

    def test_13_incomplete_survey(self):

        self.check_identifier(
            "ಸರ್ವೆ ನಂ. 90/ ರಲ್ಲಿರುವ",
            "survey_numbers",
            []
        )

    def test_14_website_exclusion(self):

        self.check_identifier(
            "ಹರಾಜು ವೆಬ್ಸೈಟ್ ನಂ. 25",
            "site_numbers",
            []
        )

    # ==============================================
    # INVALID IDENTIFIER SAFETY
    # ==============================================

    def test_15_invalid_evidence_preserved(self):

        result = parse_kannada_identifiers(
            "ಸರ್ವೆ ನಂ. 90/ ರಲ್ಲಿರುವ"
        )

        self.assertEqual(
            result["invalid_subject_identifiers"][0]["value"],
            "90/"
        )

    def test_16_invalid_identifier_reason(self):

        result = parse_kannada_identifiers(
            "ಸರ್ವೆ ನಂ. 90/ ರಲ್ಲಿರುವ"
        )

        self.assertEqual(
            result["invalid_subject_identifiers"][0]["reason"],
            "INCOMPLETE_IDENTIFIER"
        )

    # ==============================================
    # BOUNDARY SEPARATION
    # ==============================================

    def boundary_result(self, marker):

        return parse_kannada_identifiers(

            "ಸೈಟ್ ನಂ. 893 "

            + marker

            + " ಪಶ್ಚಿಮಕ್ಕೆ ಸೈಟ್ ನಂ. 56 "
            "ಉತ್ತರಕ್ಕೆ ಸೈಟ್ ನಂ. 802 "
            "ದಕ್ಷಿಣಕ್ಕೆ ಸೈಟ್ ನಂ. 894"
        )

    def check_subject(self, marker):

        result = self.boundary_result(marker)

        self.assertEqual(
            result["subject_identifiers"]["site_numbers"],
            ["893"]
        )

    def check_boundary(self, marker):

        result = self.boundary_result(marker)

        self.assertEqual(
            result["boundary_identifiers"]["site_numbers"],
            ["56", "802", "894"]
        )

    def test_17_standard_boundary_subject(self):
        self.check_subject("ಚಕ್ಕುಬಂದಿ")

    def test_18_standard_boundary_sites(self):
        self.check_boundary("ಚಕ್ಕುಬಂದಿ")

    def test_19_variant_boundary_subject(self):
        self.check_subject("ಚಕ್ಕುಬದಿ")

    def test_20_variant_boundary_sites(self):
        self.check_boundary("ಚಕ್ಕುಬದಿ")

    def test_21_alternate_boundary_subject(self):
        self.check_subject("ಚೆಕ್ಕುಬಂದಿ")

    def test_22_alternate_boundary_sites(self):
        self.check_boundary("ಚೆಕ್ಕುಬಂದಿ")

    def test_23_limits_boundary_subject(self):
        self.check_subject("ಗಡಿಗಳು:")

    def test_24_limits_boundary_sites(self):
        self.check_boundary("ಗಡಿಗಳು:")

    # ==============================================
    # REAL NEWSPAPER TESTS
    # ==============================================

    def real_notice(self, page, region):

        return parse_kannada_identifiers(
            self.records[(page, region)]["raw_text"]
        )

    def test_25_lost_will_survey(self):

        result = self.real_notice(10, 11)

        self.assertEqual(
            result["subject_identifiers"]["survey_numbers"],
            ["34/2"]
        )

    def test_26_lost_will_site(self):

        result = self.real_notice(10, 11)

        self.assertEqual(
            result["subject_identifiers"]["site_numbers"],
            ["893"]
        )

    def test_27_lost_will_boundary(self):

        result = self.real_notice(10, 11)

        self.assertEqual(
            result["boundary_identifiers"]["site_numbers"],
            ["56", "802", "894"]
        )

    def test_28_truncated_survey_excluded(self):

        result = self.real_notice(10, 17)

        self.assertNotIn(
            "90",
            result["subject_identifiers"]["survey_numbers"]
        )

    def test_29_truncated_survey_preserved(self):

        result = self.real_notice(10, 17)

        self.assertTrue(

            any(

                item["value"] == "90/"

                for item in
                result["invalid_subject_identifiers"]
            )
        )

    def test_30_first_survey_preserved(self):

        result = self.real_notice(11, 13)

        self.assertIn(
            "108/4",
            result["subject_identifiers"]["survey_numbers"]
        )

    def test_31_second_survey_recovered(self):

        result = self.real_notice(11, 13)

        self.assertIn(
            "108/2",
            result["subject_identifiers"]["survey_numbers"]
        )

    def test_32_existing_site_preserved(self):

        result = self.real_notice(7, 3)

        self.assertEqual(
            result["subject_identifiers"]["site_numbers"],
            ["1006/8"]
        )

    def test_33_existing_document_preserved(self):

        result = self.real_notice(7, 3)

        self.assertEqual(
            result["subject_identifiers"]["document_numbers"],
            ["1823/1984-85"]
        )

    # ==============================================
    # ADDITIONAL UNICODE BOUNDARY REGRESSION
    # ==============================================

    def test_34_website_with_joiner(self):

        self.check_identifier(
            "ಹರಾಜು ವೆಬ್‌ಸೈಟ್ ನಂ. 25",
            "site_numbers",
            []
        )

    def test_35_site_inside_sentence(self):

        self.check_identifier(
            "ಸದರಿ ಸೈಟ್ ಸಂಖ್ಯೆ 25",
            "site_numbers",
            ["25"]
        )

    def test_36_site_after_punctuation(self):

        self.check_identifier(
            "(ಸೈಟ್ ನಂ. 893)",
            "site_numbers",
            ["893"]
        )

    def test_37_website_and_property(self):

        self.check_identifier(
            "ವೆಬ್ಸೈಟ್ ನಂ. 25, ನಿವೇಶನ ನಂ. 893",
            "site_numbers",
            ["893"]
        )

    def test_38_kannada_site_numerals(self):

        self.check_identifier(
            "ಸೈಟ್ ನಂ. ೮೯೩",
            "site_numbers",
            ["893"]
        )


if __name__ == "__main__":

    unittest.main(verbosity=2)
