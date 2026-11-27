"""
Additional Kannada area abbreviation recovery.

Preserve original OCR punctuation and evidence.
Never silently repair malformed numeric values.
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

from notices.services.standard_area_recovery import (
    recover_standard_areas,
)


SQUARE_METRE_ABBREVIATION = (
    r"ಚ[ \t]*\.[ \t]*ಮೀ[ \t]*\."
)

SQUARE_FEET_ABBREVIATION = (
    r"ಚ[ \t]*\.[ \t]*ಅ[ \t]*\."
)


METRE_AREA_PATTERN = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<value>{NUMBER})"
    r"[ \t]*(?:\n[ \t]*)?"
    rf"(?P<unit>{SQUARE_METRE_ABBREVIATION})"
)


# A comma followed by four or more digits is
# not accepted as standard thousands grouping.

MALFORMED_METRE_AREA = re.compile(
    rf"{LEFT_BOUNDARY}"
    r"(?P<value>[0-9]+,[0-9]{4,})"
    r"[ \t]*(?:\n[ \t]*)?"
    rf"(?P<unit>{SQUARE_METRE_ABBREVIATION})"
)


# Recover the observed separated boundary-area
# expression using tightly bounded OCR context.

SEPARATED_FEET_AREA = re.compile(
    r"ಅಳತೆ[ \t]+"
    rf"(?P<value>{NUMBER})"
    r"[ \t]*\n[ \t]*"
    r"ರಂದುಇದಚೆ\.[ \t]*"
    rf"(?P<unit>{SQUARE_FEET_ABBREVIATION})"
    r"(?=[ \t]+ಪೂರ್ವಕ್ಕೆ)"
)


def raw_group(raw_text, match, name):

    return raw_text[
        match.start(name):match.end(name)
    ]


def build_numeric_candidate(
    raw_text,
    match,
    unit,
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

        "area_unit": unit,

        "normalization_method":
            "ARITHMETIC_CONVERSION",

        "normalization_decimal_places": 6,

        "normalized_values_are_derived": True,

        "property_association_verified": False,

        "area_role": None,

        "recovered_candidate": True,

        "confidence": "LOW",

        "warnings": warnings,

        **normalize_area(value, unit),

        **evidence,

        **safety_flags(),

    }


def build_ambiguous_candidate(raw_text, match):

    evidence = get_evidence(
        raw_text,
        match.start(),
        match.end(),
    )

    return {

        "measurement_type": "STANDARD_AREA",

        "extraction_method":
            "KANNADA_ABBREVIATION_AMBIGUITY",

        "language": detect_language(
            evidence["raw_measurement"]
        ),

        "reason":
            "AMBIGUOUS_NUMERIC_PUNCTUATION",

        "raw_numeric_value": raw_group(
            raw_text, match, "value"
        ),

        "raw_unit": raw_group(
            raw_text, match, "unit"
        ),

        "normalized_numeric_value": None,

        "suggested_area_unit": "SQ_M",

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

        "warnings": [
            "AMBIGUOUS_NUMERIC_PUNCTUATION",
            "DO_NOT_AUTOMATICALLY_REPLACE_COMMA",
        ],

        **evidence,

        **safety_flags(),

    }


def refine_kannada_areas(raw_text):

    raw_text = raw_text or ""

    text = normalize_text(raw_text)

    standard = extract_standard_areas(raw_text)

    recovery = recover_standard_areas(raw_text)

    existing = (

        standard["measurement_candidates"]

        + standard["ambiguous_candidates"]

        + recovery["measurement_candidates"]

        + recovery["ambiguous_candidates"]

    )

    occupied = [

        (
            item["start_offset"],
            item["end_offset"],
        )

        for item in existing

    ]

    candidates = []

    ambiguous = []

    # Preserve malformed values before attempting
    # numeric extraction.

    for match in MALFORMED_METRE_AREA.finditer(text):

        if overlaps(
            match.start(),
            match.end(),
            occupied,
        ):
            continue

        ambiguous.append(
            build_ambiguous_candidate(
                raw_text, match
            )
        )

        occupied.append(
            (match.start(), match.end())
        )

    patterns = [

        (
            METRE_AREA_PATTERN,
            "SQ_M",
            "KANNADA_SQUARE_METRE_ABBREVIATION",
            [
                "ABBREVIATED_UNIT_REQUIRES_REVIEW",
            ],
        ),

        (
            SEPARATED_FEET_AREA,
            "SQ_FT",
            "KANNADA_SEPARATED_ABBREVIATION",
            [
                "SEPARATED_NUMBER_AND_UNIT",
                "OCR_INTERFERENCE_REQUIRES_REVIEW",
                "POSSIBLE_REPEATED_MEASUREMENT",
            ],
        ),

    ]

    for pattern, unit, method, warnings in patterns:

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

            if re.search(
                r"[0-9]\s*[xX×]\s*$",
                preceding,
            ):
                continue

            candidates.append(
                build_numeric_candidate(
                    raw_text,
                    match,
                    unit,
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

        "existing_candidate_count": len(
            standard["measurement_candidates"]
            + recovery["measurement_candidates"]
        ),

        "existing_ambiguous_count": len(
            standard["ambiguous_candidates"]
            + recovery["ambiguous_candidates"]
        ),

        "selected_measurement": None,

        "property_association_pending": True,

        "area_role_classification_pending": True,

        **safety_flags(),

    }
