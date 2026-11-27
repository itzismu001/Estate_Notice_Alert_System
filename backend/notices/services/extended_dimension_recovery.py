"""Additional dimension recovery with conservative OCR handling."""

import re

from notices.services.agricultural_area_extractor import (
    normalize_text,
    get_evidence,
    detect_language,
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

from notices.services.kannada_dimension_recovery import (
    recover_kannada_dimensions,
)


ALTERNATIVE_PATTERN = re.compile(
    r"[ \t\n]*(?:or\b|ಅಥವಾ|=)[ \t\n]*"
    rf"(?P<value>{NUMBER})\s*"
    rf"(?P<unit>{LINEAR_UNIT})(?![\w²])",
    re.IGNORECASE,
)

SIDE_PATTERN = re.compile(
    r"(?P<side>"
    r"northern|southern|eastern|western"
    r"|north|south|east|west"
    r"|ಉತ್ತರ|ದಕ್ಷಿಣ|ಪೂರ್ವ|ಪಶ್ಚಿಮ"
    r")"
    r"\s*(?:side\b|ಭಾಗದಲ್ಲಿ)"
    r"\s*[:=\-]?\s*"
    rf"(?P<value>{NUMBER})\s*"
    rf"(?P<unit>{LINEAR_UNIT})(?![\w²])",
    re.IGNORECASE,
)

IRREGULAR_PATTERN = re.compile(
    r"(?<![\w./])"
    r"(?P<expression>"
    r"[0-9]+(?:\.[0-9]+)?"
    r"\s*\+\s*"
    r"[0-9]+(?:\.[0-9]+)?"
    r"\s*/\s*2"
    r")"
    rf"\s*(?P<unit>{LINEAR_UNIT})",
    re.IGNORECASE,
)

SIDE_MAP = {
    "north": "NORTH_SIDE",
    "northern": "NORTH_SIDE",
    "south": "SOUTH_SIDE",
    "southern": "SOUTH_SIDE",
    "east": "EAST_SIDE",
    "eastern": "EAST_SIDE",
    "west": "WEST_SIDE",
    "western": "WEST_SIDE",
    "ಉತ್ತರ": "NORTH_SIDE",
    "ದಕ್ಷಿಣ": "SOUTH_SIDE",
    "ಪೂರ್ವ": "EAST_SIDE",
    "ಪಶ್ಚಿಮ": "WEST_SIDE",
}


def recover_extended_dimensions(raw_text):

    raw_text = raw_text or ""
    text = normalize_text(raw_text)

    base = extract_directional_dimensions(raw_text)
    kannada = recover_kannada_dimensions(raw_text)

    previous = (
        base["dimension_candidates"]
        + base["ambiguous_candidates"]
        + kannada["dimension_candidates"]
    )

    occupied = existing_area_spans(raw_text)

    occupied.extend(
        (item["start_offset"], item["end_offset"])
        for item in previous
    )

    numeric = []
    ambiguous = []

    def add_numeric(match, direction, method, parent=None):

        start, end = match.span()

        if overlaps(start, end, occupied):
            return

        following = text[end:end + 40]

        if re.match(
            r"\s*(?:road\b|street\b|ರಸ್ತೆ|ಚದರ|square\b)",
            following,
            re.IGNORECASE,
        ):
            return

        evidence = get_evidence(raw_text, start, end)

        item = {
            "measurement_type": "LINEAR_DIMENSION",
            "extraction_method": method,
            "direction": direction,
            "language": detect_language(
                evidence["raw_measurement"]
            ),
            "raw_numeric_value": raw_text[
                match.start("value"):match.end("value")
            ],
            "raw_unit": raw_text[
                match.start("unit"):match.end("unit")
            ],
            **build_length(
                match.group("value"),
                match.group("unit"),
            ),
            "parent_measurement_offset": (
                parent["start_offset"] if parent else None
            ),
            "recovered_candidate": True,
            "confidence": "LOW",
            "eligible_for_area_calculation": False,
            "warnings": [
                "RECOVERED_MEASUREMENT_REQUIRES_REVIEW"
            ],
            **evidence,
            **dimension_flags(),
        }

        numeric.append(item)
        occupied.append((start, end))

    # Preserve explicitly printed alternative units.

    for parent in previous:

        if parent["measurement_type"] != "LINEAR_DIMENSION":
            continue

        match = ALTERNATIVE_PATTERN.match(
            text,
            parent["end_offset"],
        )

        if match:
            add_numeric(
                match,
                parent.get("direction"),
                "EXPLICIT_ALTERNATIVE_UNIT",
                parent,
            )

    # Recover additional side-specific dimensions.

    for match in SIDE_PATTERN.finditer(text):

        add_numeric(
            match,
            SIDE_MAP.get(match.group("side").casefold()),
            "EXPLICIT_SIDE_RECOVERY",
        )

    # Retain irregular expressions without evaluating them.

    for match in IRREGULAR_PATTERN.finditer(text):

        start, end = match.span()

        if overlaps(start, end, occupied):
            continue

        context = text[max(0, start - 100):start]

        if not re.search(
            r"east|west|north|south|measur"
            r"|ಪೂರ್ವ|ಪಶ್ಚಿಮ|ಉತ್ತರ|ದಕ್ಷಿಣ|ಅಳತೆ",
            context,
            re.IGNORECASE,
        ):
            continue

        evidence = get_evidence(raw_text, start, end)

        ambiguous.append({
            "measurement_type": "IRREGULAR_DIMENSION",
            "extraction_method": "IRREGULAR_EXPRESSION_RECOVERY",
            "direction": None,
            "language": detect_language(
                evidence["raw_measurement"]
            ),
            "raw_expression": raw_text[
                match.start("expression"):
                match.end("expression")
            ],
            "reason": "AMBIGUOUS_ARITHMETIC_EXPRESSION",
            "dimension_value": None,
            "dimension_unit": None,
            "normalized_feet": None,
            "normalized_metres": None,
            "eligible_for_area_calculation": False,
            "warnings": ["NO_AUTOMATIC_EVALUATION"],
            **evidence,
            **dimension_flags(),
        })

        occupied.append((start, end))

    numeric.sort(key=lambda item: item["start_offset"])
    ambiguous.sort(key=lambda item: item["start_offset"])

    return {
        "dimension_candidates": numeric,
        "ambiguous_candidates": ambiguous,
        "candidate_count": len(numeric),
        "ambiguous_count": len(ambiguous),
        "selected_dimension": None,
        "eligible_for_area_calculation": False,
        **dimension_flags(),
    }
