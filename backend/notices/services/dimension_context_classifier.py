import re

from copy import deepcopy

from notices.services.agricultural_area_extractor import (
    normalize_text,
    safety_flags,
)


ROAD_PATTERN = re.compile(
    r"^[ \t]*"
    r"(?:wide[ \t]+)?"
    r"(?:(?:church|ಚರ್ಚ್)[ \t]+)?"
    r"(?:road\b|street\b|ರಸ್ತೆ|ರಸ್ತ|ರಸ್ಥೆ)",
    re.IGNORECASE,
)


PROPERTY_AXIS_PATTERN = re.compile(
    r"\b(?:east\s*(?:to|-)\s*west"
    r"|west\s*(?:to|-)\s*east"
    r"|north\s*(?:to|-)\s*south"
    r"|south\s*(?:to|-)\s*north)\b"
    r"|ಪೂರ್ವದಿಂದ\s*ಪಶ್ಚಿಮ(?:ಕ್ಕೆ)?"
    r"|ಉತ್ತರದಿಂದ\s*ದಕ್ಷಿಣ(?:ಕ್ಕೆ)?"
    r"|ಪೂರ್ವ\s*-\s*ಪಶ್ಚಿಮ"
    r"|ಉತ್ತರ\s*-\s*ದಕ್ಷಿಣ",
    re.IGNORECASE,
)


PROPERTY_SIDE_PATTERN = re.compile(
    r"\b(?:northern|southern|eastern|western)"
    r"\s+side\b"
    r"|(?:ಉತ್ತರ|ದಕ್ಷಿಣ|ಪೂರ್ವ|ಪಶ್ಚಿಮ)"
    r"\s*ಭಾಗದಲ್ಲಿ",
    re.IGNORECASE,
)


BOUNDARY_DIRECTION_PATTERN = re.compile(
    r"\b(?:north|south|east|west)\b"
    r"|ಉತ್ತರಕ್ಕೆ|ದಕ್ಷಿಣಕ್ಕೆ"
    r"|ಪೂರ್ವಕ್ಕೆ|ಪಶ್ಚಿಮಕ್ಕೆ",
    re.IGNORECASE,
)


def classify_dimension_context(
    raw_text,
    candidate,
):

    raw_text = raw_text or ""

    result = deepcopy(candidate)

    text = normalize_text(raw_text)

    start = candidate.get("start_offset")
    end = candidate.get("end_offset")

    role = "UNRESOLVED_DIMENSION"
    reason = "INSUFFICIENT_CONTEXT"

    context = ""
    following = ""
    road_evidence = None

    valid_offsets = (
        isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start < end <= len(raw_text)
    )

    if valid_offsets:

        context = text[start:end]

        following = text[end:end + 100]

        if (
            candidate.get("measurement_type")
            == "LINEAR_DIMENSION"
        ):

            road_match = ROAD_PATTERN.match(
                following
            )

            if (
                road_match
                and BOUNDARY_DIRECTION_PATTERN.search(
                    context
                )
                and not PROPERTY_AXIS_PATTERN.search(
                    context
                )
            ):

                role = "BOUNDARY_ROAD_WIDTH"

                reason = (
                    "EXPLICIT_ROAD_AFTER_"
                    "BOUNDARY_MEASUREMENT"
                )

                road_evidence = raw_text[
                    end:end + road_match.end()
                ]

            elif PROPERTY_AXIS_PATTERN.search(
                context
            ):

                role = "PROPERTY_DIMENSION"

                reason = "EXPLICIT_PROPERTY_AXIS"

            elif PROPERTY_SIDE_PATTERN.search(
                context
            ):

                role = "PROPERTY_DIMENSION"

                reason = "EXPLICIT_PROPERTY_SIDE"

        else:

            reason = (
                "NON_LINEAR_OR_IRREGULAR_"
                "MEASUREMENT"
            )

    else:

        reason = "INVALID_SOURCE_OFFSETS"

    result.update(safety_flags())

    result.update({
        "dimension_context_role": role,
        "dimension_context_reason": reason,
        "dimension_context_evidence": {
            "measurement_context": (
                raw_text[start:end]
                if valid_offsets else None
            ),
            "following_context": (
                raw_text[end:end + 100]
                if valid_offsets else None
            ),
            "road_evidence": road_evidence,
        },
        "context_classification_verified": False,
        "property_association_verified": False,
        "eligible_for_area_calculation": False,
        "requires_review": True,
        "verified": False,
        "eligible_for_alert": False,
    })

    return result


def classify_dimension_candidates(
    raw_text,
    candidates,
):

    classified = []

    property_dimensions = []
    boundary_road_widths = []
    unresolved_dimensions = []

    for candidate in candidates or []:

        item = classify_dimension_context(
            raw_text,
            candidate,
        )

        classified.append(item)

        role = item["dimension_context_role"]

        if role == "PROPERTY_DIMENSION":

            property_dimensions.append(item)

        elif role == "BOUNDARY_ROAD_WIDTH":

            boundary_road_widths.append(item)

        else:

            unresolved_dimensions.append(item)

    return {
        "classified_candidates": classified,
        "property_dimensions": property_dimensions,
        "boundary_road_widths": boundary_road_widths,
        "unresolved_dimensions": unresolved_dimensions,
        "candidate_count": len(classified),
        "property_dimension_count": len(
            property_dimensions
        ),
        "boundary_road_width_count": len(
            boundary_road_widths
        ),
        "unresolved_dimension_count": len(
            unresolved_dimensions
        ),
        "selected_dimension": None,
        "context_classification_verified": False,
        "property_association_verified": False,
        "eligible_for_area_calculation": False,
        **safety_flags(),
    }
