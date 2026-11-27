"""
English and Kannada property dimension extraction.

Extract linear dimensions and dimension pairs.
Preserve irregular expressions for manual review.

Never automatically calculate property area or
verify property boundaries.
"""

import re

from decimal import Decimal, localcontext

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
    extract_standard_areas,
)

from notices.services.standard_area_recovery import (
    recover_standard_areas,
)

from notices.services.kannada_area_refinement import (
    refine_kannada_areas,
)


# ==================================================
# LINEAR UNITS
# ==================================================

FEET = (
    r"(?:feet\b|foot\b|ft\b\.?|ಅಡಿ)"
)

METRES = (
    r"(?:metres?\b|meters?\b|"
    r"mtrs?\b\.?|m\b\.?|ಮೀಟರ್|ಮೀ\.?)"
)

LINEAR_UNIT = rf"(?:{FEET}|{METRES})"

FEET_PATTERN = re.compile(
    rf"^{FEET}$",
    re.IGNORECASE,
)


# ==================================================
# DIRECTIONAL PATTERNS
# ==================================================

DIRECTION_PATTERNS = {

    "EAST_WEST": (

        r"\b(?:east\s*(?:to|[-–])\s*west"
        r"|west\s*(?:to|[-–])\s*east"
        r"|E\s*[-–]\s*W)\b"

        r"|ಪೂರ್ವದಿಂದ\s*ಪಶ್ಚಿಮಕ್ಕೆ"

        r"|ಪಶ್ಚಿಮದಿಂದ\s*ಪೂರ್ವಕ್ಕೆ"

    ),

    "NORTH_SOUTH": (

        r"\b(?:north\s*(?:to|[-–])\s*south"
        r"|south\s*(?:to|[-–])\s*north"
        r"|N\s*[-–]\s*S)\b"

        r"|ಉತ್ತರದಿಂದ\s*ದಕ್ಷಿಣಕ್ಕೆ"

        r"|ಉತ್ತರದಿಂದ\s*ದಕಿಣಕ್ಕೆ"

        r"|ದಕ್ಷಿಣದಿಂದ\s*ಉತ್ತರಕ್ಕೆ"

    ),

    "EAST_SIDE": (

        r"\b(?:eastern\s+side"
        r"|east\s+side|towards\s+east"
        r"|east\s*:)\b?"

        r"|ಪೂರ್ವದ\s*ಕಡೆಗೆ"

        r"|ಪೂರ್ವಕ್ಕೆ"

    ),

    "WEST_SIDE": (

        r"\b(?:western\s+side"
        r"|west\s+side|towards\s+west"
        r"|west\s*:)"

        r"|ಪಶ್ಚಿಮದ\s*ಕಡೆಗೆ"

        r"|ಪಶ್ಚಿಮಕ್ಕೆ"

    ),

    "NORTH_SIDE": (

        r"\b(?:northern\s+side"
        r"|north\s+side|towards\s+north"
        r"|north\s*:)"

        r"|ಉತ್ತರದ\s*ಕಡೆಗೆ"

        r"|ಉತ್ತರಕ್ಕೆ"

    ),

    "SOUTH_SIDE": (

        r"\b(?:southern\s+side"
        r"|south\s+side|towards\s+south"
        r"|south\s*:)"

        r"|ದಕ್ಷಿಣದ\s*ಕಡೆಗೆ"

        r"|ದಕ್ಷಿಣಕ್ಕೆ"

    ),

}

# Remove the optional zero-width boundary assertion
# from the East-side expression.

DIRECTION_PATTERNS["EAST_SIDE"] = (
    DIRECTION_PATTERNS["EAST_SIDE"]
    .replace(r"\b?", "")
)


DIRECTION_GROUP = "|".join(

    rf"(?P<{name}>{pattern})"

    for name, pattern in DIRECTION_PATTERNS.items()

)


DIRECTION_PATTERN = re.compile(
    DIRECTION_GROUP,
    re.IGNORECASE,
)


# ==================================================
# MEASUREMENT PATTERNS
# ==================================================

