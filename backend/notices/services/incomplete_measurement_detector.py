"""
Conservative detection of incomplete agricultural
measurement expressions.

Never infer missing measurement units.
"""

import re

from notices.services.agricultural_area_extractor import (
    extract_agricultural_areas,
    normalize_text,
    get_evidence,
    safety_flags,
)


AGRICULTURAL_CONTEXT = re.compile(
    r"\bacres?\b|\bguntas?\b|"
    r"\bagricultural\s+land\b|"
    r"ಎಕರೆ|ಗುಂಟೆ|ಕೃಷಿ\s*ಜಮೀನು",
    re.IGNORECASE,
)


SURVEY_MEASUREMENT = re.compile(
    r"\b(?:Sy\.?\s*No\.?|Survey\s+No\.?)"
    r"\s*(?P<survey>[0-9]+"
    r"(?:/[0-9]+)*[A-Za-z]?)"
    r"\s*,?\s*"
    r"measuring\s*"
    r"(?:(?:to\s+)?(?:an\s+)?"
    r"extent\s+of\s+|of\s+)?"
    r"(?P<value>[0-9]+(?:\.[0-9]+)?)"
    r"(?![\w.,/%+\-])",
    re.IGNORECASE,
)


KNOWN_UNIT = re.compile(
    r"^\s*(?:"
    r"acres?\b|guntas?\b|"
    r"ghuntas?\b|gunthas?\b|"
    r"sq\.?\s*(?:ft|feet|foot|yards?|"
    r"yds?|mtrs?|metres?|meters?|m)\b|"
    r"square\s*(?:feet|foot|yards?|"
    r"metres?|meters?)\b|"
    r"feet\b|foot\b|yards?\b|"
    r"metres?\b|meters?\b|"
    r"hectares?\b|cents?\b|"
    r"ಎಕರೆ|ಗುಂಟೆ|ಗುಂಟಾ|ಚದರ|ಅಡಿ|ಮೀಟರ್"
    r")",
    re.IGNORECASE,
)


def detect_incomplete_measurements(raw_text):

    raw_text = raw_text or ""

    text = normalize_text(raw_text)

    existing = extract_agricultural_areas(
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

    for match in SURVEY_MEASUREMENT.finditer(text):

        value_start = match.start("value")
        value_end = match.end("value")

        context_start = max(
            0, match.start() - 250
        )

        context_end = min(
            len(text), match.end() + 250
        )

        context = text[
            context_start:context_end
        ]

        if not AGRICULTURAL_CONTEXT.search(
            context
        ):
            continue

        # Do not duplicate complete or already
        # ambiguous agricultural measurements.

        if any(
            value_start < end
            and value_end > start
            for start, end in occupied
        ):
            continue

        following_text = text[
            value_end:value_end + 80
        ]

        # Skip measurements with recognized units.

        if KNOWN_UNIT.match(following_text):
            continue

        # Exclude dimension expressions.

        if re.match(
            r"\s*[xX×]\s*[0-9]",
            following_text,
        ):
            continue

        evidence = get_evidence(
            raw_text,
            match.start(),
            match.end(),
        )

        candidates.append({

            "measurement_type":
                "INCOMPLETE_MEASUREMENT",

            "reason":
                "MISSING_OR_CORRUPTED_UNIT",

            "survey_number_context":
                match.group("survey"),

            "raw_numeric_value":
                raw_text[value_start:value_end],

            "normalized_numeric_value":
                match.group("value"),

            "measurement_unit": None,

            "normalized_total_guntas": None,

            "normalized_total_acres": None,

            "normalized_total_square_feet": None,

            "property_association_verified": False,

            "context_evidence":
                raw_text[context_start:context_end],

            "following_source_text":
                raw_text[value_end:value_end + 80],

            **evidence,

            **safety_flags(),

        })

    return {

        "incomplete_candidates": candidates,

        "candidate_count": len(candidates),

        "selected_measurement": None,

        **safety_flags(),

    }
