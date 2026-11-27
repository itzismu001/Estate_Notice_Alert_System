"""
Permanent regression tests for agricultural area
extraction and incomplete measurement detection.

These tests do not require external newspaper files,
OCR execution, database access or temporary backups.
"""

import unittest

from decimal import Decimal

from notices.services.agricultural_area_extractor import (
    extract_agricultural_areas,
)

from notices.services.incomplete_measurement_detector import (
    detect_incomplete_measurements,
)


class MeasurementTestBase(unittest.TestCase):

    def assert_safe(self, item):

        self.assertIs(
            item["requires_review"], True
        )

        for key in (
            "verified",
            "ownership_verified",
            "approved_for_search",
            "eligible_for_alert",
        ):

            self.assertIs(item[key], False)

    def assert_evidence(self, text, item):

        start = item["start_offset"]
        end = item["end_offset"]

        self.assertTrue(
            0 <= start < end <= len(text)
        )

        self.assertEqual(
            text[start:end],
            item["raw_measurement"],
        )

        line_start = text.rfind(
            "\n", 0, start
        ) + 1

        line_end = text.find("\n", end)

        if line_end == -1:
            line_end = len(text)

        self.assertEqual(
            text[line_start:line_end],
            item["source_text"],
        )

    def assert_agricultural(
        self,
        text,
        expected,
        ambiguous_count=0,
    ):

        result = extract_agricultural_areas(text)

        candidates = result[
            "measurement_candidates"
        ]

        ambiguous = result[
            "ambiguous_candidates"
        ]

        self.assertEqual(
            [
                item["normalized_total_guntas"]
                for item in candidates
            ],
            expected,
        )

        self.assertEqual(
            result["candidate_count"],
            len(expected),
        )

        self.assertEqual(
            result["ambiguous_count"],
            ambiguous_count,
        )

        self.assertEqual(
            len(ambiguous),
            ambiguous_count,
        )

        self.assertIsNone(
            result["selected_measurement"]
        )

        self.assertTrue(
            result["property_association_pending"]
        )

        self.assert_safe(result)

        for item in candidates + ambiguous:

            self.assert_safe(item)
            self.assert_evidence(text, item)

        for item in ambiguous:

            for key in (
                "normalized_total_guntas",
                "normalized_total_acres",
                "normalized_total_square_feet",
            ):

                self.assertIsNone(item[key])

        return result

    def assert_incomplete(
        self,
        text,
        expected,
    ):

        result = detect_incomplete_measurements(
            text
        )

        candidates = result[
            "incomplete_candidates"
        ]

        self.assertEqual(
            [
                item["normalized_numeric_value"]
                for item in candidates
            ],
            expected,
        )

        self.assertEqual(
            result["candidate_count"],
            len(expected),
        )

        self.assertIsNone(
            result["selected_measurement"]
        )

        self.assert_safe(result)

        for item in candidates:

            self.assert_safe(item)

            self.assert_evidence(text, item)

            self.assertEqual(
                item["reason"],
                "MISSING_OR_CORRUPTED_UNIT",
            )

            self.assertIsNone(
                item["measurement_unit"]
            )

            self.assertFalse(
                item["property_association_verified"]
            )

            for key in (
                "normalized_total_guntas",
                "normalized_total_acres",
                "normalized_total_square_feet",
            ):

                self.assertIsNone(item[key])

        return result


