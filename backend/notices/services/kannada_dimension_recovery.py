"""
Recover shortened Kannada directional dimensions.

Preserve existing extraction results.
Never automatically calculate property area.
"""

import re

from notices.services.agricultural_area_extractor import (
    normalize_text,
    get_evidence,
    detect_language,
    extract_agricultural_areas,
)

from notices.services.incomplete_measurement_detector import (
    detect_incomplete_measurements,
)

from notices.services.directional_dimension_extractor import (
    NUMBER,
    LINEAR_UNIT,
    build_length,
    dimension_flags,
    existing_area_spans,
    extract_directional_dimensions,
    overlaps,
)


# ==================================================
# KANNADA DIRECTION PATTERNS
# ==================================================

KANNADA_DIRECTIONS = {

    "EAST_WEST": (

        r"ಪೂರ್ವ(?:ದಿಂದ\s*|"
        r"\s*[-–—/]\s*|\s+)"

        r"ಪಶ್ಚಿಮ(?:ಕ್ಕೆ)?"

        r"|ಪಶ್ಚಿಮ(?:ದಿಂದ\s*|"
        r"\s*[-–—/]\s*|\s+)"

        r"ಪೂರ್ವ(?:ಕ್ಕೆ)?"

    ),

    "NORTH_SOUTH": (

        r"ಉತ್ತರ(?:ದಿಂದ\s*|"
        r"\s*[-–—/]\s*|\s+)"

        r"(?:ದಕ್ಷಿಣ|ದಕಿಣ)(?:ಕ್ಕೆ)?"

        r"|ದಕ್ಷಿಣ(?:ದಿಂದ\s*|"
        r"\s*[-–—/]\s*|\s+)"

        r"ಉತ್ತರ(?:ಕ್ಕೆ)?"

    ),

}


DIRECTION_GROUP = "|".join(

    rf"(?P<{direction}>{pattern})"

    for direction, pattern
    in KANNADA_DIRECTIONS.items()

)


RECOVERY_PATTERN = re.compile(

    rf"(?P<direction>{DIRECTION_GROUP})"

    r"\s*[:=\-–]?\s*"

    r"(?:(?:ಅಳತೆ|ವಿಸ್ತೀರ್ಣ)"
    r"\s*[:=\-]?\s*)?"

    rf"(?P<value>{NUMBER})"

    rf"\s*(?P<unit>{LINEAR_UNIT})"

    r"(?:ಗಳು|ಗಳ)?"

    r"(?![\w²])",

    re.IGNORECASE,

)


# Prevent linear measurements from being
# incorrectly extracted from area expressions.

AREA_SUFFIX = re.compile(

    r"^[ \t]*(?:ಚದರ|ವರ್ಗ|square\b|sq\b|²)",

    re.IGNORECASE,

)


ROAD_SUFFIX = re.compile(

    r"^[ \t]*(?:wide[ \t]+)?"
    r"(?:road\b|street\b|ರಸ್ತೆ|ರಸ್ತ|ರಸ್ಥೆ)",

    re.IGNORECASE,

)


def get_direction(match):

    for direction in KANNADA_DIRECTIONS:

        if match.group(direction) is not None:

            return direction

    return None


def raw_group(raw_text, match, name):

    return raw_text[
        match.start(name):match.end(name)
    ]


def build_recovered_candidate(raw_text, match):

    evidence = get_evidence(

        raw_text,

        match.start(),

        match.end(),

    )

    measurement = build_length(

        match.group("value"),

        match.group("unit"),

    )

    warnings = [

        "RECOVERED_KANNADA_DIRECTION",

        "DIRECTION_REQUIRES_REVIEW",

    ]

    if measurement["dimension_value"] == "0":

        warnings.append("ZERO_DIMENSION")

    return {

        "measurement_type": "LINEAR_DIMENSION",

        "extraction_method":
            "KANNADA_DIRECTIONAL_RECOVERY",

        "direction": get_direction(match),

        "language": detect_language(
            evidence["raw_measurement"]
        ),

        "raw_direction": raw_group(
            raw_text, match, "direction"
        ),

        "raw_numeric_value": raw_group(
            raw_text, match, "value"
        ),

        "raw_unit": raw_group(
            raw_text, match, "unit"
        ),

        **measurement,

        "normalization_method":
            "ARITHMETIC_CONVERSION",

        "normalized_values_are_derived": True,

        "recovered_candidate": True,

        "confidence": "LOW",

        "dimension_context_role":
            "PROPERTY_DIMENSION",

        "context_classification_verified": False,

        "eligible_for_area_calculation": False,

        "warnings": warnings,

        **evidence,

        **dimension_flags(),

    }


# ==================================================
# MAIN RECOVERY SERVICE
# ==================================================

def recover_kannada_dimensions(raw_text):

    raw_text = raw_text or ""

    text = normalize_text(raw_text)

    existing = extract_directional_dimensions(
        raw_text
    )

    occupied = existing_area_spans(raw_text)

    agricultural = extract_agricultural_areas(
        raw_text
    )

    incomplete = detect_incomplete_measurements(
        raw_text
    )

    protected_candidates = (

        existing["dimension_candidates"]

        + existing["ambiguous_candidates"]

        + agricultural["measurement_candidates"]

        + agricultural["ambiguous_candidates"]

        + incomplete["incomplete_candidates"]

    )

    for item in protected_candidates:

        occupied.append((

            item["start_offset"],

            item["end_offset"],

        ))

    recovered = []

    excluded_overlaps = 0

    excluded_context = 0

    for match in RECOVERY_PATTERN.finditer(text):

        start = match.start()

        end = match.end()

        if overlaps(start, end, occupied):

            excluded_overlaps += 1

            continue

        following = text[end:end + 60]

        if (

            AREA_SUFFIX.match(following)

            or ROAD_SUFFIX.match(following)

        ):

            excluded_context += 1

            continue

        candidate = build_recovered_candidate(

            raw_text,

            match,

        )

        recovered.append(candidate)

        occupied.append((start, end))

    recovered.sort(

        key=lambda item: item["start_offset"]

    )

    return {

        "dimension_candidates": recovered,

        "candidate_count": len(recovered),

        "ambiguous_candidates": [],

        "ambiguous_count": 0,

        "existing_candidate_count":
            existing["candidate_count"],

        "existing_ambiguous_count":
            existing["ambiguous_count"],

        "excluded_overlaps": excluded_overlaps,

        "excluded_context": excluded_context,

        "selected_dimension": None,

        "property_association_pending": True,

        "dimension_consolidation_pending": True,

        "eligible_for_area_calculation": False,

        **dimension_flags(),

    }
