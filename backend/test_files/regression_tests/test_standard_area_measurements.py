"""
Permanent regression tests for standard property
area extraction, recovery and Kannada refinement.

All measurements remain unverified candidates.
"""

import json
import unittest

from pathlib import Path
from decimal import Decimal
from collections import Counter

from notices.services.standard_area_extractor import (
    extract_standard_areas,
    normalize_area,
)

from notices.services.standard_area_recovery import (
    recover_standard_areas,
)

from notices.services.kannada_area_refinement import (
    refine_kannada_areas,
)

from notices.services.agricultural_area_extractor import (
    extract_agricultural_areas,
)

from notices.services.incomplete_measurement_detector import (
    detect_incomplete_measurements,
)


def numeric_values(result):

    return [
        (
            item["area_value"],
            item["area_unit"],
        )
        for item in result["measurement_candidates"]
    ]


def ambiguity_reasons(result):

    return [
        item["reason"]
        for item in result["ambiguous_candidates"]
    ]


def all_candidates(result):

    return (
        result["measurement_candidates"]
        + result["ambiguous_candidates"]
    )


def is_safe(item):

    return (
        item.get("requires_review") is True
        and item.get("verified") is False
        and item.get("ownership_verified") is False
        and item.get("approved_for_search") is False
        and item.get("eligible_for_alert") is False
    )


def overlaps(first, second):

    return (
        first["start_offset"] < second["end_offset"]
        and first["end_offset"] > second["start_offset"]
    )


class MeasurementTestBase(unittest.TestCase):

    def assert_safe_result(self, text, result):

        text = text or ""

        self.assertTrue(is_safe(result))

        self.assertIsNone(
            result["selected_measurement"]
        )

        self.assertEqual(
            result["candidate_count"],
            len(result["measurement_candidates"]),
        )

        self.assertEqual(
            result["ambiguous_count"],
            len(result["ambiguous_candidates"]),
        )

        items = all_candidates(result)

        for item in items:

            self.assertTrue(is_safe(item))

            self.assertFalse(
                item["property_association_verified"]
            )

            start = item["start_offset"]
            end = item["end_offset"]

            self.assertTrue(
                0 <= start < end <= len(text)
            )

            self.assertEqual(
                text[start:end],
                item["raw_measurement"],
            )

        for item in result["ambiguous_candidates"]:

            for key in (
                "area_value",
                "area_unit",
                "normalized_square_feet",
                "normalized_square_yards",
                "normalized_square_metres",
            ):

                self.assertIsNone(item[key])

        for index, first in enumerate(items):

            for second in items[index + 1:]:

                self.assertFalse(
                    overlaps(first, second)
                )

    def assert_extraction(
        self,
        extractor,
        text,
        expected,
        reasons=None,
    ):

        result = extractor(text)

        self.assertEqual(
            numeric_values(result),
            expected,
        )

        self.assertEqual(
            ambiguity_reasons(result),
            reasons or [],
        )

        self.assert_safe_result(text, result)

        return result


# ==================================================
# STANDARD AREA EXTRACTION: 20 TESTS
# ==================================================


