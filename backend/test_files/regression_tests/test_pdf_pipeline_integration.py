"""End-to-end PDF pipeline compatibility tests."""

import unittest

from pathlib import Path

from documents.services.pipeline import process_pdf


TEST_FILES = (
    Path(__file__).resolve().parents[1]
)


class TestPDFPipelineIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.direct = process_pdf(
            TEST_FILES / "sample_multiple_notices.pdf",
            multilingual=True,
        )

        cls.scanned = process_pdf(
            TEST_FILES / "sample_multiple_notices_scanned.pdf",
            multilingual=True,
        )

        cls.legacy = process_pdf(
            TEST_FILES / "sample_multiple_notices_scanned.pdf",
            multilingual=False,
        )

    def get_boxes(self, result):

        return [
            box
            for page in result["pages"]
            for box in page["bounding_boxes"]
        ]

    def test_01_direct_notice_count(self):

        self.assertEqual(
            self.direct["total_notices"], 2
        )

    def test_02_scanned_notice_count(self):

        self.assertEqual(
            self.scanned["total_notices"], 2
        )

    def test_03_legacy_compatibility(self):

        self.assertEqual(
            self.legacy["total_notices"], 2
        )

    def test_04_direct_detection_method(self):

        for box in self.get_boxes(self.direct):

            self.assertEqual(
                box["detection_method"],
                "multilingual_direct",
            )

    def test_05_fallback_detection_method(self):

        for box in self.get_boxes(self.scanned):

            self.assertEqual(
                box["detection_method"],
                "multilingual_ocr_fallback",
            )

    def test_06_fallback_report(self):

        self.assertTrue(
            self.scanned["pages"][0]["fallback_report"]
        )

    def test_07_pipeline_version(self):

        self.assertEqual(
            self.scanned["pipeline_version"],
            "multilingual_v2",
        )

    def test_08_no_failed_pages(self):

        for result in (
            self.direct,
            self.scanned,
            self.legacy,
        ):

            self.assertEqual(
                result["failed_pages"], 0
            )

    def test_09_no_partial_failures(self):

        for result in (
            self.direct,
            self.scanned,
        ):

            self.assertEqual(
                result["partial_failure_pages"], 0
            )

    def test_10_normalized_coordinates(self):

        for result in (
            self.direct,
            self.scanned,
        ):

            for box in self.get_boxes(result):

                bbox = box["normalized_bbox"]

                self.assertTrue(
                    0 <= bbox["x0"]
                    < bbox["x1"] <= 1
                )

                self.assertTrue(
                    0 <= bbox["y0"]
                    < bbox["y1"] <= 1
                )

    def test_11_survey_number_preservation(self):

        for result in (
            self.direct,
            self.scanned,
        ):

            numbers = set()

            for box in self.get_boxes(result):

                fields = box["notice_result"]["fields"]

                numbers.update(
                    fields.get("survey_numbers") or []
                )

            self.assertEqual(
                numbers,
                {"123/4", "456/2"},
            )

    def test_12_unverified_notice_safety(self):

        for result in (
            self.direct,
            self.scanned,
        ):

            for box in self.get_boxes(result):

                notice = box["notice_result"]

                self.assertTrue(
                    notice["retain_candidate"]
                )

                self.assertTrue(
                    notice["requires_review"]
                )

                self.assertFalse(
                    notice["verified"]
                )

                self.assertFalse(
                    notice["eligible_for_alert"]
                )

    def test_13_validation_evidence(self):

        for result in (
            self.direct,
            self.scanned,
        ):

            for box in self.get_boxes(result):

                notice = box["notice_result"]

                for key in (
                    "party_validation",
                    "location_validation",
                    "measurement_validation",
                    "deadline_validation",
                ):

                    self.assertIsNotNone(
                        notice[key]
                    )

    def test_14_ocr_provenance(self):

        for box in self.get_boxes(self.scanned):

            metadata = (
                box["notice_result"]["ocr_metadata"]
            )

            self.assertEqual(
                metadata["primary"]["language"],
                "kan+eng",
            )

            self.assertEqual(
                metadata["primary"]["method"],
                "page_ocr_text_blocks",
            )

    def test_15_original_text_preserved(self):

        for result in (
            self.direct,
            self.scanned,
        ):

            for box in self.get_boxes(result):

                self.assertTrue(
                    box["notice_result"]["raw_text"].strip()
                )


if __name__ == "__main__":

    unittest.main()
