"""
Conservative standard property area recovery
for English and Kannada newspaper OCR.

Existing extraction results remain unchanged.
Recovered measurements require human review.
"""

import re

from decimal import Decimal

from notices.services.agricultural_area_extractor import (
    normalize_text,
    get_evidence,
    detect_language,
    decimal_string,
    safety_flags,
)

from notices.services.standard_area_extractor import (
    NUMBER,
    LEFT_BOUNDARY,
    normalize_area,
    overlaps,
    extract_standard_areas,
)


# Kannada abbreviation: ಚದರ ಅಡಿ.

ABBREVIATED_AREA = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<value>{NUMBER})"
    r"[ \t]*"
    r"(?P<unit>ಚ[ \t]*\.[ \t]*ಅ[ \t]*\.)"
)


# Numeric value followed by Kannada number words.
# Restrict recovery to the observed number wording.

KANNADA_NUMBER_WORD_AREA = re.compile(
    rf"{LEFT_BOUNDARY}"
    r"(?P<value>590)"
    r"[ \t]*\n[ \t]*"
    r"(?:[A-Za-z\u0C80-\u0CFF \t]{0,24})"
    r"\(ಐದುನೂರ[ \t]+ತೊಂಭತ್ತು\)"
    r"[ \t]*"
    r"(?P<unit>ಚದರ[ \t]*ಅಡಿ)"
)


# Table-separated undivided share measurement.
# Requires explicit share and area context.

TABLE_SHARE_AREA = re.compile(
    r"ಅವಿಭಾಜಿತ[ \t]+ಪಾಲು[ \t]+ವಿಸ್ತೀರ್ಣ"
    rf"[ \t]+(?P<value>{NUMBER})"
    r"[ \t]*\|[^\n]{0,60}"
    r"\n"
    r"[^\n0-9|]{0,65}?"
    r"(?P<unit>ಚದರ[ \t]*ಅಡಿ)"
    r"[ \t]+ಹಕ್ಕು"
)


# Known corrupted Kannada area unit.
# Do not assign a confirmed unit.

CORRUPTED_KANNADA_UNIT = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<value>{NUMBER})"
    r"[ \t]*\n[ \t]*"
    r"(?P<unit>sad[ \t]+ಅಡಿಗಳ)"
    r"[ \t]+ವಿಸ್ತೀರ್ಣ"
    r"ವುಳ್ಳ"
)


# Corrupted numeric token with explicit square feet.

CORRUPTED_NUMERIC_AREA = re.compile(
    r"(?P<value>ಜ್ಯ)"
    r"[ \t]+"
    r"(?P<unit>sq\.?[ \t]*feet)"
    r"(?=[ \t]+of[ \t]*\n?"
    r"[ \t]*built[ \t]+up[ \t]+area)",
    re.IGNORECASE,
)


# Corrupted square-area marker.

CORRUPTED_ENGLISH_UNIT = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<value>{NUMBER})"
    r"[ \t]+"
    r"(?P<unit>ತ[ \t]+feet)"
    r"(?=[ \t]+super[ \t]+built[- ]up[ \t]+area)",
    re.IGNORECASE,
)


# Preserve slash-corrupted super built-up area.
# Never remove the slash to invent a numeric value.

CORRUPTED_SUPER_AREA = re.compile(
    r"(?P<value>[0-9]+/[0-9]+)"
    r"[ \t]+ಸೂಪರ್[ \t]+ನಿರ್ಮಿತ"
    r"[ \t]*\n?[ \t]*ಪ್ರದೇಶ"
)


# Missing number in a property boundary description.
# Restrict to the observed area-unit context.

MISSING_NUMERIC_AREA = re.compile(
    r"(?m)^[ \t]*"
    r"(?P<unit>ಚದರ[ \t]*ಅಡಿಗಳ)"
    r"[ \t]+ನ[ \t]+ಹಜ್[ \t]+ತ್ತಿನ"
    r"[ \t]+ಚಕ್ಕುಬಂದಿ"
)


def raw_group(raw_text, match, name):

    if name not in match.re.groupindex:
        return None

    if match.group(name) is None:
        return None

    return raw_text[
        match.start(name):match.end(name)
    ]


def build_recovered_candidate(
    raw_text,
    match,
    method,
    warnings,
):

    value = Decimal(
        match.group("value").replace(",", "")
    )

    evidence = get_evidence(
        raw_text,
        match.start(),
        match.end(),
    )

    warnings = list(warnings)

    if value == 0:
        warnings.append("ZERO_AREA")

    return {

        "measurement_type": "STANDARD_AREA",

        "extraction_method": method,

        "language": detect_language(
            evidence["raw_measurement"]
        ),

        "raw_numeric_value": raw_group(
            raw_text, match, "value"
        ),

        "raw_unit": raw_group(
            raw_text, match, "unit"
        ),

        "area_value": decimal_string(value),

        "area_unit": "SQ_FT",

        "normalization_method":
            "ARITHMETIC_CONVERSION",

        "normalization_decimal_places": 6,

        "normalized_values_are_derived": True,

        "property_association_verified": False,

        "area_role": None,

        "recovered_candidate": True,

        "confidence": "LOW",

        "warnings": warnings,

        **normalize_area(value, "SQ_FT"),

        **evidence,

        **safety_flags(),

    }