class TestStandardAreaExtraction(MeasurementTestBase):

    def test_01_square_feet(self):

        self.assert_extraction(
            extract_standard_areas,
            "1200 sq. ft.",
            [("1200", "SQ_FT")],
        )

    def test_02_square_feet_full_words(self):

        self.assert_extraction(
            extract_standard_areas,
            "1500 square feet",
            [("1500", "SQ_FT")],
        )

    def test_03_square_yards(self):

        self.assert_extraction(
            extract_standard_areas,
            "500 sq. yards",
            [("500", "SQ_YD")],
        )

    def test_04_square_metres(self):

        self.assert_extraction(
            extract_standard_areas,
            "100 square metres",
            [("100", "SQ_M")],
        )

    def test_05_decimal_value(self):

        self.assert_extraction(
            extract_standard_areas,
            "474.78 sq.ft.",
            [("474.78", "SQ_FT")],
        )

    def test_06_thousands_separator(self):

        self.assert_extraction(
            extract_standard_areas,
            "1,200 sq.ft.",
            [("1200", "SQ_FT")],
        )

    def test_07_kannada_square_feet(self):

        self.assert_extraction(
            extract_standard_areas,
            "1200 ಚದರ ಅಡಿ",
            [("1200", "SQ_FT")],
        )

    def test_08_kannada_digits(self):

        self.assert_extraction(
            extract_standard_areas,
            "೧೨೦೦ ಚದರ ಅಡಿ",
            [("1200", "SQ_FT")],
        )

    def test_09_kannada_square_metres(self):

        self.assert_extraction(
            extract_standard_areas,
            "100 ಚದರ ಮೀಟರ್",
            [("100", "SQ_M")],
        )

    def test_10_multiline_area(self):

        self.assert_extraction(
            extract_standard_areas,
            "1200\nಚದರ ಅಡಿ",
            [("1200", "SQ_FT")],
        )

    def test_11_multiple_areas(self):

        self.assert_extraction(
            extract_standard_areas,
            "982 sq.ft. and 223 sq.ft.",
            [
                ("982", "SQ_FT"),
                ("223", "SQ_FT"),
            ],
        )

    def test_12_repeated_occurrences(self):

        self.assert_extraction(
            extract_standard_areas,
            "1200 sq.ft.; 1200 sq.ft.",
            [
                ("1200", "SQ_FT"),
                ("1200", "SQ_FT"),
            ],
        )

    def test_13_linear_measurement_excluded(self):

        self.assert_extraction(
            extract_standard_areas,
            "East to West 30 feet",
            [],
        )

    def test_14_dimension_operand_excluded(self):

        self.assert_extraction(
            extract_standard_areas,
            "30 x 40 sq.ft.",
            [],
        )

    def test_15_agricultural_area_excluded(self):

        self.assert_extraction(
            extract_standard_areas,
            "1 acre 25 guntas",
            [],
        )

    def test_16_malformed_number_excluded(self):

        self.assert_extraction(
            extract_standard_areas,
            "12,00 sq.ft.",
            [],
        )

    def test_17_corrupted_unit(self):

        self.assert_extraction(
            extract_standard_areas,
            "280 sq. 11",
            [],
            ["AMBIGUOUS_OCR_AREA_UNIT"],
        )

    def test_18_zero_area_warning(self):

        result = self.assert_extraction(
            extract_standard_areas,
            "0 sq.ft.",
            [("0", "SQ_FT")],
        )

        self.assertIn(
            "ZERO_AREA",
            result["measurement_candidates"][0]["warnings"],
        )

    def test_19_conversion_square_yards(self):

        result = normalize_area("500", "SQ_YD")

        self.assertEqual(
            result["normalized_square_feet"],
            "4500",
        )

        self.assertEqual(
            result["normalized_square_metres"],
            "418.06368",
        )

    def test_20_conversion_square_metres(self):

        result = normalize_area("100", "SQ_M")

        self.assertEqual(
            result["normalized_square_feet"],
            "1076.391042",
        )

        self.assertEqual(
            result["normalized_square_yards"],
            "119.599005",
        )


# ==================================================
# STANDARD AREA RECOVERY: 15 TESTS
# ==================================================