class AgriculturalAreaTests(
    MeasurementTestBase
):

    def test_01_english_compound(self):

        self.assert_agricultural(
            "6 Acres 38 Guntas",
            ["278"],
        )

    def test_02_singular_acre(self):

        self.assert_agricultural(
            "1 Acre 25 Guntas",
            ["65"],
        )

    def test_03_multiline_compound(self):

        self.assert_agricultural(
            "6 Acres 38\nGuntas",
            ["278"],
        )

    def test_04_kannada_compound(self):

        self.assert_agricultural(
            "1 ಎಕರೆ 04.2 ಗುಂಟೆ",
            ["44.2"],
        )

    def test_05_kannada_digits(self):

        self.assert_agricultural(
            "೧ ಎಕರೆ ೨೫ ಗುಂಟೆ",
            ["65"],
        )

    def test_06_hyphenated_measurement(self):

        self.assert_agricultural(
            "0-32 guntas",
            ["32"],
        )

    def test_07_decimal_hyphenated(self):

        self.assert_agricultural(
            "0-13.04 GUNTAS",
            ["13.04"],
        )

    def test_08_decimal_guntas(self):

        self.assert_agricultural(
            "7.5 Guntas",
            ["7.5"],
        )

    def test_09_standalone_acre(self):

        self.assert_agricultural(
            "1 acre",
            ["40"],
        )

    def test_10_multiple_parcel_areas(self):

        self.assert_agricultural(
            "7.5 Guntas, 19 Guntas, 13.5 Guntas",
            ["7.5", "19", "13.5"],
        )

    def test_11_subject_and_parent_area(self):

        self.assert_agricultural(
            "0-32 guntas out of 1 acre 25 guntas",
            ["32", "65"],
        )

    def test_12_included_kharab_area(self):

        self.assert_agricultural(
            "6 Acres 38 Guntas including "
            "14 Guntas of Phut Kharab",
            ["278", "14"],
        )

    def test_13_repeated_measurements(self):

        self.assert_agricultural(
            "Item 1: 13 guntas. Item 2: 13 guntas",
            ["13", "13"],
        )

    def test_14_ambiguous_percentage(self):

        self.assert_agricultural(
            "3% guntas",
            [],
            1,
        )

    def test_15_ambiguous_punctuation(self):

        self.assert_agricultural(
            "1! guntas",
            [],
            1,
        )

    def test_16_missing_acre_digit(self):

        self.assert_agricultural(
            "ಒಟ್ಟು! ಎಕರೆ 04.2 ಗುಂಟೆ",
            [],
            1,
        )

    def test_17_multiple_kannada_measurements(self):

        self.assert_agricultural(
            "1 ಎಕರೆ 04.2 ಗುಂಟೆ, "
            "19.04 ಗುಂಟೆ ಮತ್ತು 24.98 ಗುಂಟೆ",
            ["44.2", "19.04", "24.98"],
        )

    def test_18_financial_text_excluded(self):

        self.assert_agricultural(
            "Loan amount Rs. 48,70,000/- "
            "interest 12% and notice 30 days",
            [],
        )

    def test_19_empty_input(self):

        self.assert_agricultural("", [])

    def test_20_standard_area_excluded(self):

        self.assert_agricultural(
            "1950 Sq.Ft and 216 Sq.Mtrs",
            [],
        )


class IncompleteMeasurementTests(
    MeasurementTestBase
):

    def test_21_real_court_ocr_pattern(self):

        self.assert_incomplete(
            "1 acre 21 guntas, "
            "Sy. No. 48/4 measuring 27\n"
            "ಸ್ಯಾರಿ ನಾಟ to an extent of 1 acre",
            ["27"],
        )

    def test_22_missing_unit(self):

        self.assert_incomplete(
            "Agricultural land Survey No. 43/2 "
            "measuring 15",
            ["15"],
        )

    def test_23_decimal_missing_unit(self):

        self.assert_incomplete(
            "Agricultural land Sy. No. 43/2 "
            "measuring 13.5",
            ["13.5"],
        )

    def test_24_complete_gunta_excluded(self):

        self.assert_incomplete(
            "Agricultural land Sy. No. 43/2 "
            "measuring 15 guntas",
            [],
        )

    def test_25_complete_compound_excluded(self):

        self.assert_incomplete(
            "Sy. No. 43/2 measuring 1 acre 25 guntas",
            [],
        )

    def test_26_multiline_unit_excluded(self):

        self.assert_incomplete(
            "Agricultural land Sy. No. 43/2 "
            "measuring 15\n"
            "guntas",
            [],
        )

    def test_27_square_feet_excluded(self):

        self.assert_incomplete(
            "Agricultural land Sy. No. 43/2 "
            "measuring 1200 Sq.Ft",
            [],
        )

    def test_28_square_metres_excluded(self):

        self.assert_incomplete(
            "Agricultural land Sy. No. 43/2 "
            "measuring 216 sq.m",
            [],
        )

    def test_29_dimensions_excluded(self):

        self.assert_incomplete(
            "Agricultural land Sy. No. 43/2 "
            "measuring 30 x 40 feet",
            [],
        )

    def test_30_existing_ambiguity_excluded(self):

        self.assert_incomplete(
            "Agricultural land Sy. No. 43/2 "
            "measuring 3% guntas",
            [],
        )

    def test_31_agricultural_context_required(self):

        self.assert_incomplete(
            "Sy. No. 43/2 measuring 27",
            [],
        )

    def test_32_financial_text_excluded(self):

        self.assert_incomplete(
            "Agricultural loan amount Rs. 270000",
            [],
        )

    def test_33_kannada_context(self):

        self.assert_incomplete(
            "ಎಕರೆ Sy. No. 48/4 measuring ೨೭",
            ["27"],
        )

    def test_34_multiple_incomplete_measurements(self):

        self.assert_incomplete(
            "Agricultural land Sy. No. 43/2 "
            "measuring 15; "
            "Sy. No. 48/4 measuring 27",
            ["15", "27"],
        )

    def test_35_empty_input(self):

        self.assert_incomplete("", [])


