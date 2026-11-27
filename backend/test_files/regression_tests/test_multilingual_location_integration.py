
import json
import unittest

from pathlib import Path
from unittest.mock import patch

from notices.services.multilingual_processor import (
    process_multilingual_notice
)


class MultilingualLocationIntegrationTests(
    unittest.TestCase
):

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

        cls.results = {}

        for key, notice in cls.records.items():

            cls.results[key] = (
                process_multilingual_notice(

                    notice["raw_text"],

                    notice.get(
                        "secondary_raw_text"
                    ),

                    primary_ocr_language=notice.get(
                        "primary_ocr_language"
                    ),

                    secondary_ocr_language=notice.get(
                        "secondary_ocr_language"
                    )
                )
            )

    def test_01_all_regions_processed(self):

        self.assertEqual(
            len(self.results),
            40
        )

    def test_02_retained_notice_validation(self):

        for key, result in self.results.items():

            if result["retain_candidate"]:

                with self.subTest(region=key):

                    self.assertIsNotNone(
                        result["location_validation"]
                    )

    def test_03_rejected_notice_validation(self):

        for key, result in self.results.items():

            if result["decision"] == "REJECT":

                with self.subTest(region=key):

                    self.assertIsNone(
                        result["location_validation"]
                    )

    def test_04_kannada_village(self):

        result = self.results[(10, 1)]

        locations = result["location_validation"]

        self.assertEqual(

            locations[
                "agreed_location_candidates"
            ].get("village"),

            "ಮಲ್ಲತ್ತಹಳ್ಳಿ"
        )

    def test_05_kannada_hobli(self):

        result = self.results[(10, 1)]

        self.assertEqual(

            result["location_validation"][
                "agreed_location_candidates"
            ].get("hobli"),

            "ಯಶವಂತಪುರ"
        )

    def test_06_normalized_taluk(self):

        result = self.results[(10, 1)]

        self.assertEqual(

            result["location_validation"][
                "agreed_location_candidates"
            ].get("taluk"),

            "Bengaluru North"
        )

    def test_07_pid_conflict_preserved(self):

        result = self.results[(10, 1)]

        validation = result["ocr_validation"]

        self.assertEqual(

            validation["validations"][
                "pid_numbers"
            ]["status"],

            "CONFLICT"
        )

    def test_08_conflicting_pid_blocked(self):

        fields = self.results[(10, 1)]["fields"]

        self.assertIsNone(
            fields.get("pid_number")
        )

        self.assertEqual(
            fields.get("pid_numbers"),
            []
        )

    def test_09_lost_will_layout(self):

        result = self.results[(10, 11)]

        self.assertEqual(

            result["location_validation"][
                "agreed_location_candidates"
            ].get("layout"),

            "ಅರ್ಕಾವತಿ"
        )

    def test_10_lost_will_identifier_conflict(self):

        result = self.results[(10, 11)]

        fields = result["fields"]

        validation = result["ocr_validation"]

        comparison = validation["validations"][
            "site_numbers"
        ]

        # Confirm original primary OCR evidence.

        self.assertEqual(

            result["primary_result"]["fields"][
                "site_numbers"
            ],

            ["893"]
        )

        # Confirm secondary OCR disagreement.

        self.assertCountEqual(

            result["secondary_result"]["fields"][
                "site_numbers"
            ],

            ["893", "89"]
        )

        # Verify conflict detection.

        self.assertEqual(
            comparison["status"],
            "CONFLICT"
        )

        self.assertCountEqual(
            comparison["all_candidates"],
            ["89", "893"]
        )

        self.assertIsNone(
            comparison["selected_value"]
        )

        self.assertIn(
            "site_numbers",
            validation["conflicting_fields"]
        )

        # Verify conflicting values are blocked.

        self.assertIsNone(
            fields.get("site_number")
        )

        self.assertEqual(
            fields.get("site_numbers"),
            []
        )

        self.assertIn(
            "site_numbers",
            fields["blocked_identifier_fields"]
        )

        # Preserve valid survey number.

        self.assertEqual(
            fields["survey_numbers"],
            ["34/2"]
        )

        # Preserve neighbouring property evidence.

        self.assertCountEqual(

            fields["boundary_identifiers"][
                "site_numbers"
            ],

            ["56", "802", "894"]
        )

        # Confirm safety requirements.

        self.assertTrue(
            result["requires_review"]
        )

        self.assertFalse(
            result["verified"]
        )

        self.assertFalse(
            result["eligible_for_alert"]
        )

    def test_11_english_address(self):

        result = self.results[(11, 3)]

        addresses = result[
            "location_validation"
        ]["primary_result"][
            "property_address_candidates"
        ]

        self.assertIn(

            "Banashankari",

            " ".join(addresses)
        )

    def test_12_advocate_address_excluded(self):

        result = self.results[(10, 14)]

        candidates = result[
            "location_validation"
        ]["agreed_location_candidates"]

        self.assertNotEqual(
            candidates.get("layout"),
            "HSR"
        )

        self.assertNotEqual(
            candidates.get("pin_code"),
            "560102"
        )

    def test_13_court_notice_retained(self):

        result = self.results[(7, 1)]

        self.assertEqual(
            result["decision"],
            "REVIEW"
        )

        self.assertIsNotNone(
            result["location_validation"]
        )

    def test_14_missing_secondary_ocr(self):

        result = self.results[(7, 1)]

        locations = result["location_validation"]

        self.assertFalse(
            locations["secondary_available"]
        )

        self.assertIn(

            "taluk",

            locations[
                "secondary_unavailable_fields"
            ]
        )

    def test_15_secured_property_notice(self):

        result = self.results[(10, 10)]

        self.assertEqual(
            result["decision"],
            "REVIEW"
        )

        self.assertEqual(

            result["notice_category"],

            "SECURED_PROPERTY_DEMAND"
        )

        self.assertIsNotNone(
            result["location_validation"]
        )

    def test_16_original_text_preserved(self):

        for key, result in self.results.items():

            original = self.records[key]

            with self.subTest(region=key):

                self.assertEqual(

                    result["raw_text"],

                    original["raw_text"]
                )

                self.assertEqual(

                    result["secondary_raw_text"],

                    original.get("secondary_raw_text")
                )

    def test_17_no_verified_property_address(self):

        for key, result in self.results.items():

            locations = result["location_validation"]

            if locations is not None:

                with self.subTest(region=key):

                    self.assertIsNone(
                        locations["property_address"]
                    )

                    self.assertFalse(
                        locations["verified"]
                    )

    def test_18_no_search_approval(self):

        for result in self.results.values():

            locations = result["location_validation"]

            if locations is not None:

                self.assertFalse(
                    locations["approved_for_search"]
                )

    def test_19_no_automatic_alerts(self):

        for result in self.results.values():

            self.assertFalse(
                result["eligible_for_alert"]
            )

            locations = result["location_validation"]

            if locations is not None:

                self.assertFalse(
                    locations["eligible_for_alert"]
                )

                self.assertTrue(
                    locations["requires_review"]
                )

    def test_20_rejected_notice_skips_service(self):

        notice = self.records[(7, 2)]

        with patch(

            "notices.services.multilingual_processor."
            "validate_property_locations"

        ) as validator:

            result = process_multilingual_notice(

                notice["raw_text"],

                notice.get("secondary_raw_text")
            )

            self.assertEqual(
                result["decision"],
                "REJECT"
            )

            validator.assert_not_called()


if __name__ == "__main__":

    unittest.main(verbosity=2)
