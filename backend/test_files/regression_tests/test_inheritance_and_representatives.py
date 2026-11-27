import json
import unittest

from pathlib import Path
from copy import deepcopy

from notices.services.inheritance_party_extractor import (
    clean_name,
    extract_inheritance_parties,
)

from notices.services.legal_representative_extractor import (
    extract_legal_representatives,
)

from notices.services.ocr_legal_representative_extractor import (
    extract_ocr_legal_representatives,
)

from notices.services.hybrid_legal_representative_extractor import (
    extract_hybrid_legal_representatives,
    consolidate_associations,
)


ENGLISH_TEXT = (
    "Srinivasa Reddy, S/o Late Venkataswamy "
    "Reddy. Smt. Savithramma, Wio Srinivasa"
)

KANNADA_TEXT = (
    "(ಮೃತ ಸಾಲಗಾರರ ಆಸ್ತಿ) "
    "ಶ್ರೀಮತಿ ಜಿ.ಎನ್. ಜಮುನಾ ಬಾಯಿ "
    "ಲೇಟ್ ಜಿ.ಎನ್. ಗಿರಿಯಪ್ಪನವರ ಪತ್ನಿ, "
    "ಸ್ಥಿರಾಸ್ತಿಯ ಎಲ್ಲಾ ಭಾಗ ವಿಭಾಗಗಳನ್ನೊಳಗೊಂಡಂತೆ"
)

STANDARD_TEXT = """
23. Sri. Gopal, Since dead Represented by his LR's
23(a) Smt. Kamalamma, W/o Late Gopal
23(b) Smt. Manjula, D/o Late Gopal
23(c) Sri. Venkatesh, S/o Late Gopal
24. Sri. Ramesh, aged 45 years
"""

OCR_TEXT = """
Sri. Gopal, Since dead Represented by his LR's
DEFENDANT NO.23
24, SMT. KAMALAMMA, W/o. Late Gopal,
aged about 59 years ... DEFENDANT NO.23{a) /
RESPONDENT NO.24
25, SMT. MANJULA, 0/0, Late Gopal, aged
about 37 years ... DEFENDANT NO.23(b) /
RESPONDENT NO.25
26. SRI.VENKATESH, S/o Late Gopal, aged
about 39 years ... DEFENDANT NO.23 | c) /
RESPONDENT NO.26
"""


class InheritanceRegressionTests(unittest.TestCase):

    def setUp(self):

        self.english = extract_inheritance_parties(
            ENGLISH_TEXT
        )["party_candidates"]

        self.kannada = extract_inheritance_parties(
            KANNADA_TEXT
        )["party_candidates"]

    def test_01_english_name_boundary(self):

        self.assertEqual(
            clean_name(
                "Venkataswamy Reddy. Smt. Savithramma",
                "en",
            ),
            "Venkataswamy Reddy",
        )

    def test_02_english_deceased_person(self):

        self.assertTrue(any(
            item["name"] == "Venkataswamy Reddy"
            and item["role"] == "DECEASED_PERSON"
            for item in self.english
        ))

    def test_03_second_person_excluded(self):

        self.assertFalse(any(
            "Savithramma" in item["name"]
            for item in self.english
        ))

    def test_04_ambiguous_financial_party(self):

        self.assertTrue(any(
            item["name"] == "ಜಿ.ಎನ್. ಜಮುನಾ ಬಾಯಿ"
            and item["role"]
            == "FINANCIAL_PARTY_UNSPECIFIED"
            and item.get("role_ambiguous") is True
            for item in self.kannada
        ))

    def test_05_deceased_spouse(self):

        self.assertTrue(any(
            item["name"] == "ಜಿ.ಎನ್. ಗಿರಿಯಪ್ಪ"
            and item["role"] == "DECEASED_PERSON"
            for item in self.kannada
        ))

    def test_06_unsupported_borrower_excluded(self):

        self.assertFalse(any(
            item["role"] == "DECEASED_BORROWER"
            for item in self.kannada
        ))

    def test_07_no_unsupported_legal_heirs(self):

        self.assertFalse(any(
            item["role"] == "LEGAL_HEIR"
            for item in self.english + self.kannada
        ))

    def test_08_empty_input(self):

        result = extract_inheritance_parties("")

        self.assertEqual(
            result["party_candidates"],
            [],
        )

    def test_09_original_evidence(self):

        for item in self.english:

            self.assertIn(
                item["source_text"],
                ENGLISH_TEXT,
            )

        for item in self.kannada:

            self.assertIn(
                item["source_text"],
                KANNADA_TEXT,
            )

    def test_10_inheritance_safety(self):

        self.assertTrue(self.english)
        self.assertTrue(self.kannada)

        for item in self.english + self.kannada:

            self.assertTrue(item["requires_review"])

            for field in (
                "verified",
                "ownership_verified",
                "legal_entitlement_verified",
                "identity_merged",
                "approved_for_search",
                "eligible_for_alert",
            ):

                self.assertIs(item[field], False)


