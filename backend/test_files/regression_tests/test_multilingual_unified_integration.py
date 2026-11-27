"""
Permanent regression tests for multilingual notice
processing and unified party validation.
"""

import unittest

from copy import deepcopy
from unittest.mock import patch

from notices.services.multilingual_processor import (
    process_multilingual_notice,
)

from notices.services.unified_party_extractor import (
    extract_unified_parties,
)

from notices.services.location_ocr_validator import (
    validate_property_locations,
)


EXTRACTOR_PATH = (
    "notices.services.multilingual_processor."
    "extract_unified_parties"
)


ENGLISH_NOTICE = """
PUBLIC NOTICE

Notice is hereby given that my client intends
to purchase the property bearing Survey No. 123/4,
Site No. 25, situated at Bengaluru.

The property belongs to Mr. Ramesh Kumar.

Any person having any claim, right, title or
interest in the said property shall submit
objections within 15 days.

Advocate: Suresh Kumar
"""


KANNADA_NOTICE = """
ಸಾರ್ವಜನಿಕ ಪ್ರಕಟಣೆ

ಬೆಂಗಳೂರು ಜಿಲ್ಲೆಯ ಮಲ್ಲತ್ತಹಳ್ಳಿ ಗ್ರಾಮದ
ಸರ್ವೆ ನಂ. 24/2 ರಲ್ಲಿ ನಿವೇಶನ ಸಂಖ್ಯೆ 3
ಆಸ್ತಿಯನ್ನು ಖರೀದಿಸಲು ಉದ್ದೇಶಿಸಲಾಗಿದೆ.

ಸದರಿ ಆಸ್ತಿಯ ಮೇಲೆ ಯಾರಿಗಾದರೂ ಹಕ್ಕು,
ತಕರಾರು ಅಥವಾ ಆಕ್ಷೇಪಣೆ ಇದ್ದಲ್ಲಿ
15 ದಿನಗಳ ಒಳಗೆ ತಿಳಿಸಬೇಕು.
"""


RECRUITMENT_NOTICE = """
RECRUITMENT NOTICE

Applications are invited for software developers.
Candidates should submit their resumes by email.
Experience in Python is preferred.
"""


VALIDATORS = (

    "party_validation",

    "organization_validation",

    "legal_relationship_validation",

)


