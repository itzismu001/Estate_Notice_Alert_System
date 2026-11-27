"""English and Kannada objection deadline extraction."""

import re

from datetime import date, timedelta

from notices.services.agricultural_area_extractor import (
    normalize_text,
    get_evidence,
    safety_flags,
)


DEADLINE_PATTERNS = [

    (
        "en",
        re.compile(
            r"\bwithin\s+(?:a\s+period\s+of\s+)?"
            r"(?P<value>[0-9]{1,3})\s*"
            r"(?P<unit>days?|weeks?|months?)\b",
            re.IGNORECASE,
        ),
    ),

    (
        "kn",
        re.compile(
            r"(?<![\w./])"
            r"(?P<value>[0-9]{1,3})\s*"
            r"(?P<unit>ದಿನ(?:ಗಳ)?|ವಾರ(?:ಗಳ)?"
            r"|ತಿಂಗಳ(?:ು)?)"
            r"\s*(?:ಒಳಗಾಗಿ|ಒಳಗೆ|ಒಳಗಡೆ|ಒಳಗೆಂದು)",
        ),
    ),

]


OBJECTION_CONTEXT = re.compile(
    r"objection|claims?\b|objections?"
    r"|ಆಕ್ಷೇಪಣೆ|ತಕರಾರು|ಹಕ್ಕು|ಆಕ್ಷೇಪ",
    re.IGNORECASE,
)


OTHER_DEADLINE_CONTEXT = re.compile(
    r"repay|repayment|loan amount|payment"
    r"|auction deposit|earnest money"
    r"|ಸಾಲ ಮರುಪಾವತಿ|ಪಾವತಿಸ",
    re.IGNORECASE,
)


UNIT_MAP = {
    "day": "DAYS",
    "days": "DAYS",
    "week": "WEEKS",
    "weeks": "WEEKS",
    "month": "MONTHS",
    "months": "MONTHS",
    "ದಿನ": "DAYS",
    "ದಿನಗಳ": "DAYS",
    "ವಾರ": "WEEKS",
    "ವಾರಗಳ": "WEEKS",
    "ತಿಂಗಳ": "MONTHS",
    "ತಿಂಗಳು": "MONTHS",
}


def extract_deadline_candidates(raw_text):

    raw_text = raw_text or ""
    text = normalize_text(raw_text)

    candidates = []

    for language, pattern in DEADLINE_PATTERNS:

        for match in pattern.finditer(text):

            value = int(match.group("value"))

            unit = UNIT_MAP.get(
                match.group("unit").casefold()
            )

            if value <= 0 or unit is None:
                continue

            context = text[
                max(0, match.start() - 160):
                match.end() + 160
            ]

            objection = bool(
                OBJECTION_CONTEXT.search(context)
            )

            other = bool(
                OTHER_DEADLINE_CONTEXT.search(context)
            )

            if objection and not other:

                role = "OBJECTION_DEADLINE"

            elif other and not objection:

                role = "OTHER_DEADLINE"

            else:

                role = "UNRESOLVED_DEADLINE"

            candidates.append({
                "deadline_value": value,
                "deadline_unit": unit,
                "deadline_role": role,
                "language": language,
                "normalized_days": (
                    value if unit == "DAYS"
                    else value * 7 if unit == "WEEKS"
                    else None
                ),
                "reference_date": None,
                "calculated_deadline": None,
                "deadline_verified": False,
                "reference_date_verified": False,
                "context_verified": False,
                **get_evidence(
                    raw_text,
                    match.start(),
                    match.end(),
                ),
                **safety_flags(),
            })

    candidates.sort(
        key=lambda item: item["start_offset"]
    )

    return {
        "deadline_candidates": candidates,
        "candidate_count": len(candidates),
        "selected_deadline": None,
        **safety_flags(),
    }


def validate_deadlines(
    primary_text,
    secondary_text=None,
):

    primary = extract_deadline_candidates(
        primary_text
    )

    secondary = (
        extract_deadline_candidates(secondary_text)
        if secondary_text and secondary_text.strip()
        else None
    )

    def keys(result):

        if result is None:
            return set()

        return {
            (
                item["deadline_value"],
                item["deadline_unit"],
            )
            for item in result["deadline_candidates"]
            if item["deadline_role"]
            == "OBJECTION_DEADLINE"
        }

    first = keys(primary)
    second = keys(secondary)

    if secondary is None:

        status = (
            "SECONDARY_NOT_AVAILABLE"
            if first else "NOT_FOUND"
        )

    elif not first and not second:

        status = "NOT_FOUND"

    elif first and second and first != second:

        status = "CONFLICT"

    elif first == second and len(first) == 1:

        status = "CONSISTENT_UNVERIFIED"

    elif first == second and len(first) > 1:

        status = "MULTIPLE_CANDIDATES"

    else:

        status = "SINGLE_SOURCE"

    return {
        "primary": primary,
        "secondary": secondary,
        "status": status,
        "primary_values": [
            list(item) for item in sorted(first)
        ],
        "secondary_values": [
            list(item) for item in sorted(second)
        ],
        "selected_deadline": None,
        "calculated_deadline": None,
        "deadline_verified": False,
        **safety_flags(),
    }