class TestStandardAreaRecovery(MeasurementTestBase):

    def test_01_kannada_abbreviation(self):

        self.assert_extraction(
            recover_standard_areas,
            "ಕಾರ್ಪೆಟ್ ಪ್ರದೇಶ 1,657 ಚ.ಅ.",
            [("1657", "SQ_FT")],
        )

    def test_02_unicode_abbreviation(self):

        self.assert_extraction(
            recover_standard_areas,
            "೧೨೦೦ ಚ.ಅ.",
            [("1200", "SQ_FT")],
        )

    def test_03_primary_number_words(self):

        self.assert_extraction(
            recover_standard_areas,
            "590\na ae (ಐದುನೂರ ತೊಂಭತ್ತು) ಚದರ ಅಡಿ",
            [("590", "SQ_FT")],
        )

    def test_04_secondary_number_words(self):

        self.assert_extraction(
            recover_standard_areas,
            "590\nಚತತ (ಐದುನೂರ ತೊಂಭತ್ತು) ಚದರ ಅಡಿ",
            [("590", "SQ_FT")],
        )

    def test_05_table_column_recovery(self):

        result = self.assert_extraction(
            recover_standard_areas,
            "ಅವಿಭಾಜಿತ ಪಾಲು ವಿಸ್ತೀರ್ಣ 360| ಮತ್ತು ಶುಲ್ಕಗಳು.\n"
            "ಚೌಡಯ್ಯ ಬ್ಲಾಕ್‌, ಆರ್‌ ಟಿ ನಗರ, ಚದರ ಅಡಿ ಹಕ್ಕು",
            [("360", "SQ_FT")],
        )

        self.assertIn(
            "TABLE_COLUMN_INTERFERENCE",
            result["measurement_candidates"][0]["warnings"],
        )

    def test_06_corrupted_kannada_unit(self):

        result = self.assert_extraction(
            recover_standard_areas,
            "1200\nsad ಅಡಿಗಳ ವಿಸ್ತೀರ್ಣವುಳ್ಳ ಸ್ವತ್ತನ್ನು",
            [],
            ["CORRUPTED_KANNADA_AREA_UNIT"],
        )

        self.assertEqual(
            result["ambiguous_candidates"][0][
                "normalized_numeric_value"
            ],
            "1200",
        )

    def test_07_corrupted_numeric_value(self):

        self.assert_extraction(
            recover_standard_areas,
            "ಜ್ಯ Sq. feet of\nbuilt up area",
            [],
            ["CORRUPTED_NUMERIC_VALUE"],
        )

    def test_08_corrupted_english_unit(self):

        self.assert_extraction(
            recover_standard_areas,
            "1465 ತ feet Super Built-up area",
            [],
            ["CORRUPTED_ENGLISH_AREA_UNIT"],
        )

    def test_09_slash_corruption(self):

        result = self.assert_extraction(
            recover_standard_areas,
            "2/170 ಸೂಪರ್‌ ನಿರ್ಮಿತ\nಪ್ರದೇಶ",
            [],
            ["AMBIGUOUS_SLASH_NUMERIC_VALUE"],
        )

        self.assertIsNone(
            result["ambiguous_candidates"][0][
                "normalized_numeric_value"
            ]
        )

    def test_10_missing_numeric_value(self):

        self.assert_extraction(
            recover_standard_areas,
            "ಚದರ ಅಡಿಗಳ ನ ಹಜ್‌ ತ್ತಿನ ಚಕ್ಕುಬಂದಿ:",
            [],
            ["MISSING_NUMERIC_VALUE"],
        )

    def test_11_existing_area_not_duplicated(self):

        self.assert_extraction(
            recover_standard_areas,
            "1200 sq.ft.; 1200 ಚದರ ಅಡಿ",
            [],
        )

    def test_12_existing_ambiguity_not_duplicated(self):

        self.assert_extraction(
            recover_standard_areas,
            "280 sq. 11",
            [],
        )

    def test_13_number_word_disagreement(self):

        self.assert_extraction(
            recover_standard_areas,
            "690\n(ಐದುನೂರ ತೊಂಭತ್ತು) ಚದರ ಅಡಿ",
            [],
        )

    def test_14_unrelated_identifier_excluded(self):

        self.assert_extraction(
            recover_standard_areas,
            "Survey No. 2/170",
            [],
        )

    def test_15_dimension_operand_excluded(self):

        self.assert_extraction(
            recover_standard_areas,
            "30 x 40 ಚ.ಅ.",
            [],
        )


# ==================================================
# KANNADA AREA REFINEMENT: 15 TESTS
# ==================================================