class MultilingualUnifiedIntegrationTests(
    unittest.TestCase
):

    def run_processor(
        self,
        primary,
        secondary=None,
        **kwargs,
    ):

        with patch(

            EXTRACTOR_PATH,

            wraps=extract_unified_parties,

        ) as extractor:

            result = process_multilingual_notice(

                primary,

                secondary,

                **kwargs,

            )

            return (

                result,

                extractor.call_count,

                extractor.call_args,

            )

    def assert_safe(self, item):

        self.assertIs(
            item["requires_review"],
            True,
        )

        for key in (

            "verified",

            "identity_merged",

            "ownership_verified",

            "legal_entitlement_verified",

            "approved_for_search",

            "eligible_for_alert",

        ):

            with self.subTest(flag=key):

                self.assertIs(
                    item[key],
                    False,
                )

    def english_result(self):

        return process_multilingual_notice(
            ENGLISH_NOTICE
        )

    def dual_result(self):

        return process_multilingual_notice(

            ENGLISH_NOTICE,

            ENGLISH_NOTICE.replace(
                "15 days",
                "14 days",
            ),

        )

    def test_01_english_notice_retained(self):

        result = self.english_result()

        self.assertEqual(
            result["decision"],
            "ACCEPT",
        )

        self.assertTrue(
            result["retain_candidate"]
        )

    def test_02_english_language_preserved(self):

        self.assertEqual(

            self.english_result()["language"],

            "en",

        )

    def test_03_kannada_notice_retained(self):

        result = process_multilingual_notice(
            KANNADA_NOTICE
        )

        self.assertEqual(
            result["decision"],
            "ACCEPT",
        )

        self.assertTrue(
            result["retain_candidate"]
        )

    def test_04_kannada_language_preserved(self):

        result = process_multilingual_notice(
            KANNADA_NOTICE
        )

        self.assertEqual(
            result["language"],
            "kn",
        )

    def test_05_english_extractor_called_once(self):

        _, calls, _ = self.run_processor(
            ENGLISH_NOTICE
        )

        self.assertEqual(calls, 1)

    def test_06_kannada_extractor_called_once(self):

        _, calls, _ = self.run_processor(
            KANNADA_NOTICE
        )

        self.assertEqual(calls, 1)

    def test_07_dual_ocr_extractor_called_once(self):

        _, calls, _ = self.run_processor(

            ENGLISH_NOTICE,

            ENGLISH_NOTICE,

        )

        self.assertEqual(calls, 1)

    def test_08_recruitment_notice_rejected(self):

        result = process_multilingual_notice(
            RECRUITMENT_NOTICE
        )

        self.assertEqual(
            result["decision"],
            "REJECT",
        )

        self.assertFalse(
            result["retain_candidate"]
        )

    def test_09_rejected_extractor_not_called(self):

        _, calls, _ = self.run_processor(
            RECRUITMENT_NOTICE
        )

        self.assertEqual(calls, 0)

    def test_10_rejected_validation_is_none(self):

        result = process_multilingual_notice(
            RECRUITMENT_NOTICE
        )

        self.assertIsNone(
            result["party_validation"]
        )

    def test_11_rejected_fields_remain_empty(self):

        result = process_multilingual_notice(
            RECRUITMENT_NOTICE
        )

        self.assertIsNone(
            result["fields"]
        )

        self.assertIsNone(
            result["location_validation"]
        )

    def test_12_empty_input_rejected(self):

        result, calls, _ = self.run_processor("")

        self.assertEqual(
            result["decision"],
            "REJECT",
        )

        self.assertEqual(calls, 0)

        self.assertIsNone(
            result["party_validation"]
        )

    def test_13_none_input_rejected(self):

        result, calls, _ = self.run_processor(None)

        self.assertEqual(
            result["decision"],
            "REJECT",
        )

        self.assertEqual(calls, 0)

        self.assertEqual(
            result["raw_text"],
            "",
        )

    def test_14_final_category_forwarded(self):

        result, _, arguments = self.run_processor(
            ENGLISH_NOTICE
        )

        self.assertEqual(

            arguments.kwargs["notice_category"],

            result["notice_category"],

        )

    def test_15_primary_text_forwarded_exactly(self):

        primary = ENGLISH_NOTICE + "\u200c"

        result, _, arguments = self.run_processor(
            primary
        )

        self.assertEqual(
            arguments.args[0],
            primary,
        )

        self.assertEqual(
            result["raw_text"],
            primary,
        )

    def test_16_secondary_text_forwarded_exactly(self):

        secondary = ENGLISH_NOTICE + "\u200d"

        result, _, arguments = self.run_processor(

            ENGLISH_NOTICE,

            secondary,

        )

        self.assertEqual(
            arguments.args[1],
            secondary,
        )

        self.assertEqual(
            result["secondary_raw_text"],
            secondary,
        )

    def test_17_english_direct_unified_equality(self):

        result = self.english_result()

        expected = extract_unified_parties(

            ENGLISH_NOTICE,

            notice_category=(
                result["notice_category"] or ""
            ),

        )

        self.assertEqual(

            result["party_validation"],

            expected,

        )

    def test_18_kannada_direct_unified_equality(self):

        result = process_multilingual_notice(
            KANNADA_NOTICE
        )

        expected = extract_unified_parties(

            KANNADA_NOTICE,

            notice_category=(
                result["notice_category"] or ""
            ),

        )

        self.assertEqual(

            result["party_validation"],

            expected,

        )

    def test_19_dual_ocr_direct_unified_equality(self):

        result = self.dual_result()

        expected = extract_unified_parties(

            result["raw_text"],

            result["secondary_raw_text"],

            notice_category=(
                result["notice_category"] or ""
            ),

        )

        self.assertEqual(

            result["party_validation"],

            expected,

        )

    def test_20_all_three_validators_available(self):

        unified = self.english_result()[
            "party_validation"
        ]

        for key in VALIDATORS:

            self.assertIn(
                key,
                unified,
            )

    def test_21_missing_secondary_preserved(self):

        result = self.english_result()

        unified = result["party_validation"]

        self.assertIsNone(
            result["secondary_raw_text"]
        )

        self.assertIsNone(
            unified["secondary"]
        )

        self.assertFalse(
            unified["secondary_available"]
        )

    def test_22_dual_ocr_availability_preserved(self):

        unified = self.dual_result()[
            "party_validation"
        ]

        self.assertTrue(
            unified["secondary_available"]
        )

        self.assertIsNotNone(
            unified["secondary"]
        )

    def test_23_validation_pending_flags_disabled(self):

        unified = self.english_result()[
            "party_validation"
        ]

        self.assertFalse(

            unified[
                "organization_validation_pending"
            ]

        )

        self.assertFalse(

            unified[
                "legal_relationship_validation_pending"
            ]

        )

    def test_24_location_validation_preserved(self):

        result = self.dual_result()

        expected = validate_property_locations(

            result["raw_text"],

            result["secondary_raw_text"],

        )

        self.assertEqual(

            result["location_validation"],

            expected,

        )

    def test_25_existing_output_fields_preserved(self):

        result = self.dual_result()

        required = {

            "detection",

            "fields",

            "raw_text",

            "language",

            "language_info",

            "decision",

            "notice_category",

            "retain_candidate",

            "requires_review",

            "verified",

            "eligible_for_alert",

            "primary_ocr_language",

            "secondary_ocr_language",

            "secondary_raw_text",

            "primary_result",

            "secondary_result",

            "ocr_validation",

            "location_validation",

            "party_validation",

        }
        required.update({
            "measurement_validation",
            "deadline_validation",
        })

        self.assertEqual(
            set(result),
            required,
        )

    def test_26_ocr_language_metadata_preserved(self):

        result = process_multilingual_notice(

            ENGLISH_NOTICE,

            ENGLISH_NOTICE,

            primary_ocr_language="kan+eng",

            secondary_ocr_language="eng",

        )

        self.assertEqual(

            result["primary_ocr_language"],

            "kan+eng",

        )

        self.assertEqual(

            result["secondary_ocr_language"],

            "eng",

        )

    def test_27_multilingual_root_safety(self):

        result = self.english_result()

        self.assertTrue(
            result["requires_review"]
        )

        self.assertFalse(
            result["verified"]
        )

        self.assertFalse(
            result["eligible_for_alert"]
        )

    def test_28_unified_and_validator_safety(self):

        unified = self.dual_result()[
            "party_validation"
        ]

        self.assert_safe(unified)

        for key in VALIDATORS:

            self.assert_safe(
                unified[key]
            )

            for group in unified[key]["comparisons"]:

                self.assert_safe(group)

    def test_29_unified_result_does_not_replace_fields(self):

        baseline = self.english_result()

        modified = deepcopy(
            baseline["party_validation"]
        )

        modified["test_marker"] = (
            "UNIFIED_VALIDATION_ONLY"
        )

        with patch(

            EXTRACTOR_PATH,

            return_value=modified,

        ):

            result = self.english_result()

        self.assertEqual(

            result["fields"],

            baseline["fields"],

        )

        self.assertEqual(

            result["location_validation"],

            baseline["location_validation"],

        )

        self.assertEqual(

            result["ocr_validation"],

            baseline["ocr_validation"],

        )

        self.assertEqual(

            result["party_validation"],

            modified,

        )

    def test_30_review_candidate_runs_extraction(self):

        result, calls, _ = self.run_processor(

            ENGLISH_NOTICE,

            RECRUITMENT_NOTICE,

        )

        self.assertEqual(
            result["decision"],
            "REVIEW",
        )

        self.assertTrue(
            result["retain_candidate"]
        )

        self.assertEqual(calls, 1)

        self.assertIsNotNone(
            result["party_validation"]
        )

        self.assertFalse(
            result["eligible_for_alert"]
        )


if __name__ == "__main__":

    unittest.main()