DIRECTIONAL_DIMENSION = re.compile(

    rf"(?P<direction>{DIRECTION_GROUP})"

    r"\s*[:=\-]?\s*"

    r"(?:(?:measuring|measures|"

    r"measurement|length|ಅಳತೆ)\s*[:=\-]?\s*)?"

    rf"(?P<value>{NUMBER})"

    rf"\s*(?P<unit>{LINEAR_UNIT})",

    re.IGNORECASE,

)


DIMENSION_PAIR = re.compile(

    rf"{LEFT_BOUNDARY}"

    rf"(?P<first>{NUMBER})"

    rf"(?:[ \t]*(?P<first_unit>{LINEAR_UNIT}))?"

    r"[ \t]*[xX×][ \t]*"

    rf"(?P<second>{NUMBER})"

    rf"[ \t]*(?P<second_unit>{LINEAR_UNIT})"

    r"(?![\w])",

    re.IGNORECASE,

)


IRREGULAR_DIMENSION = re.compile(

    rf"(?P<direction>{DIRECTION_GROUP})"

    r"\s*[:=\-]?\s*"

    r"(?P<expression>\([^()\n]{2,60}\)"

    r"\s*/\s*2\b)"

    rf"(?:\s*(?P<unit>{LINEAR_UNIT}))?",

    re.IGNORECASE,

)


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def unit_name(raw_unit):

    if FEET_PATTERN.fullmatch(raw_unit):

        return "FT"

    return "M"


def normalize_length(value, unit):

    value = Decimal(str(value))

    with localcontext() as context:

        context.prec = 40

        if unit == "FT":

            feet = value

            metres = value * Decimal("0.3048")

        elif unit == "M":

            metres = value

            feet = value / Decimal("0.3048")

        else:

            raise ValueError(
                f"Unsupported linear unit: {unit}"
            )

        precision = Decimal("0.000001")

        return {

            "normalized_feet": decimal_string(
                feet.quantize(precision)
            ),

            "normalized_metres": decimal_string(
                metres.quantize(precision)
            ),

        }


def raw_group(raw_text, match, name):

    if match.start(name) == -1:

        return None

    return raw_text[
        match.start(name):match.end(name)
    ]


def get_direction(match):

    for name in DIRECTION_PATTERNS:

        if match.group(name) is not None:

            return name

    return None


def overlaps(start, end, occupied):

    return any(

        start < old_end and end > old_start

        for old_start, old_end in occupied

    )


def existing_area_spans(raw_text):

    occupied = []

    for extractor in (

        extract_standard_areas,

        recover_standard_areas,

        refine_kannada_areas,

    ):

        result = extractor(raw_text)

        for item in (

            result["measurement_candidates"]

            + result["ambiguous_candidates"]

        ):

            occupied.append((

                item["start_offset"],

                item["end_offset"],

            ))

    return occupied


def dimension_flags():

    return {

        "property_association_verified": False,

        "geometry_verified": False,

        "boundary_verified": False,

        "calculated_area": None,

        **safety_flags(),

    }


def build_length(value, raw_unit):

    value = Decimal(
        str(value).replace(",", "")
    )

    unit = unit_name(raw_unit)

    return {

        "dimension_value": decimal_string(value),

        "dimension_unit": unit,

        **normalize_length(value, unit),

    }


def build_linear_candidate(raw_text, match):

    evidence = get_evidence(

        raw_text,

        match.start(),

        match.end(),

    )

    measurement = build_length(

        match.group("value"),

        match.group("unit"),

    )

    warnings = []

    if Decimal(
        measurement["dimension_value"]
    ) == 0:

        warnings.append("ZERO_DIMENSION")

    return {

        "measurement_type": "LINEAR_DIMENSION",

        "extraction_method":
            "EXPLICIT_DIRECTIONAL_DIMENSION",

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

        "warnings": warnings,

        **evidence,

        **dimension_flags(),

    }