class TestKannadaAreaRefinement(MeasurementTestBase):

    def test_01_square_metre_abbreviation(self):

        self.assert_extraction(
            refine_kannada_areas,
            "195.0963 ಚ.ಮೀ.",
            [("195.0963", "SQ_M")],
        )

    def test_02_multiline_abbreviation(self):

        self.assert_extraction(
            refine_kannada_areas,
            "195.0963\nಚ.ಮೀ.",
            [("195.0963", "SQ_M")],
        )

    def test_03_malformed_decimal(self):

        result = self.assert_extraction(
            refine_kannada_areas,
            "195,0963\nಚ.ಮೀ.",
            [],
            ["AMBIGUOUS_NUMERIC_PUNCTUATION"],
        )

        item = result["ambiguous_candidates"][0]

        self.assertEqual(
            item["raw_numeric_value"],
            "195,0963",
        )

        self.assertIsNone(
            item["normalized_numeric_value"]
        )

    def test_04_valid_thousands_grouping(self):

        self.assert_extraction(
            refine_kannada_areas,
            "1,200 ಚ.ಮೀ.",
            [("1200", "SQ_M")],
        )

    def test_05_kannada_digits(self):

        self.assert_extraction(
            refine_kannada_areas,
            "೧೦೦ ಚ.ಮೀ.",
            [("100", "SQ_M")],
        )

    def test_06_spaced_abbreviation(self):

        self.assert_extraction(
            refine_kannada_areas,
            "100 ಚ. ಮೀ.",
            [("100", "SQ_M")],
        )

    def test_07_separated_square_feet(self):

        self.assert_extraction(
            refine_kannada_areas,
            "ಅಳತೆ 1,157\n"
            "ರಂದುಇದಚೆ. ಚ.ಅ. ಪೂರ್ವಕ್ಕೆ:",
            [("1157", "SQ_FT")],
        )

    def test_08_separated_unicode_value(self):

        self.assert_extraction(
            refine_kannada_areas,
            "ಅಳತೆ ೧೧೫೭\n"
            "ರಂದುಇದಚೆ. ಚ.ಅ. ಪೂರ್ವಕ್ಕೆ:",
            [("1157", "SQ_FT")],
        )

    def test_09_unrelated_number_excluded(self):

        self.assert_extraction(
            refine_kannada_areas,
            "Loan amount 1157\nunknown text ಚ.ಅ.",
            [],
        )

    def test_10_existing_recovery_excluded(self):

        self.assert_extraction(
            refine_kannada_areas,
            "2100 ಚ.ಅ.",
            [],
        )

    def test_11_existing_standard_excluded(self):

        self.assert_extraction(
            refine_kannada_areas,
            "100 ಚದರ ಮೀಟರ್",
            [],
        )

    def test_12_linear_metre_excluded(self):

        self.assert_extraction(
            refine_kannada_areas,
            "18.288037 ಮೀ.",
            [],
        )

    def test_13_dimension_operand_excluded(self):

        self.assert_extraction(
            refine_kannada_areas,
            "30 x 40 ಚ.ಮೀ.",
            [],
        )

    def test_14_repeated_occurrences(self):

        self.assert_extraction(
            refine_kannada_areas,
            "100 ಚ.ಮೀ.; 100 ಚ.ಮೀ.",
            [
                ("100", "SQ_M"),
                ("100", "SQ_M"),
            ],
        )

    def test_15_missing_input(self):

        for text in ("", None):

            with self.subTest(text=text):

                self.assert_extraction(
                    refine_kannada_areas,
                    text,
                    [],
                )


# ==================================================
# REAL DATASET REGRESSION: 10 TESTS
# ==================================================


