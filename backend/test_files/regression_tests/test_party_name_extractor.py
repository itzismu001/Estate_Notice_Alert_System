
import json
import unittest

from pathlib import Path

from notices.services.party_name_extractor import (
    extract_party_candidates,
    validate_person_name
)


class PartyNameExtractorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        path = Path(
            "test_files/party_extraction_audit/"
            "results.json"
        )

        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        cls.records = {}

        cls.results = {}

        for record in data["results"]:

            key = (
                record["page_number"],
                record["region_number"]
            )

            cls.records[key] = record

            cls.results[key] = (
                extract_party_candidates(
                    record["raw_text"]
                )
            )

    def candidates(self, page, region):

        return {

            (
                candidate["name"],
                candidate["role"]
            )

            for candidate in self.results[
                (page, region)
            ]["party_candidates"]
        }

    def test_01_english_person(self):

        self.assertTrue(
            validate_person_name(
                "Ramesh Kumar",
                "en"
            )
        )

    def test_02_english_initials(self):

        self.assertTrue(
            validate_person_name(
                "M. Vasanth Kumar",
                "en"
            )
        )

    def test_03_kannada_person(self):

        self.assertTrue(
            validate_person_name(
                "ಕ್ರಿಸ್ಟೋಫರ್ ಜಾನ್ಸನ್",
                "kn"
            )
        )

    def test_04_kannada_initials(self):

        self.assertTrue(
            validate_person_name(
                "ಜಿ.ಡಿ. ದೇವರಾಜ್",
                "kn"
            )
        )

    def test_05_english_organization(self):

        self.assertFalse(
            validate_person_name(
                "Nandi Associates",
                "en"
            )
        )

    def test_06_kannada_organization(self):

        self.assertFalse(
            validate_person_name(
                "ಶ್ರೀ. ನಂದಿ ಅಸೋಸಿಯೇಟ್ಸ್",
                "kn"
            )
        )

    def test_07_kannada_sentence(self):

        self.assertFalse(
            validate_person_name(
                "ಅವರ ಸ್ವಂತ ಸಂಪೂರ್ಣ "
                "ಪ್ರಜ್ಞಾವಸ್ಥೆಯಲ್ಲಿದ್ದಾಗ",
                "kn"
            )
        )

    def test_08_property_phrase(self):

        self.assertFalse(
            validate_person_name(
                "of properties in Kodathi Village",
                "en"
            )
        )

    def test_09_numeric_identifier(self):

        self.assertFalse(
            validate_person_name(
                "Site 893",
                "en"
            )
        )

    def test_10_real_organization_excluded(self):

        self.assertNotIn(

            (
                "ಶ್ರೀ. ನಂದಿ ಅಸೋಸಿಯೇಟ್ಸ್",
                "ADVOCATE"
            ),

            self.candidates(10, 1)
        )

    def test_11_real_declarant(self):

        self.assertIn(

            (
                "ಕ್ರಿಸ್ಟೋಫರ್ ಜಾನ್ಸನ್",
                "DECLARANT"
            ),

            self.candidates(10, 11)
        )

    def test_12_real_testator(self):

        self.assertIn(

            (
                "ಜಿ.ಡಿ. ದೇವರಾಜ್",
                "TESTATOR"
            ),

            self.candidates(10, 11)
        )

    def test_13_real_false_declarant(self):

        self.assertNotIn(

            (
                "ಅವರ ಸ್ವಂತ ಸಂಪೂರ್ಣ "
                "ಪ್ರಜ್ಞಾವಸ್ಥೆಯಲ್ಲಿದ್ದಾಗ",
                "DECLARANT"
            ),

            self.candidates(10, 11)
        )

    def test_14_real_borrowers(self):

        candidates = self.candidates(10, 10)

        self.assertIn(
            ("ಜಿ ಸೌಮ್ಯ", "BORROWER"),
            candidates
        )

        self.assertIn(
            ("ತನುಜಾ", "BORROWER"),
            candidates
        )

    def test_15_real_co_applicant(self):

        self.assertIn(

            ("ಮುರಳಿ ಕೆ", "CO_APPLICANT"),

            self.candidates(10, 10)
        )

    def test_16_real_poa_executant(self):

        self.assertIn(

            (
                "KAVITA CHOWDHURY",
                "POA_EXECUTANT"
            ),

            self.candidates(10, 14)
        )

    def test_17_real_poa_holder(self):

        self.assertIn(

            ("Jayanta Das", "POA_HOLDER"),

            self.candidates(10, 14)
        )

    def test_18_real_advocate(self):

        self.assertIn(

            (
                "MYGAPULA SHARANYA",
                "ADVOCATE"
            ),

            self.candidates(10, 14)
        )

    def test_19_previous_owner(self):

        self.assertIn(

            (
                "Dinesh Kumar K",
                "PREVIOUS_OWNER"
            ),

            self.candidates(11, 3)
        )

    def test_20_contact_not_owner(self):

        candidates = self.candidates(11, 3)

        self.assertIn(

            (
                "MAHANTESH RAJENDRA GOANKAR",
                "CONTACT_PERSON"
            ),

            candidates
        )

        self.assertNotIn(

            (
                "MAHANTESH RAJENDRA GOANKAR",
                "OWNER"
            ),

            candidates
        )

    def test_21_real_contact_advocate(self):

        self.assertIn(

            ("M. Vasanth Kumar", "ADVOCATE"),

            self.candidates(11, 3)
        )

    def test_22_empty_text(self):

        result = extract_party_candidates("")

        self.assertEqual(
            result["party_candidates"],
            []
        )

    def test_23_deduplication(self):

        text = (
            "Ramesh Kumar, Advocate\n"
            "Ramesh Kumar, Advocate"
        )

        result = extract_party_candidates(text)

        self.assertEqual(
            result["candidate_count"],
            1
        )

    def test_24_original_evidence(self):

        for result in self.results.values():

            for candidate in result[
                "party_candidates"
            ]:

                self.assertTrue(
                    candidate["source_text"]
                )

                self.assertTrue(
                    candidate["evidence"]
                )

    def test_25_safety_flags(self):

        for result in self.results.values():

            self.assertTrue(
                result["requires_review"]
            )

            self.assertFalse(
                result["verified"]
            )

            self.assertFalse(
                result["approved_for_search"]
            )

            self.assertFalse(
                result["eligible_for_alert"]
            )

            for candidate in result[
                "party_candidates"
            ]:

                self.assertFalse(
                    candidate["verified"]
                )

                self.assertTrue(
                    candidate["requires_review"]
                )


if __name__ == "__main__":
    unittest.main()
