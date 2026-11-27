
import re
from copy import deepcopy

from notices.services.location_extractor import (
    normalize_location_text
)


# ==================================================
# KNOWN LOCATION ALIASES
# ==================================================

LOCATION_ALIASES = {

    "bangalore": "Bengaluru",

    "bengaluru": "Bengaluru",

    "bangalore urban": "Bengaluru Urban",

    "bengaluru urban": "Bengaluru Urban",

    "bangalore rural": "Bengaluru Rural",

    "bengaluru rural": "Bengaluru Rural",

    "bangalore north": "Bengaluru North",

    "bengaluru north": "Bengaluru North",

    "bangalore south": "Bengaluru South",

    "bengaluru south": "Bengaluru South",

    "bangalore east": "Bengaluru East",

    "bengaluru east": "Bengaluru East",

    "bangalore west": "Bengaluru West",

    "bengaluru west": "Bengaluru West",

    "ಬೆಂಗಳೂರು": "Bengaluru",

    "ಬೆಂಗಳೂರು ಉತ್ತರ": "Bengaluru North",

    "ಬೆಂಗಳೂರು ದಕ್ಷಿಣ": "Bengaluru South",

    "ಬೆಂಗಳೂರು ಪೂರ್ವ": "Bengaluru East",

    "ಬೆಂಗಳೂರು ಪಶ್ಚಿಮ": "Bengaluru West",

    "ಬೆಂಗಳೂರು ನಗರ": "Bengaluru Urban",

    "ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ": "Bengaluru Rural",

    "ಕರ್ನಾಟಕ": "Karnataka",

    "karnataka": "Karnataka"
}


# ==================================================
# INVALID LOCATION WORDS
# ==================================================

INVALID_LOCATION_WORDS = {

    "additional",

    "principal",

    "senior",

    "junior",

    "civil",

    "court",

    "judge",

    "honourable",

    "honorable",

    "registered",

    "office",

    "said",

    "property",

    "the",

    "of",

    "in",

    "at"
}


# ==================================================
# ADDRESS CONTEXT FOR PIN CODES
# ==================================================

PIN_CONTEXT_TERMS = (

    "bengaluru",

    "bangalore",

    "karnataka",

    "mysuru",

    "mysore",

    "kolar",

    "tumakuru",

    "tumkur",

    "ramanagara",

    "mandya",

    "hassan",

    "chikkaballapura",

    "ಬೆಂಗಳೂರು",

    "ಕರ್ನಾಟಕ",

    "ಮೈಸೂರು",

    "ಕೋಲಾರ",

    "ತುಮಕೂರು",

    "ರಾಮನಗರ",

    "ಮಂಡ್ಯ",

    "ಹಾಸನ",

    "ಚಿಕ್ಕಬಳ್ಳಾಪುರ",

    "pin code",

    "pincode",

    "postal code",

    "ಪಿನ್ ಕೋಡ್"
)


# ==================================================
# NON-ADDRESS NUMBER CONTEXT
# ==================================================

NON_PIN_CONTEXT_PATTERN = (

    r"(?:"

    r"document|registration|account|loan|"

    r"survey|assessment|pid|"

    r"ದಾಖಲೆ|ದಸ್ತಾವೇಜು|ನೋಂದಣಿ|"

    r"ಸಾಲ|ಸರ್ವೆ|ಅಸೆಸ್ಮೆಂಟ್"

    r")"

    r"\s*"

    r"(?:no\.?|number|ನಂ\.?|ಸಂ\.?|ಸಂಖ್ಯೆ)?"

    r"\s*[:.]?\s*$"
)


# ==================================================
# NORMALIZE KNOWN LOCATION NAMES
# ==================================================

def canonicalize_location(value):

    value = normalize_location_text(
        value
    ).strip(" ,.;:")

    if not value:
        return None

    key = value.casefold()

    if key in INVALID_LOCATION_WORDS:
        return None

    return LOCATION_ALIASES.get(
        key,
        value
    )


