
import re

from notices.services.location_extractor import (
    normalize_location_text
)

from notices.services.property_location_associator import (
    associate_property_locations
)


# ==================================================
# ADDRESS START MARKERS
# ==================================================

ADDRESS_START_PATTERN = (

    r"\b(?:"

    r"situated\s+at|"

    r"situated\s+in|"

    r"located\s+at|"

    r"located\s+in|"

    r"property\s+address\s*:"

    r")\s*"
)


# ==================================================
# ADDRESS END MARKERS
# ==================================================

ADDRESS_END_PATTERN = (

    r"\b(?:"

    r"measuring|"

    r"having\s+an\s+area|"

    r"admeasuring|"

    r"bounded|"

    r"boundaries|"

    r"together\s+with|"

    r"advocate|"

    r"residing\s+at|"

    r"office\s*:|"

    r"mobile\s*:|"

    r"e-mail|"

    r"i\s+have|"

    r"my\s+client"

    r")"
)


# ==================================================
# URBAN ADDRESS COMPONENTS
# ==================================================

COMPONENT_PATTERNS = {

    "stage": (

        r"\b(\d{1,2})"

        r"(?:st|nd|rd|th)?\s+stage\b"
    ),

    "block": (

        r"\b(\d{1,3}|[A-Za-z])"

        r"(?:st|nd|rd|th)?\s+block\b"
    ),

    "cross": (

        r"\b(\d{1,3})"

        r"(?:st|nd|rd|th)?"

        r"\s*(?:([A-Za-z])\s+)?cross\b"
    ),

    "kannada_stage": (

        r"(\d{1,2})\s*ನೇ\s*ಹಂತ"
    ),

    "kannada_block": (

        r"(\d{1,3})\s*ನೇ\s*ಬ್ಲಾಕ್"
    ),

    "kannada_cross": (

        r"(\d{1,3})\s*ನೇ\s*"

        r"(?:[A-Za-z\u0C80-\u0CFF]+\s+)?"

        r"(?:ಕ್ರಾಸ್|ಅಡ್ಡರಸ್ತೆ)"
    )
}


# ==================================================
# UNIQUE VALUES
# ==================================================

def unique_values(values):

    result = []
    seen = set()

    for value in values:

        value = value.strip(" ,.;:-")

        key = value.casefold()

        if value and key not in seen:

            result.append(value)

            seen.add(key)

    return result


# ==================================================
# CLEAN ADDRESS CANDIDATE
# ==================================================

def clean_address(value):

    value = value.strip(" ,.;:-")

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    # Reject very short or unusually long
    # address fragments.

    if len(value) < 5:

        return None

    if len(value) > 220:

        return None

    if not re.search(

        r"[A-Za-z\u0C85-\u0CB9]",

        value
    ):

        return None

    return value


# ==================================================
# EXPLICIT PROPERTY ADDRESSES
# ==================================================

def extract_explicit_addresses(section_text):

    text = normalize_location_text(
        section_text
    )

    evidence = []

    for match in re.finditer(

        ADDRESS_START_PATTERN,

        text,

        re.IGNORECASE
    ):

        remaining = text[match.end():]

        end = re.search(

            ADDRESS_END_PATTERN,

            remaining,

            re.IGNORECASE
        )

        candidate = (

            remaining[:end.start()]

            if end

            else remaining
        )

        # Stop at the first sentence boundary.

        sentence_end = re.search(

            r"\.\s+(?=[A-Z])",

            candidate
        )

        if sentence_end:

            candidate = candidate[
                :sentence_end.start()
            ]

        address = clean_address(
            candidate
        )

        if address:

            evidence.append({

                "address": address,

                "method": "EXPLICIT_ADDRESS",

                "source_text": text,

                "verified": False
            })

    return evidence


# ==================================================
# URBAN ADDRESS COMPONENT EXTRACTION
# ==================================================

def extract_address_components(text):

    components = {}

    for field, pattern in COMPONENT_PATTERNS.items():

        values = [

            match.group().strip()

            for match in re.finditer(

                pattern,

                text,

                re.IGNORECASE
            )
        ]

        components[field] = unique_values(
            values
        )

    return components


# ==================================================
# KANNADA PROPERTY ADDRESS CONTEXT
# ==================================================

def extract_kannada_address_context(section_text):

    text = normalize_location_text(
        section_text
    )

    evidence = []

    pattern = (

        r"(?:ಬೆಂಗಳೂರಿನ|"

        r"ಬೆಂಗಳೂರಿನಲ್ಲಿ)"

        r"\s+"

        r"(.{5,160}?)"

        r"(?="

        r"(?:ನಲ್ಲಿರುವ|ದಲ್ಲಿರುವ)"

        r"|(?:ನಿವೇಶನ|ಸೈಟ್)\s*"

        r"(?:ನಂ\.?|ಸಂ\.?|ಸಂಖ್ಯೆ)"

        r")"
    )

    for match in re.finditer(

        pattern,

        text,

        re.IGNORECASE
    ):

        candidate = clean_address(
            match.group(1)
        )

        if candidate:

            evidence.append({

                "address": candidate,

                "method": "KANNADA_PROPERTY_CONTEXT",

                "source_text": text,

                "verified": False
            })

    return evidence


# ==================================================
# MAIN PROPERTY ADDRESS EXTRACTOR
# ==================================================

def extract_property_address_candidates(raw_text):

    association = associate_property_locations(
        raw_text
    )

    evidence = []

    components = {

        field: []

        for field in COMPONENT_PATTERNS
    }

    for section in association["property_sections"]:

        text = section["text"]

        evidence.extend(

            extract_explicit_addresses(text)
        )

        evidence.extend(

            extract_kannada_address_context(text)
        )

        extracted_components = (

            extract_address_components(text)
        )

        for field, values in extracted_components.items():

            components[field].extend(values)

    candidates = unique_values([

        item["address"]

        for item in evidence
    ])

    components = {

        field: unique_values(values)

        for field, values in components.items()
    }

    return {

        "property_address_candidates": candidates,

        "address_components": components,

        "address_evidence": evidence,

        "association_method": (
            association["association_method"]
        ),

        "property_location_candidates": (

            association[
                "property_location_candidates"
            ]
        ),

        "property_address": None,

        "requires_review": True,

        "verified": False,

        "eligible_for_alert": False,

        "review_reasons": [

            "Free-text addresses require human verification",

            "Address components may belong to "
            "different property schedules"
        ]
    }
