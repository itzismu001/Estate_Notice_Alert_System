
from notices.services.property_address_extractor import (
    extract_property_address_candidates
)

from notices.services.location_validator import (
    canonicalize_location
)

from notices.services.location_extractor import (
    normalize_location_text
)

from notices.services.ocr_validator import (
    compare_ocr_values
)


# ==================================================
# CONFIGURATION
# ==================================================

LOCATION_FIELDS = (

    "state",
    "district",
    "taluk",
    "hobli",
    "village",
    "layout",
    "gram_panchayat",
    "ward_number",
    "pin_code"
)

ADDRESS_COMPONENT_FIELDS = (

    "stage",
    "block",
    "cross",
    "kannada_stage",
    "kannada_block",
    "kannada_cross"
)


# ==================================================
# NORMALIZE LOCATION VALUES
# ==================================================

def normalize_candidates(values, use_aliases=False):

    result = []

    for value in values or []:

        if use_aliases:

            value = canonicalize_location(
                value
            )

        else:

            value = normalize_location_text(
                value
            ).strip(" ,.;:")

        if value:

            result.append(
                value.casefold()
            )

    return sorted(set(result))


# ==================================================
# COMPARE ONE LOCATION FIELD
# ==================================================

def compare_location_candidates(
    values_a,
    values_b,
    secondary_available=True,
    use_aliases=False
):

    values_a = list(values_a or [])
    values_b = list(values_b or [])

    normalized_a = normalize_candidates(
        values_a,
        use_aliases=use_aliases
    )

    normalized_b = normalize_candidates(
        values_b,
        use_aliases=use_aliases
    )

    result = compare_ocr_values(
        normalized_a,
        normalized_b
    )

    if not secondary_available and normalized_a:

        result["status"] = (
            "SECONDARY_NOT_AVAILABLE"
        )

        result["selected_value"] = None

    # Preserve original spelling and capitalization.

    result["original_source_a_candidates"] = (
        values_a
    )

    result["original_source_b_candidates"] = (
        values_b
    )

    result["verified"] = False

    result["approved_for_search"] = False

    return result


# ==================================================
# RESTORE ORIGINAL DISPLAY VALUE
# ==================================================

def get_display_value(
    comparison,
    use_aliases=False
):

    selected = comparison.get(
        "selected_value"
    )

    if not selected:

        return None

    originals = (

        comparison[
            "original_source_a_candidates"
        ]

        + comparison[
            "original_source_b_candidates"
        ]
    )

    for value in originals:

        normalized = normalize_candidates(

            [value],

            use_aliases=use_aliases
        )

        if selected in normalized:

            if use_aliases:

                return canonicalize_location(
                    value
                )

            return normalize_location_text(
                value
            ).strip(" ,.;:")

    return None


# ==================================================
# MAIN LOCATION OCR VALIDATOR
# ==================================================

def validate_property_locations(
    primary_text,
    secondary_text=None
):

    primary = extract_property_address_candidates(
        primary_text
    )

    secondary_available = bool(

        secondary_text

        and secondary_text.strip()
    )

    secondary = (

        extract_property_address_candidates(
            secondary_text
        )

        if secondary_available

        else None
    )

    primary_locations = primary.get(
        "property_location_candidates",
        {}
    )

    secondary_locations = (

        secondary.get(
            "property_location_candidates",
            {}
        )

        if secondary

        else {}
    )

    validations = {}

    # ----------------------------------------------
    # Administrative location comparison
    # ----------------------------------------------

    for field in LOCATION_FIELDS:

        validations[field] = (

            compare_location_candidates(

                primary_locations.get(
                    field,
                    []
                ),

                secondary_locations.get(
                    field,
                    []
                ),

                secondary_available=(
                    secondary_available
                ),

                use_aliases=True
            )
        )

    # ----------------------------------------------
    # Free-text property address comparison
    # ----------------------------------------------

    validations["property_address"] = (

        compare_location_candidates(

            primary.get(
                "property_address_candidates",
                []
            ),

            secondary.get(
                "property_address_candidates",
                []
            ) if secondary else [],

            secondary_available=(
                secondary_available
            )
        )
    )

    # ----------------------------------------------
    # Address component comparison
    # ----------------------------------------------

    components_a = primary.get(
        "address_components",
        {}
    )

    components_b = (

        secondary.get(
            "address_components",
            {}
        )

        if secondary

        else {}
    )

    for field in ADDRESS_COMPONENT_FIELDS:

        validations[field] = (

            compare_location_candidates(

                components_a.get(field, []),

                components_b.get(field, []),

                secondary_available=(
                    secondary_available
                )
            )
        )

    # ----------------------------------------------
    # Summarize validation outcomes
    # ----------------------------------------------

    conflicts = []

    single_source = []

    multiple_candidates = []

    unavailable_secondary = []

    consistent = []

    agreed_candidates = {}

    for field, result in validations.items():

        status = result["status"]

        if status == "CONFLICT":

            conflicts.append(field)

        elif status == "SINGLE_SOURCE":

            single_source.append(field)

        elif status == "MULTIPLE_CANDIDATES":

            multiple_candidates.append(field)

        elif status == "SECONDARY_NOT_AVAILABLE":

            unavailable_secondary.append(field)

        elif status == "CONSISTENT_UNVERIFIED":

            consistent.append(field)

            value = get_display_value(

                result,

                use_aliases=(
                    field in LOCATION_FIELDS
                )
            )

            if value:

                agreed_candidates[field] = value

    # ----------------------------------------------
    # Review information
    # ----------------------------------------------

    review_reasons = [

        "OCR agreement does not verify "
        "property location",

        "Property association remains heuristic"
    ]

    for field in conflicts:

        review_reasons.append(
            f"Location OCR conflict: {field}"
        )

    for field in single_source:

        review_reasons.append(
            f"Single-source location: {field}"
        )

    for field in multiple_candidates:

        review_reasons.append(
            f"Multiple location candidates: {field}"
        )

    if not secondary_available:

        review_reasons.append(
            "Secondary OCR unavailable"
        )

    return {

        "primary_result": primary,

        "secondary_result": secondary,

        "secondary_available": (
            secondary_available
        ),

        "validations": validations,

        "agreed_location_candidates": (
            agreed_candidates
        ),

        "conflicting_fields": conflicts,

        "single_source_fields": single_source,

        "multiple_candidate_fields": (
            multiple_candidates
        ),

        "secondary_unavailable_fields": (
            unavailable_secondary
        ),

        "consistent_fields": consistent,

        "has_conflicts": bool(conflicts),

        "property_address": None,

        "requires_review": True,

        "verified": False,

        "approved_for_search": False,

        "eligible_for_alert": False,

        "review_reasons": review_reasons
    }