# ==================================================
# CHECK PIN CODE CONTEXT
# ==================================================

def validate_pin_candidates(raw_text):

    text = normalize_location_text(
        raw_text
    )

    records = []

    for match in re.finditer(

        r"(?<!\d)[1-9]\d{5}(?!\d)",

        text
    ):

        value = match.group()

        before = text[
            max(0, match.start() - 70):
            match.start()
        ]

        after = text[
            match.end():
            min(len(text), match.end() + 20)
        ]

        context = before + value + after

        address_prefix = before[-40:].casefold()

        # Require a nearby location label.
        # This does not verify actual postal validity.

        has_address_context = any(

            re.search(

                re.escape(term.casefold())
                + r"\s*[,:\-–]?\s*$",

                address_prefix
            )

            for term in PIN_CONTEXT_TERMS
        )

        has_non_pin_context = bool(

            re.search(

                NON_PIN_CONTEXT_PATTERN,

                before,

                re.IGNORECASE
            )
        )

        # Avoid treating parts of decimals,
        # identifiers or formatted dates as PIN codes.

        previous_char = (

            text[match.start() - 1]

            if match.start() > 0

            else ""
        )

        next_char = (

            text[match.end()]

            if match.end() < len(text)

            else ""
        )

        decimal_fragment = (

            previous_char in (".", "/", ",")

            and match.start() >= 2

            and text[match.start() - 2].isdigit()
        ) or (

            next_char in (".", "/", ",")

            and match.end() + 1 < len(text)

            and text[match.end() + 1].isdigit()
        )

        if decimal_fragment:

            status = "NUMERIC_FRAGMENT"

        elif has_non_pin_context:

            status = "NON_ADDRESS_IDENTIFIER"

        elif has_address_context:

            status = "ADDRESS_CONTEXT"

        else:

            status = "INSUFFICIENT_CONTEXT"

        records.append({

            "value": value,

            "status": status,

            "source_text": context,

            "verified": False
        })

    return records


# ==================================================
# MAIN LOCATION VALIDATOR
# ==================================================

def validate_location_candidates(
    raw_text,
    location_result
):

    original = deepcopy(
        location_result or {}
    )

    candidates = original.get(
        "location_candidates"
    ) or {}

    normalized = {}

    rejected = []

    normalization_evidence = []

    for field, values in candidates.items():

        if field == "pin_code":
            continue

        normalized[field] = []

        seen = set()

        for value in values:

            canonical = canonicalize_location(
                value
            )

            if canonical is None:

                rejected.append({

                    "field": field,

                    "value": value,

                    "reason": "INVALID_LOCATION_WORD"
                })

                continue

            key = canonical.casefold()

            if key not in seen:

                normalized[field].append(
                    canonical
                )

                seen.add(key)

            normalization_evidence.append({

                "field": field,

                "original_value": value,

                "normalized_value": canonical,

                "verified": False
            })

    # ----------------------------------------------
    # PIN code context validation
    # ----------------------------------------------

    pin_records = validate_pin_candidates(
        raw_text
    )

    normalized["pin_code"] = list(

        dict.fromkeys(

            item["value"]

            for item in pin_records

            if item["status"] == "ADDRESS_CONTEXT"
        )
    )

    ambiguous = [

        field

        for field, values in normalized.items()

        if len(values) > 1
    ]

    return {

        "original_location_candidates": (
            candidates
        ),

        "normalized_location_candidates": (
            normalized
        ),

        "normalization_evidence": (
            normalization_evidence
        ),

        "rejected_location_candidates": (
            rejected
        ),

        "pin_code_evidence": pin_records,

        "ambiguous_location_fields": ambiguous,

        "property_address": None,

        "requires_review": True,

        "verified": False,

        "review_reasons": [

            "Normalized locations require "
            "property association verification",

            "PIN code context does not establish "
            "postal validity",

            "Unknown OCR spellings are preserved "
            "without automatic correction"
        ]
    }