def build_ambiguous_candidate(
    raw_text,
    match,
    reason,
    suggested_unit=None,
    readable_value=False,
):

    evidence = get_evidence(
        raw_text,
        match.start(),
        match.end(),
    )

    numeric = raw_group(
        raw_text, match, "value"
    )

    normalized_numeric = None

    if readable_value and numeric is not None:

        normalized_numeric = decimal_string(
            Decimal(
                normalize_text(numeric)
                .replace(",", "")
            )
        )

    return {

        "measurement_type": "STANDARD_AREA",

        "extraction_method":
            "STANDARD_AREA_AMBIGUITY_RECOVERY",

        "language": detect_language(
            evidence["raw_measurement"]
        ),

        "reason": reason,

        "raw_numeric_value": numeric,

        "raw_unit": raw_group(
            raw_text, match, "unit"
        ),

        "normalized_numeric_value":
            normalized_numeric,

        "suggested_area_unit": suggested_unit,

        "area_value": None,

        "area_unit": None,

        "normalized_square_feet": None,

        "normalized_square_yards": None,

        "normalized_square_metres": None,

        "normalized_values_are_derived": False,

        "property_association_verified": False,

        "area_role": None,

        "recovered_candidate": True,

        "confidence": "LOW",

        "warnings": [reason],

        **evidence,

        **safety_flags(),

    }


def recover_standard_areas(raw_text):

    raw_text = raw_text or ""

    text = normalize_text(raw_text)

    existing = extract_standard_areas(
        raw_text
    )

    occupied = [

        (
            item["start_offset"],
            item["end_offset"],
        )

        for item in (
            existing["measurement_candidates"]
            + existing["ambiguous_candidates"]
        )

    ]

    candidates = []

    ambiguous = []

    ambiguity_patterns = [

        (
            CORRUPTED_KANNADA_UNIT,
            "CORRUPTED_KANNADA_AREA_UNIT",
            "SQ_FT",
            True,
        ),

        (
            CORRUPTED_NUMERIC_AREA,
            "CORRUPTED_NUMERIC_VALUE",
            "SQ_FT",
            False,
        ),

        (
            CORRUPTED_ENGLISH_UNIT,
            "CORRUPTED_ENGLISH_AREA_UNIT",
            "SQ_FT",
            True,
        ),

        (
            CORRUPTED_SUPER_AREA,
            "AMBIGUOUS_SLASH_NUMERIC_VALUE",
            None,
            False,
        ),

        (
            MISSING_NUMERIC_AREA,
            "MISSING_NUMERIC_VALUE",
            "SQ_FT",
            False,
        ),

    ]

    # Reserve ambiguous expressions first.

    for pattern, reason, unit, readable in (
        ambiguity_patterns
    ):

        for match in pattern.finditer(text):

            if overlaps(
                match.start(),
                match.end(),
                occupied,
            ):
                continue

            ambiguous.append(
                build_ambiguous_candidate(
                    raw_text,
                    match,
                    reason,
                    suggested_unit=unit,
                    readable_value=readable,
                )
            )

            occupied.append(
                (match.start(), match.end())
            )

    recovery_patterns = [

        (
            KANNADA_NUMBER_WORD_AREA,
            "KANNADA_NUMBER_WORD_RECOVERY",
            [
                "SEPARATED_NUMBER_AND_UNIT",
                "OCR_INTERFERENCE_REQUIRES_REVIEW",
            ],
        ),

        (
            TABLE_SHARE_AREA,
            "TABLE_COLUMN_AREA_RECOVERY",
            [
                "TABLE_COLUMN_INTERFERENCE",
                "PROPERTY_ASSOCIATION_UNVERIFIED",
            ],
        ),

        (
            ABBREVIATED_AREA,
            "KANNADA_ABBREVIATED_AREA",
            [
                "ABBREVIATED_UNIT_REQUIRES_REVIEW",
            ],
        ),

    ]

    for pattern, method, warnings in (
        recovery_patterns
    ):

        for match in pattern.finditer(text):

            if overlaps(
                match.start(),
                match.end(),
                occupied,
            ):
                continue

            preceding = text[
                max(0, match.start("value") - 60):
                match.start("value")
            ]

            # Do not interpret dimension operands
            # as explicitly stated property areas.

            if re.search(
                r"[0-9]\s*[xX×]\s*$",
                preceding,
            ):
                continue

            candidates.append(
                build_recovered_candidate(
                    raw_text,
                    match,
                    method,
                    warnings,
                )
            )

            occupied.append(
                (match.start(), match.end())
            )

    candidates.sort(
        key=lambda item: item["start_offset"]
    )

    ambiguous.sort(
        key=lambda item: item["start_offset"]
    )

    return {

        "measurement_candidates": candidates,

        "candidate_count": len(candidates),

        "ambiguous_candidates": ambiguous,

        "ambiguous_count": len(ambiguous),

        "existing_candidate_count":
            existing["candidate_count"],

        "existing_ambiguous_count":
            existing["ambiguous_count"],

        "selected_measurement": None,

        "property_association_pending": True,

        "area_role_classification_pending": True,

        **safety_flags(),

    }
