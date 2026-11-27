
import re

from notices.services.kannada_identifier_parser import (
    normalize_text,
    parse_kannada_identifiers
)


# ==================================================
# BACKWARD-COMPATIBLE NORMALIZATION
# ==================================================

def normalize_kannada_text(text):

    return normalize_text(text)


# ==================================================
# PROPERTY AREA EXTRACTION
# ==================================================

def extract_property_area(text):

    text = normalize_kannada_text(text)

    number = r"([0-9]+(?:\.[0-9]+)?)"

    patterns = [

        (
            number + r"\s*(?:ಚದರ\s*ಅಡಿ|ಚದರಡಿ|ಚ\.?\s*ಅ\.?)",
            "square_feet"
        ),

        (
            number + r"\s*(?:ಚದರ\s*ಮೀಟರ್|ಚ\.?\s*ಮೀ\.?)",
            "square_metres"
        ),

        (
            number + r"\s*ಚದರ\s*ಗಜ",
            "square_yards"
        ),

        (
            number + r"\s*ಎಕರೆ",
            "acres"
        ),

        (
            number + r"\s*ಗುಂಟ[ೆ]?",
            "guntas"
        )
    ]

    for pattern, unit in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1), unit

    return None, None


# ==================================================
# RESPONSE DEADLINE EXTRACTION
# ==================================================

def extract_response_deadline(text):

    text = normalize_kannada_text(text)

    match = re.search(

        r"(?<!\d)(\d{1,3})\s*"
        r"(?:\([^)]*\)\s*)?"
        r"ದಿನ(?:ಗಳ)?",

        text
    )

    if match:

        return match.group(1), "day"

    return None, None


# ==================================================
# SCALAR IDENTIFIER SELECTION
# ==================================================

def single_identifier(values):

    if len(values) == 1:

        return values[0]

    return None


# ==================================================
# MAIN KANNADA FIELD EXTRACTOR
# ==================================================

def extract_kannada_fields(raw_text):

    parsed = parse_kannada_identifiers(
        raw_text
    )

    subject = parsed["subject_identifiers"]

    subject_text = parsed["subject_text"]

    area, area_unit = extract_property_area(
        subject_text
    )

    deadline, deadline_unit = (
        extract_response_deadline(
            raw_text
        )
    )

    # ----------------------------------------------
    # Common field structure.
    # ----------------------------------------------

    fields = {

        "language": "kn",

        "survey_number": None,
        "survey_numbers": [],

        "site_number": None,
        "site_numbers": [],

        "khata_number": None,
        "khata_numbers": [],

        "pid_number": None,
        "pid_numbers": [],

        "document_number": None,
        "document_numbers": [],

        "assessment_number": None,
        "assessment_numbers": [],

        "registration_number": None,
        "registration_numbers": [],

        "property_number": None,
        "property_numbers": [],

        "flat_number": None,
        "flat_numbers": [],

        "plot_number": None,
        "plot_numbers": [],

        "subdivision_number": None,
        "subdivision_numbers": [],

        "hissa_number": None,
        "hissa_numbers": [],

        "municipal_number": None,
        "municipal_numbers": [],

        "tp_number": None,
        "tp_numbers": [],

        "khasra_number": None,
        "khasra_numbers": [],

        "property_area": area,

        "property_area_unit": area_unit,

        "land_share_percentage": None,

        "response_deadline": deadline,

        "response_deadline_unit": deadline_unit,

        "village": None,

        "hobli": None,

        "taluk": None,

        "district": None,

        "property_address": None,

        "party_names": None,

        "advocate_name": None,

        "notice_date": None,

        "publication_date": None,

        "sale_deed_date": None
    }

    # ----------------------------------------------
    # Integrate improved identifier values.
    # ----------------------------------------------

    for field, values in subject.items():

        fields[field] = list(values)

        if field.endswith("_numbers"):

            scalar_field = field[:-1]

            fields[scalar_field] = (
                single_identifier(values)
            )

    # ----------------------------------------------
    # Keep assessment numbers as evidence only
    # until the OCR validator supports them.
    # ----------------------------------------------

    fields["assessment_number"] = None

    fields["assessment_numbers"] = []

    # ----------------------------------------------
    # Preserve subject and boundary evidence.
    # ----------------------------------------------

    fields["subject_text"] = subject_text

    fields["boundary_text"] = (
        parsed["boundary_text"]
    )

    fields["boundary_identifiers"] = (
        parsed["boundary_identifiers"]
    )

    fields["identifier_evidence"] = (
        parsed["subject_evidence"]
    )

    fields["boundary_identifier_evidence"] = (
        parsed["boundary_evidence"]
    )

    fields["invalid_subject_identifiers"] = (
        parsed["invalid_subject_identifiers"]
    )

    fields["invalid_boundary_identifiers"] = (
        parsed["invalid_boundary_identifiers"]
    )

    # Preserve all parser candidates, including
    # assessment numbers not yet consolidated.

    fields["identifier_candidates"] = {

        key: list(values)

        for key, values in subject.items()
    }

    # ----------------------------------------------
    # Review requirements.
    # ----------------------------------------------

    review_reasons = list(
        parsed["review_reasons"]
    )

    if deadline is not None:

        review_reasons.append(
            "OCR-derived deadline requires verification"
        )

    if any(
        len(values) > 1
        for values in subject.values()
    ):

        review_reasons.append(
            "Multiple identifiers require "
            "property association verification"
        )

    if subject.get("assessment_numbers"):

        review_reasons.append(
            "Assessment numbers preserved as "
            "unvalidated candidates"
        )

    fields["requires_review"] = True

    fields["verified"] = False

    fields["review_reasons"] = list(
        dict.fromkeys(review_reasons)
    )

    return fields
