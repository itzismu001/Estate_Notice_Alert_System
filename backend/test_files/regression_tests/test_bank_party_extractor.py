"""
Permanent regression tests for financial party extraction.

Uses cached newspaper OCR to avoid running Tesseract
during every regression test.
"""

import json
import unittest

from pathlib import Path
from collections import Counter

from notices.services.bank_party_extractor import (
    extract_bank_party_candidates,
    integrate_recovered_bank_parties,
)

from notices.services.bank_party_recovery import (
    recover_bank_parties,
)

from notices.services.bank_hybrid_header_detector import (
    detect_hybrid_financial_headers,
)


class TestBankPartyExtractor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        base = Path("test_files")

        audit = json.loads(
            (base / "bank_party_audit/results.json")
            .read_text(encoding="utf-8")
        )

        baseline = json.loads(
            (
                base
                / "bank_recovery_integration/results.json"
            ).read_text(encoding="utf-8")
        )

        cls.records = {
            (
                item["page_number"],
                item["region_number"],
            ): item
            for item in audit["results"]
            if item["notice_category"].startswith(
                "SECURED_PROPERTY_"
            )
        }

        cls.baseline = {
            (
                item["page_number"],
                item["region_number"],
            ): item
            for item in baseline["results"]
        }

        cls.results = {}

        for key, record in cls.records.items():

            for field in [
                "raw_text",
                "secondary_raw_text",
            ]:

                cls.results[(key, field)] = (
                    extract_bank_party_candidates(
                        record.get(field) or "",
                        record["notice_category"],
                    )
                )

    def get_result(
        self,
        page,
        region,
        source="raw_text",
    ):

        return self.results[
            ((page, region), source)
        ]

    def get_candidates(self, page, region):

        return self.get_result(
            page, region
        )["party_candidates"]

    def get_recovery(self, page, region):

        return recover_bank_parties(
            self.records[
                (page, region)
            ]["raw_text"]
        )

    def assert_candidate(
        self,
        page,
        region,
        name,
        role,
    ):

        self.assertTrue(
            any(
                item["name"] == name
                and item["role"] == role
                for item in self.get_candidates(
                    page, region
                )
            ),
            f"Missing candidate: {name} {role}",
        )

    def test_01_non_bank_notice_excluded(self):

        result = extract_bank_party_candidates(
            "Public notice regarding property ownership",
            "ESTATE_PROPERTY_NOTICE",
        )

        self.assertFalse(result["applicable"])
        self.assertEqual(result["party_candidates"], [])

    def test_02_missing_category_excluded(self):

        result = extract_bank_party_candidates(
            "Sample text",
            None,
        )

        self.assertFalse(result["applicable"])

    def test_03_empty_bank_notice(self):

        result = extract_bank_party_candidates(
            "",
            "SECURED_PROPERTY_DEMAND",
        )

        self.assertTrue(result["applicable"])
        self.assertEqual(result["candidate_count"], 0)

    def test_04_all_bank_categories_supported(self):

        for category in [
            "SECURED_PROPERTY_DEMAND",
            "SECURED_PROPERTY_POSSESSION",
            "SECURED_PROPERTY_AUCTION",
            "SECURED_PROPERTY_OTHER",
        ]:

            with self.subTest(category=category):

                result = extract_bank_party_candidates(
                    "",
                    category,
                )

                self.assertTrue(result["applicable"])

    def test_05_all_nine_bank_notices_present(self):

        self.assertEqual(len(self.records), 9)

    def test_06_all_eighteen_ocr_sources_present(self):

        self.assertEqual(len(self.results), 18)

    def test_07_hybrid_heading_coverage(self):

        for key, record in self.records.items():

            for field in [
                "raw_text",
                "secondary_raw_text",
            ]:

                with self.subTest(
                    region=key,
                    source=field,
                ):

                    headers = (
                        detect_hybrid_financial_headers(
                            record[field]
                        )
                    )

                    self.assertTrue(headers)

    def test_08_person_row_not_consumed(self):

        headers = detect_hybrid_financial_headers(
            self.records[(10, 10)]["raw_text"]
        )

        self.assertFalse(
            any(
                item["start_line"] <= 20
                <= item["end_line"]
                for item in headers
            )
        )

    def test_09_narrative_heading_rejected(self):

        headers = detect_hybrid_financial_headers(
            self.records[(10, 19)][
                "secondary_raw_text"
            ]
        )

        self.assertFalse(
            any(
                item["start_line"] < 9
                for item in headers
            )
        )

    def test_10_heading_fragments_merged(self):

        headers = detect_hybrid_financial_headers(
            self.records[(10, 20)]["raw_text"]
        )

        self.assertTrue(
            any(
                item["start_line"] <= 11
                and item["end_line"] >= 13
                for item in headers
            )
        )

    def test_11_legacy_heading_preserved(self):

        headers = detect_hybrid_financial_headers(
            self.records[(11, 8)]["raw_text"]
        )

        self.assertTrue(
            any(
                "LEGACY" in item["detection_methods"]
                for item in headers
            )
        )

    def test_12_incorrect_coapplicant_role_rejected(self):

        self.assertFalse(
            any(
                item["name"] == "ಜಿ ಸೌಮ್ಯ"
                and item["role"] == "CO_APPLICANT"
                for item in self.get_candidates(
                    10, 10
                )
            )
        )

    def test_13_loan_account_party_recovery(self):

        for name in [
            "ಸೈಫುಲ್ಲಾ",
            "ರವೂಫ್ ಖಾನ್",
            "ಮುಜಾಸಿಮ್",
        ]:

            self.assert_candidate(
                10, 18, name,
                "FINANCIAL_PARTY_UNSPECIFIED",
            )

    def test_14_ambiguous_name_boundaries(self):

        candidates = self.get_recovery(10, 18)

        ambiguous = {
            item["name"]
            for item in candidates
            if item["name_boundary_ambiguous"]
        }

        self.assertEqual(
            ambiguous,
            {"ಸೈಫುಲ್ಲಾ", "ರವೂಫ್ ಖಾನ್"},
        )

    def test_15_multiline_party_recovery(self):

        self.assert_candidate(
            10, 19,
            "ಭಾಗ್ಯಮ್ಮ",
            "FINANCIAL_PARTY_UNSPECIFIED",
        )

    def test_16_numbered_account_party(self):

        self.assert_candidate(
            10, 20,
            "ಎ ರಮೇಶ್",
            "FINANCIAL_PARTY_UNSPECIFIED",
        )

    def test_17_numbered_auction_parties(self):

        for name in [
            "ಜನ್ ಕೆ ಜಿ",
            "ಸ್ವಪ್ನಾ",
            "ಪ್ರಶಾಂತ್ ಎಂ.ಎಸ್",
            "ವಿಶಾಲ್ ರಾಜ್",
        ]:

            self.assert_candidate(
                11, 12, name,
                "FINANCIAL_PARTY_UNSPECIFIED",
            )

    def test_18_explicit_borrower_role(self):

        self.assert_candidate(
            11, 13,
            "ರವಿತೇಜ ಪಿ",
            "BORROWER",
        )

    def test_19_explicit_coapplicant_role(self):

        self.assert_candidate(
            11, 13,
            "ಪೀತಾ ಅಂಕಮ್ಮ",
            "CO_APPLICANT",
        )

    def test_20_redundant_unspecified_role_removed(self):

        self.assertFalse(
            any(
                item["name"] == "ರವಿತೇಜ ಪಿ"
                and item["role"]
                == "FINANCIAL_PARTY_UNSPECIFIED"
                for item in self.get_candidates(
                    11, 13
                )
            )
        )

    def test_21_non_person_text_excluded(self):

        forbidden = [
            "ನೀರು",
            "ನೈರ್ಮಲ್ಯ ವ್ಯವಸ್ಥೆ",
            "ಒಟ್ಟು",
            "ಅನ್ನು ಹೊಸದಾಗಿ ನೀಡಲಾಗುತ್ತಿದೆ",
        ]

        for result in self.results.values():

            for item in result["party_candidates"]:

                for value in forbidden:

                    self.assertNotIn(
                        value,
                        item["name"],
                    )

    def test_22_candidate_safety_flags(self):

        for result in self.results.values():

            for item in result["party_candidates"]:

                self.assertTrue(
                    item["requires_review"]
                )

                self.assertFalse(item["verified"])

                self.assertFalse(
                    item["approved_for_search"]
                )

                self.assertFalse(
                    item["eligible_for_alert"]
                )

    def test_23_recovery_evidence_preserved(self):

        count = 0

        for result in self.results.values():

            for item in result["party_candidates"]:

                if not item.get(
                    "extraction_method", ""
                ).startswith("RECOVERY_"):

                    continue

                count += 1

                for field in [
                    "source_text",
                    "start_line",
                    "end_line",
                    "heading_evidence",
                    "evidence",
                ]:

                    self.assertTrue(item.get(field))

                self.assertFalse(
                    item["identity_merged"]
                )

                self.assertLessEqual(
                    item["start_line"],
                    item["end_line"],
                )

        self.assertGreaterEqual(count, 22)

    def test_24_organization_candidates_preserved(self):

        for (key, field), result in (
            self.results.items()
        ):

            expected = self.baseline[key][
                "sources"
            ][field]["organization_candidates"]

            actual = result[
                "organization_candidates"
            ]

            for organization in expected:

                self.assertIn(
                    organization,
                    actual,
                )

    def test_25_existing_candidate_baseline_preserved(self):

        def key(item):

            return (
                item["name"].casefold(),
                item["role"],
                item["language"],
            )

        target_name = "ಜಿ.ಎನ್. ಜಮುನಾ ಬಾಯಿ"

        correction_count = 0

        for (region, field), result in (
            self.results.items()
        ):

            previous = self.baseline[region][
                "sources"
            ][field]["party_candidates"]

            current = result["party_candidates"]

            expected = Counter()

            for item in previous:

                candidate_key = key(item)

                # Permit only the intentional correction
                # validated against the original OCR.

                if (
                    region == (10, 17)

                    and field in (
                        "raw_text",
                        "secondary_raw_text",
                    )

                    and item["name"] == target_name

                    and item["role"] == "DECEASED_BORROWER"

                    and item["language"] == "kn"

                    and item["extraction_method"]
                    == "BANK_DECEASED_BORROWER_CONTEXT"
                ):

                    candidate_key = (
                        target_name.casefold(),
                        "FINANCIAL_PARTY_UNSPECIFIED",
                        "kn",
                    )

                    correction_count += 1

                    corrected = [

                        candidate

                        for candidate in current

                        if key(candidate) == candidate_key

                    ]

                    self.assertEqual(
                        len(corrected),
                        1,
                    )

                    candidate = corrected[0]

                    self.assertIs(
                        candidate["role_ambiguous"],
                        True,
                    )

                    self.assertEqual(
                        candidate["extraction_method"],
                        "BANK_DECEASED_PROPERTY_CONTEXT",
                    )

                    self.assertEqual(
                        candidate["source_text"],
                        item["source_text"],
                    )

                    self.assertFalse(any(

                        other["name"] == target_name

                        and other["role"]
                        == "DECEASED_BORROWER"

                        for other in current

                    ))

                    self.assertIs(
                        candidate["requires_review"],
                        True,
                    )

                    for safety_field in (
                        "verified",
                        "approved_for_search",
                        "eligible_for_alert",
                    ):

                        self.assertIs(
                            candidate[safety_field],
                            False,
                        )

                expected[candidate_key] += 1

            actual = Counter(
                key(item)
                for item in current
            )

            # Preserve every expected candidate.

            self.assertFalse(
                expected - actual,
                f"Candidate lost: {region} {field}",
            )

            # Reject unexpected candidate changes.

            self.assertFalse(
                actual - expected,
                f"Unexpected candidate: {region} {field}",
            )

            self.assertEqual(
                result["candidate_count"],
                len(current),
            )

        # Exactly two intentional corrections:
        # primary and secondary OCR.

        self.assertEqual(
            correction_count,
            2,
        )


if __name__ == "__main__":
    unittest.main()