class LegalRepresentativeRegressionTests(
    unittest.TestCase
):

    def setUp(self):

        self.standard = (
            extract_legal_representatives(
                STANDARD_TEXT
            )["associations"]
        )

        self.ocr = (
            extract_ocr_legal_representatives(
                OCR_TEXT
            )["associations"]
        )

        self.hybrid = (
            extract_hybrid_legal_representatives(
                OCR_TEXT
            )["associations"]
        )

    def test_11_standard_count(self):

        self.assertEqual(len(self.standard), 3)

    def test_12_standard_relationships(self):

        self.assertEqual(
            {
                item["relationship"]
                for item in self.standard
            },
            {"WIFE", "DAUGHTER", "SON"},
        )

    def test_13_unrelated_defendant_excluded(self):

        self.assertNotIn(
            "Ramesh",
            {
                item["representative_name"]
                for item in self.standard
            },
        )

    def test_14_ocr_count(self):

        self.assertEqual(len(self.ocr), 3)

    def test_15_ocr_defendant_numbers(self):

        self.assertEqual(
            {
                item["representative_entry_number"]
                for item in self.ocr
            },
            {"23(a)", "23(b)", "23(c)"},
        )

    def test_16_ocr_respondent_numbers(self):

        self.assertEqual(
            {
                item["respondent_number"]
                for item in self.ocr
            },
            {"24", "25", "26"},
        )

    def test_17_ambiguous_relationship(self):

        item = next(
            item for item in self.ocr
            if item["representative_name"]
            == "MANJULA"
        )

        self.assertIsNone(item["relationship"])

        self.assertTrue(
            item["relationship_uncertain"]
        )

    def test_18_original_ocr_labels(self):

        self.assertEqual(
            {
                item["raw_defendant_label"]
                for item in self.ocr
            },
            {
                "DEFENDANT NO.23{a)",
                "DEFENDANT NO.23(b)",
                "DEFENDANT NO.23 | c)",
            },
        )

    def test_19_missing_representation(self):

        text = OCR_TEXT.replace(
            "Since dead Represented by his LR's",
            "aged 70 years",
        )

        result = extract_hybrid_legal_representatives(
            text
        )

        self.assertEqual(
            result["association_count"],
            0,
        )

    def test_20_mismatched_defendant(self):

        text = OCR_TEXT.replace(
            "DEFENDANT NO.23{a)",
            "DEFENDANT NO.24(a)",
        )

        result = extract_ocr_legal_representatives(
            text
        )

        self.assertFalse(any(
            item["representative_name"]
            == "KAMALAMMA"
            for item in result["associations"]
        ))

    def test_21_contradictory_respondent(self):

        text = OCR_TEXT.replace(
            "RESPONDENT NO.24",
            "RESPONDENT NO.99",
        )

        result = extract_ocr_legal_representatives(
            text
        )

        self.assertFalse(any(
            item["representative_name"]
            == "KAMALAMMA"
            for item in result["associations"]
        ))

    def test_22_hybrid_preservation(self):

        self.assertEqual(len(self.hybrid), 3)

        for old in self.ocr:

            self.assertTrue(any(
                item["representative_name"]
                == old["representative_name"]
                and item["source_text"]
                == old["source_text"]
                for item in self.hybrid
            ))

    def test_23_duplicate_consolidation(self):

        sample = self.standard[0]

        duplicate = deepcopy(sample)

        duplicate["association_method"] = (
            "SECOND_METHOD"
        )

        result = consolidate_associations(
            [sample, duplicate]
        )

        self.assertEqual(len(result), 1)

        self.assertEqual(
            len(result[0]["evidence"]),
            2,
        )

        self.assertEqual(
            len(result[0]["association_methods"]),
            2,
        )

    def test_24_relationship_conflict(self):

        sample = self.standard[0]

        conflict = deepcopy(sample)

        conflict["relationship"] = "DAUGHTER"

        result = consolidate_associations(
            [sample, conflict]
        )

        self.assertEqual(len(result), 1)

        self.assertTrue(
            result[0]["relationship_conflict"]
        )

        self.assertIsNone(
            result[0]["relationship"]
        )

    def test_25_identity_conflict(self):

        sample = self.standard[0]

        different = deepcopy(sample)

        different["representative_name"] = (
            "Lakshmi"
        )

        result = consolidate_associations(
            [sample, different]
        )

        self.assertEqual(len(result), 2)

        self.assertTrue(all(
            item["identity_conflict"]
            and not item["identity_merged"]
            for item in result
        ))

    def test_26_separate_source_positions(self):

        sample = self.standard[0]

        separate = deepcopy(sample)

        separate["representative_start_line"] += 10

        result = consolidate_associations(
            [sample, separate]
        )

        self.assertEqual(len(result), 2)

    def test_27_empty_hybrid_input(self):

        result = extract_hybrid_legal_representatives(
            ""
        )

        self.assertEqual(
            result["association_count"],
            0,
        )

    def test_28_representative_safety(self):

        self.assertTrue(self.hybrid)

        for item in self.hybrid:

            self.assertTrue(item["requires_review"])

            for field in (
                "verified",
                "ownership_verified",
                "legal_entitlement_verified",
                "identity_merged",
                "approved_for_search",
                "eligible_for_alert",
            ):

                self.assertIs(item[field], False)


class RealNewspaperRegressionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        root = Path(__file__).resolve().parents[1]

        cls.data = json.loads(
            (
                root
                / "inheritance_regex_correction"
                / "results.json"
            ).read_text(encoding="utf-8")
        )

    def test_29_real_inheritance_regression(self):

        notices = 0
        sources = 0
        candidates = 0

        for record in self.data["results"]:

            notices += 1

            for field, source in (
                record["sources"].items()
            ):

                sources += 1

                with self.subTest(
                    page=record["page_number"],
                    region=record["region_number"],
                    source=field,
                ):

                    result = (
                        extract_inheritance_parties(
                            source["raw_text"]
                        )
                    )

                    self.assertEqual(
                        result,
                        source["updated"],
                    )

                    candidates += len(
                        result["party_candidates"]
                    )

        self.assertEqual(notices, 30)
        self.assertEqual(sources, 54)
        self.assertEqual(candidates, 54)

    def test_30_real_representative_regression(self):

        total = 0
        sources = 0
        target = []

        for record in self.data["results"]:

            region = (
                record["page_number"],
                record["region_number"],
            )

            for field, source in (
                record["sources"].items()
            ):

                sources += 1

                result = (
                    extract_hybrid_legal_representatives(
                        source["raw_text"]
                    )
                )

                items = result["associations"]

                total += len(items)

                if (
                    region == (7, 1)
                    and field == "raw_text"
                ):

                    target = items

                else:

                    self.assertEqual(items, [])

        self.assertEqual(sources, 54)
        self.assertEqual(total, 3)

        self.assertEqual(
            {
                (
                    item["representative_name"],
                    item["representative_entry_number"],
                    item["respondent_number"],
                    item["relationship"],
                )
                for item in target
            },
            {
                ("KAMALAMMA", "23(a)", "24", "WIFE"),
                ("MANJULA", "23(b)", "25", None),
                ("VENKATESH", "23(c)", "26", "SON"),
            },
        )

        self.assertTrue(all(
            item["deceased_person"] == "Gopal"
            and item["requires_review"]
            and not item["verified"]
            and not item["eligible_for_alert"]
            for item in target
        ))


if __name__ == "__main__":

    unittest.main()
