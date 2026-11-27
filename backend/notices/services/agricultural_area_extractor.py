"""
Extract agricultural area candidates from English
and Kannada property notice OCR text.

All measurements remain unverified and require review.
"""

import re
from decimal import Decimal


KANNADA_DIGITS = str.maketrans(
    "೦೧೨೩೪೫೬೭೮೯",
    "0123456789",
)

NUMBER = r"[0-9]+(?:\.[0-9]+)?"

ACRE = r"(?:acres?\b|ಎಕರೆ)"

GUNTA = r"(?:guntas?\b|ಗುಂಟೆ(?:ಗಳು)?)"

LEFT_BOUNDARY = r"(?<![\w./%+\-!,])"


COMPOUND_PATTERN = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<acres>{NUMBER})\s*{ACRE}"
    rf"\s*(?:and\s+|ಮತ್ತು\s+)?"
    rf"(?P<guntas>{NUMBER})\s*{GUNTA}",
    re.IGNORECASE,
)


HYPHENATED_PATTERN = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<acres>[0-9]+)"
    rf"\s*[-–]\s*"
    rf"(?P<guntas>{NUMBER})\s*{GUNTA}",
    re.IGNORECASE,
)


SINGLE_PATTERN = re.compile(
    rf"{LEFT_BOUNDARY}"
    rf"(?P<value>{NUMBER})\s*"
    rf"(?P<unit>{ACRE}|{GUNTA})",
    re.IGNORECASE,
)


AMBIGUOUS_PATTERN = re.compile(
    rf"(?<!\w)"
    rf"[0-9]+[!%?/]"
    rf"\s*{GUNTA}"
    rf"|[!]\s*{ACRE}\s*"
    rf"{NUMBER}\s*{GUNTA}",
    re.IGNORECASE,
)


def safety_flags():

    return {
        "requires_review": True,
        "verified": False,
        "ownership_verified": False,
        "approved_for_search": False,
        "eligible_for_alert": False,
    }


def decimal_string(value):

    value = Decimal(value)

    return format(value.normalize(), "f")


def normalize_text(raw_text):

    # Keep character positions unchanged so that
    # original evidence can be recovered exactly.

    return (
        raw_text.translate(KANNADA_DIGITS)
        .replace("\u200c", " ")
        .replace("\u200d", " ")
    )


def get_evidence(raw_text, start, end):

    line_start = raw_text.rfind(
        "\n", 0, start
    ) + 1

    line_end = raw_text.find("\n", end)

    if line_end == -1:
        line_end = len(raw_text)

    return {
        "raw_measurement": raw_text[start:end],
        "source_text": raw_text[line_start:line_end],
        "start_offset": start,
        "end_offset": end,
        "start_line": raw_text.count(
            "\n", 0, start
        ) + 1,
        "end_line": raw_text.count(
            "\n", 0, end
        ) + 1,
    }


def overlaps(start, end, occupied):

    return any(
        start < other_end
        and end > other_start
        for other_start, other_end in occupied
    )


def detect_language(text):

    has_kannada = bool(
        re.search(r"[\u0C80-\u0CFF]", text)
    )

    has_english = bool(
        re.search(r"[A-Za-z]", text)
    )

    if has_kannada and has_english:
        return "mixed"

    if has_kannada:
        return "kn"

    return "en"


def build_candidate(
    raw_text,
    match,
    acres,
    guntas,
    extraction_method,
    explicit_components,
):

    acres = Decimal(acres)
    guntas = Decimal(guntas)

    total_guntas = acres * 40 + guntas

    warnings = []

    if (
        extraction_method in {
            "COMPOUND_ACRE_GUNTA",
            "HYPHENATED_ACRE_GUNTA",
        }
        and guntas >= 40
    ):
        warnings.append(
            "GUNTA_COMPONENT_OUTSIDE_STANDARD_RANGE"
        )

    if total_guntas == 0:
        warnings.append("ZERO_AREA")

    evidence = get_evidence(
        raw_text,
        match.start(),
        match.end(),
    )

    if extraction_method == "HYPHENATED_ACRE_GUNTA":
        warnings.append(
            "HYPHENATED_NOTATION_REQUIRES_CONFIRMATION"
        )

    return {
        "measurement_type": "AGRICULTURAL_AREA",
        "extraction_method": extraction_method,
        "language": detect_language(
            evidence["raw_measurement"]
        ),
        "acres": decimal_string(acres),
        "guntas": decimal_string(guntas),
        "explicit_components": explicit_components,
        "normalized_total_guntas": decimal_string(
            total_guntas
        ),
        "normalized_total_acres": decimal_string(
            total_guntas / 40
        ),
        "normalized_total_square_feet": decimal_string(
            total_guntas * 1089
        ),
        "normalization_method": "ARITHMETIC_CONVERSION",
        "normalized_values_are_derived": True,
        "property_association_verified": False,
        "warnings": warnings,
        **evidence,
        **safety_flags(),
    }


def extract_agricultural_areas(raw_text):

    raw_text = raw_text or ""

    text = normalize_text(raw_text)

    candidates = []
    ambiguous_candidates = []
    occupied = []

    # Reserve ambiguous expressions before extracting
    # valid measurements. Never guess missing digits.

    for match in AMBIGUOUS_PATTERN.finditer(text):

        occupied.append(
            (match.start(), match.end())
        )

        ambiguous_candidates.append({
            "measurement_type": "AGRICULTURAL_AREA",
            "reason": "AMBIGUOUS_OCR_MEASUREMENT",
            "normalized_total_guntas": None,
            "normalized_total_acres": None,
            "normalized_total_square_feet": None,
            **get_evidence(
                raw_text,
                match.start(),
                match.end(),
            ),
            **safety_flags(),
        })

    # Extract complete compound measurements first.

    for pattern, method in (
        (
            COMPOUND_PATTERN,
            "COMPOUND_ACRE_GUNTA",
        ),
        (
            HYPHENATED_PATTERN,
            "HYPHENATED_ACRE_GUNTA",
        ),
    ):

        for match in pattern.finditer(text):

            if overlaps(
                match.start(),
                match.end(),
                occupied,
            ):
                continue

            candidates.append(
                build_candidate(
                    raw_text,
                    match,
                    match.group("acres"),
                    match.group("guntas"),
                    method,
                    ["acres", "guntas"],
                )
            )

            occupied.append(
                (match.start(), match.end())
            )

    # Extract remaining standalone acres or guntas.

    for match in SINGLE_PATTERN.finditer(text):

        if overlaps(
            match.start(),
            match.end(),
            occupied,
        ):
            continue

        value = match.group("value")

        unit = match.group("unit").casefold()

        is_acre = (
            unit.startswith("acre")
            or unit.startswith("ಎಕರೆ")
        )

        candidates.append(
            build_candidate(
                raw_text,
                match,
                value if is_acre else "0",
                "0" if is_acre else value,
                (
                    "STANDALONE_ACRE"
                    if is_acre
                    else "STANDALONE_GUNTA"
                ),
                ["acres"] if is_acre else ["guntas"],
            )
        )

    # Preserve repeated measurements independently.

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
        **safety_flags(),
    }