def build_pair_candidate(raw_text, match):

    evidence = get_evidence(

        raw_text,

        match.start(),

        match.end(),

    )

    first_unit = match.group("first_unit")

    second_unit = match.group("second_unit")

    warnings = [

        "DIMENSION_ORIENTATION_UNVERIFIED",

    ]

    if first_unit is None:

        first_unit = second_unit

        warnings.append(
            "SHARED_UNIT_ASSUMPTION"
        )

    first = build_length(

        match.group("first"),

        first_unit,

    )

    second = build_length(

        match.group("second"),

        second_unit,

    )

    if (

        Decimal(first["dimension_value"]) == 0

        or Decimal(second["dimension_value"]) == 0

    ):

        warnings.append("ZERO_DIMENSION")

    return {

        "measurement_type": "DIMENSION_PAIR",

        "extraction_method":
            "EXPLICIT_MULTIPLICATION_PAIR",

        "direction": None,

        "language": detect_language(
            evidence["raw_measurement"]
        ),

        "first_dimension": first,

        "second_dimension": second,

        "raw_first_value": raw_group(
            raw_text, match, "first"
        ),

        "raw_second_value": raw_group(
            raw_text, match, "second"
        ),

        "raw_first_unit": raw_group(
            raw_text, match, "first_unit"
        ),

        "raw_second_unit": raw_group(
            raw_text, match, "second_unit"
        ),

        "warnings": warnings,

        **evidence,

        **dimension_flags(),

    }


def build_irregular_candidate(raw_text, match):

    evidence = get_evidence(

        raw_text,

        match.start(),

        match.end(),

    )

    return {

        "measurement_type": "IRREGULAR_DIMENSION",

        "extraction_method":
            "UNEVALUATED_DIMENSION_EXPRESSION",

        "direction": get_direction(match),

        "language": detect_language(
            evidence["raw_measurement"]
        ),

        "raw_expression": raw_group(
            raw_text, match, "expression"
        ),

        "raw_unit": raw_group(
            raw_text, match, "unit"
        ),

        "reason":
            "IRREGULAR_OR_CORRUPTED_EXPRESSION",

        "dimension_value": None,

        "dimension_unit": None,

        "normalized_feet": None,

        "normalized_metres": None,

        "warnings": [

            "EXPRESSION_REQUIRES_MANUAL_REVIEW",

            "NO_AUTOMATIC_EVALUATION",

        ],

        **evidence,

        **dimension_flags(),

    }


# ==================================================
# MAIN EXTRACTION SERVICE
# ==================================================

def extract_directional_dimensions(raw_text):

    raw_text = raw_text or ""

    text = normalize_text(raw_text)

    occupied = existing_area_spans(raw_text)

    candidates = []

    ambiguous = []

    excluded_area_overlaps = 0

    # Reserve irregular expressions first.

    for match in IRREGULAR_DIMENSION.finditer(text):

        if overlaps(
            match.start(),
            match.end(),
            occupied,
        ):

            excluded_area_overlaps += 1

            continue

        ambiguous.append(
            build_irregular_candidate(
                raw_text, match
            )
        )

        occupied.append((

            match.start(),

            match.end(),

        ))

    # Dimension pairs are extracted before
    # individual directional dimensions.

    for match in DIMENSION_PAIR.finditer(text):

        if overlaps(
            match.start(),
            match.end(),
            occupied,
        ):

            excluded_area_overlaps += 1

            continue

        candidates.append(
            build_pair_candidate(
                raw_text, match
            )
        )

        occupied.append((

            match.start(),

            match.end(),

        ))

    # Extract explicit direction + value + unit.

    for match in DIRECTIONAL_DIMENSION.finditer(text):

        if overlaps(
            match.start(),
            match.end(),
            occupied,
        ):

            excluded_area_overlaps += 1

            continue

        candidates.append(
            build_linear_candidate(
                raw_text, match
            )
        )

        occupied.append((

            match.start(),

            match.end(),

        ))

    candidates.sort(
        key=lambda item: item["start_offset"]
    )

    ambiguous.sort(
        key=lambda item: item["start_offset"]
    )

    return {

        "dimension_candidates": candidates,

        "candidate_count": len(candidates),

        "ambiguous_candidates": ambiguous,

        "ambiguous_count": len(ambiguous),

        "excluded_area_overlaps":
            excluded_area_overlaps,

        "selected_dimension": None,

        "property_association_pending": True,

        "dimension_consolidation_pending": True,

        **dimension_flags(),

    }