class MeasurementIntegrityTests(
    MeasurementTestBase
):

    def test_36_exact_arithmetic_conversion(self):

        result = self.assert_agricultural(
            "6 Acres 38 Guntas",
            ["278"],
        )

        item = result[
            "measurement_candidates"
        ][0]

        self.assertEqual(
            Decimal(item["normalized_total_acres"]),
            Decimal("6.95"),
        )

        self.assertEqual(
            Decimal(
                item["normalized_total_square_feet"]
            ),
            Decimal("302742"),
        )

        self.assertTrue(
            item["normalized_values_are_derived"]
        )

    def test_37_decimal_precision(self):

        result = self.assert_agricultural(
            "13.04 Guntas",
            ["13.04"],
        )

        item = result[
            "measurement_candidates"
        ][0]

        self.assertEqual(
            Decimal(
                item["normalized_total_square_feet"]
            ),
            Decimal("14200.56"),
        )

    def test_38_hyphenated_warning(self):

        result = self.assert_agricultural(
            "0-32 guntas",
            ["32"],
        )

        item = result[
            "measurement_candidates"
        ][0]

        self.assertIn(
            "HYPHENATED_NOTATION_REQUIRES_CONFIRMATION",
            item["warnings"],
        )

    def test_39_out_of_range_gunta_warning(self):

        result = self.assert_agricultural(
            "1 acre 45 guntas",
            ["85"],
        )

        item = result[
            "measurement_candidates"
        ][0]

        self.assertIn(
            "GUNTA_COMPONENT_OUTSIDE_STANDARD_RANGE",
            item["warnings"],
        )

    def test_40_zero_area_warning(self):

        result = self.assert_agricultural(
            "0 acres",
            ["0"],
        )

        item = result[
            "measurement_candidates"
        ][0]

        self.assertIn(
            "ZERO_AREA",
            item["warnings"],
        )

    def test_41_unicode_evidence_preserved(self):

        text = (
            "ಒಟ್ಟು\u200c ೧ ಎಕರೆ\u200d ೨೫ ಗುಂಟೆ"
        )

        result = self.assert_agricultural(
            text,
            ["65"],
        )

        item = result[
            "measurement_candidates"
        ][0]

        self.assertIn(
            "\u200d",
            item["raw_measurement"],
        )

        self.assertEqual(
            item["source_text"],
            text,
        )

    def test_42_repeated_occurrences_have_distinct_offsets(self):

        result = self.assert_agricultural(
            "Item 1: 13 guntas. Item 2: 13 guntas",
            ["13", "13"],
        )

        first, second = result[
            "measurement_candidates"
        ]

        self.assertLess(
            first["start_offset"],
            second["start_offset"],
        )

        self.assertLessEqual(
            first["end_offset"],
            second["start_offset"],
        )

    def test_43_incomplete_survey_context_preserved(self):

        result = self.assert_incomplete(
            "1 acre 21 guntas, "
            "Sy. No. 48/4 measuring 27\n"
            "ಸ್ಯಾರಿ ನಾಟ to an extent of 1 acre",
            ["27"],
        )

        item = result[
            "incomplete_candidates"
        ][0]

        self.assertEqual(
            item["survey_number_context"],
            "48/4",
        )

        self.assertEqual(
            item["raw_numeric_value"],
            "27",
        )

        self.assertEqual(
            item["raw_measurement"],
            "Sy. No. 48/4 measuring 27",
        )

        self.assertTrue(
            item["following_source_text"].startswith(
                "\nಸ್ಯಾರಿ"
            )
        )

    def test_44_kannada_numeric_evidence_preserved(self):

        result = self.assert_incomplete(
            "ಎಕರೆ Sy. No. 48/4 measuring ೨೭",
            ["27"],
        )

        item = result[
            "incomplete_candidates"
        ][0]

        self.assertEqual(
            item["raw_numeric_value"],
            "೨೭",
        )

        self.assertEqual(
            item["normalized_numeric_value"],
            "27",
        )

    def test_45_extractors_preserve_existing_outputs(self):

        text = (
            "Sy. No. 43/1 measuring 1 acre 21 guntas, "
            "Sy. No. 48/4 measuring 27\n"
            "ಸ್ಯಾರಿ ನಾಟ. "
            "Sy. No. 63/4 measuring 3% guntas"
        )

        before = self.assert_agricultural(
            text,
            ["61"],
            1,
        )

        incomplete = self.assert_incomplete(
            text,
            ["27"],
        )

        after = extract_agricultural_areas(text)

        self.assertEqual(before, after)

        existing = (
            after["measurement_candidates"]
            + after["ambiguous_candidates"]
        )

        for candidate in incomplete[
            "incomplete_candidates"
        ]:

            for item in existing:

                self.assertFalse(
                    candidate["start_offset"]
                    < item["end_offset"]
                    and candidate["end_offset"]
                    > item["start_offset"]
                )


if __name__ == "__main__":

    unittest.main()
