"""
Extract standard property area candidates from
English and Kannada newspaper OCR text.

Original evidence is preserved. All extracted
measurements require human review.
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


NUMBER = (
    r"(?:"
    r"[0-9]{1,3}(?:,[0-9]{3})+"
    r"|[0-9]+"
    r")"
    r"(?:\.[0-9]+)?"
)


LEFT_BOUNDARY = r"(?<![\w.,/%+\-!₹])"


UNIT_PATTERNS = {

    "SQ_FT": (
        r"(?:"
        r"sq\.?\s*(?:ft|feet|foot)\b\.?"
        r"|square\s+(?:feet|foot)\b"
        r"|sqft\b"
        r"|ft²"
        r"|ಚದರ\s*ಅಡಿ"
        r")"
    ),

    "SQ_YD": (
        r"(?:"
        r"sq\.?\s*(?:yards?|yds?)\b\.?"
        r"|square\s+yards?\b"
        r"|sqyds?\b"
        r"|yd²"
        r"|ಚದರ\s*ಗಜ(?:ಗಳು)?"
        r")"
    ),

    "SQ_M": (
        r"(?:"
        r"sq\.?\s*(?:mtrs?|metres?|meters?|m)\b\.?"
        r"|square\s+(?:metres?|meters?)\b"
        r"|sqm\b"
        r"|m²"
        r"|ಚದರ\s*ಮೀಟರ್(?:ಗಳು)?"
        r")"
    ),

}


UNIT_EXPRESSION = "|".join(
    f"(?P<{unit}>{pattern})"
    for unit, pattern in UNIT_PATTERNS.items()
)


AREA_PATTERN = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<value>{NUMBER})"
    rf"\s*(?:{UNIT_EXPRESSION})",
    re.IGNORECASE,
)


AMBIGUOUS_AREA_PATTERN = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<value>{NUMBER})"
    rf"\s*sq\.?\s*"
    rf"(?:11|f1|fl|1t)\b\.?",
    re.IGNORECASE,
)


SQUARE_METRES_PER_UNIT = {

    "SQ_FT": Decimal("0.09290304"),

    "SQ_YD": Decimal("0.83612736"),

    "SQ_M": Decimal("1"),

}


def overlaps(start, end, occupied):

    return any(
        start < other_end
        and end > other_start
        for other_start, other_end in occupied
    )


def normalize_area(value, unit):

    value = Decimal(value)

    with localcontext() as context:

        context.prec = 40

        square_metres = (
            value * SQUARE_METRES_PER_UNIT[unit]
        )

        if unit == "SQ_FT":

            square_feet = value

        elif unit == "SQ_YD":

            square_feet = value * 9

        else:

            square_feet = (
                square_metres
                / SQUARE_METRES_PER_UNIT["SQ_FT"]
            )

        if unit == "SQ_YD":

            square_yards = value

        else:

            square_yards = square_feet / 9

        return {

            "normalized_square_feet":
                decimal_string(
                    square_feet.quantize(
                        Decimal("0.000001")
                    )
                ),

            "normalized_square_yards":
                decimal_string(
                    square_yards.quantize(
                        Decimal("0.000001")
                    )
                ),

            "normalized_square_metres":
                decimal_string(
                    square_metres.quantize(
                        Decimal("0.000001")
                    )
                ),

        }


def build_area_candidate(raw_text, match):

    unit = next(
        unit
        for unit in UNIT_PATTERNS
        if match.group(unit) is not None
    )

    value = Decimal(
        match.group("value").replace(",", "")
    )

    evidence = get_evidence(
        raw_text,
        match.start(),
        match.end(),
    )

    warnings = []

    if value == 0:

        warnings.append("ZERO_AREA")

    return {

        "measurement_type": "STANDARD_AREA",

        "extraction_method":
            "EXPLICIT_STANDARD_AREA",

        "language": detect_language(
            evidence["raw_measurement"]
        ),

        "raw_numeric_value":
            raw_text[
                match.start("value"):
                match.end("value")
            ],

        "raw_unit":
            raw_text[
                match.start(unit):
                match.end(unit)
            ],

        "area_value": decimal_string(value),

        "area_unit": unit,

        "normalization_method":
            "ARITHMETIC_CONVERSION",

        "normalization_decimal_places": 6,

        "normalized_values_are_derived": True,

        "property_association_verified": False,

        "area_role": None,

        "warnings": warnings,

        **normalize_area(value, unit),

        **evidence,

        **safety_flags(),

    }


def extract_standard_areas(raw_text):

    raw_text = raw_text or ""

    text = normalize_text(raw_text)

    candidates = []

    ambiguous_candidates = []

    occupied = []

    # Preserve recognizable corrupted area units
    # without assuming what the unit should be.

    for match in AMBIGUOUS_AREA_PATTERN.finditer(text):

        occupied.append(
            (match.start(), match.end())
        )

        ambiguous_candidates.append({

            "measurement_type": "STANDARD_AREA",

            "reason": "AMBIGUOUS_OCR_AREA_UNIT",

            "raw_numeric_value":
                raw_text[
                    match.start("value"):
                    match.end("value")
                ],

            "area_value": None,

            "area_unit": None,

            "normalized_square_feet": None,

            "normalized_square_yards": None,

            "normalized_square_metres": None,

            "property_association_verified": False,

            **get_evidence(
                raw_text,
                match.start(),
                match.end(),
            ),

            **safety_flags(),

        })

    # Extract explicitly stated standard areas.

    for match in AREA_PATTERN.finditer(text):

        if overlaps(
            match.start(),
            match.end(),
            occupied,
        ):

            continue

        # Avoid interpreting the second number
        # of a dimension expression as an area.

        preceding = text[
            max(0, match.start() - 60):
            match.start()
        ]

        if re.search(
            r"[0-9]\s*[xX×]\s*$",
            preceding,
        ):

            continue

        candidates.append(
            build_area_candidate(
                raw_text,
                match,
            )
        )

        occupied.append(
            (match.start(), match.end())
        )

    candidates.sort(
        key=lambda item: item["start_offset"]
    )

    ambiguous_candidates.sort(
        key=lambda item: item["start_offset"]
    )

    return {

        "measurement_candidates": candidates,

        "candidate_count": len(candidates),

        "ambiguous_candidates": ambiguous_candidates,

        "ambiguous_count": len(ambiguous_candidates),

        "selected_measurement": None,

        "property_association_pending": True,

        "area_role_classification_pending": True,

        **safety_flags(),

    }