class TestRealStandardAreaDataset(MeasurementTestBase):

    @classmethod
    def setUpClass(cls):

        root = Path(__file__).resolve().parents[2]

        path = (
            root
            / "test_files"
            / "kannada_area_refinement_validation"
            / "results.json"
        )

        if not path.exists():

            raise FileNotFoundError(
                f"Required regression dataset missing: {path}"
            )

        cls.dataset = json.loads(
            path.read_text(encoding="utf-8")
        )

        cls.sources = []

        cls.indexed = {}

        for record in cls.dataset["results"]:

            for source, data in record["sources"].items():

                if data is None:
                    continue

                text = data["raw_text"]

                current = {

                    "raw_text": text,

                    "standard_area_result":
                        extract_standard_areas(text),

                    "recovery_result":
                        recover_standard_areas(text),

                    "refinement_result":
                        refine_kannada_areas(text),

                    "agricultural_result":
                        extract_agricultural_areas(text),

                    "incomplete_result":
                        detect_incomplete_measurements(text),

                }

                cls.sources.append((data, current))

                cls.indexed[
                    (
                        record["page_number"],
                        record["region_number"],
                        source,
                    )
                ] = current

    def test_01_dataset_source_count(self):

        self.assertEqual(
            len(self.dataset["results"]),
            30,
        )

        self.assertEqual(len(self.sources), 54)

    def test_02_standard_outputs_preserved(self):

        for previous, current in self.sources:

            self.assertEqual(
                previous["standard_area_result"],
                current["standard_area_result"],
            )

    def test_03_recovery_outputs_preserved(self):

        for previous, current in self.sources:

            self.assertEqual(
                previous["recovery_result"],
                current["recovery_result"],
            )

    def test_04_refinement_outputs_preserved(self):

        for previous, current in self.sources:

            self.assertEqual(
                previous["refinement_result"],
                current["refinement_result"],
            )

    def test_05_agricultural_outputs_preserved(self):

        for previous, current in self.sources:

            self.assertEqual(
                previous["agricultural_result"],
                current["agricultural_result"],
            )

    def test_06_incomplete_outputs_preserved(self):

        for previous, current in self.sources:

            self.assertEqual(
                previous["incomplete_result"],
                current["incomplete_result"],
            )

    def test_07_final_measurement_counts(self):

        counts = Counter()

        for _, current in self.sources:

            for key in (
                "standard_area_result",
                "recovery_result",
                "refinement_result",
            ):

                result = current[key]

                counts["standard_numeric"] += (
                    result["candidate_count"]
                )

                counts["standard_ambiguous"] += (
                    result["ambiguous_count"]
                )

            agricultural = current[
                "agricultural_result"
            ]

            counts["agricultural_numeric"] += (
                agricultural["candidate_count"]
            )

            counts["agricultural_ambiguous"] += (
                agricultural["ambiguous_count"]
            )

            counts["incomplete"] += current[
                "incomplete_result"
            ]["candidate_count"]

        self.assertEqual(
            dict(counts),
            {
                "standard_numeric": 63,
                "standard_ambiguous": 9,
                "agricultural_numeric": 33,
                "agricultural_ambiguous": 4,
                "incomplete": 1,
            },
        )

        self.assertEqual(
            sum(counts.values()),
            110,
        )

    def test_08_all_evidence_and_safety(self):

        for _, current in self.sources:

            text = current["raw_text"]

            for key in (
                "standard_area_result",
                "recovery_result",
                "refinement_result",
            ):

                self.assert_safe_result(
                    text,
                    current[key],
                )

    def test_09_no_cross_module_overlap(self):

        for _, current in self.sources:

            items = []

            for key in (
                "standard_area_result",
                "recovery_result",
                "refinement_result",
            ):

                items.extend(
                    all_candidates(current[key])
                )

            for index, first in enumerate(items):

                for second in items[index + 1:]:

                    self.assertFalse(
                        overlaps(first, second)
                    )

    def test_10_targeted_real_refinements(self):

        primary = self.indexed[
            (10, 18, "primary")
        ]["refinement_result"]

        self.assertIn(
            ("195.0963", "SQ_M"),
            numeric_values(primary),
        )

        secondary = self.indexed[
            (10, 18, "secondary")
        ]["refinement_result"]

        self.assertIn(
            "AMBIGUOUS_NUMERIC_PUNCTUATION",
            ambiguity_reasons(secondary),
        )

        for source in ("primary", "secondary"):

            result = self.indexed[
                (11, 11, source)
            ]["refinement_result"]

            self.assertIn(
                ("1157", "SQ_FT"),
                numeric_values(result),
            )


if __name__ == "__main__":

    unittest.main(verbosity=2)
