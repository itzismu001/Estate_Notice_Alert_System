
import re
import unicodedata


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize_text(text):

    text = unicodedata.normalize(
        "NFC",
        text or ""
    )

    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")

    text = text.translate(
        str.maketrans(
            "೦೧೨೩೪೫೬೭೮೯",
            "0123456789"
        )
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# ==================================================
# IDENTIFIER CONFIGURATION
# ==================================================

NUMBER_LABEL = (
    r"(?:ನಂ\.?|ಸಂ\.?|ಸಂಖ್ಯೆ|ನಂಬರ್|No\.?)"
)

IDENTIFIER = (
    r"[0-9]+"
    r"(?:[/\-][0-9A-Za-z]+)*"
    r"[/\-]?"
)

PATTERNS = {

    "survey_numbers": (
        r"ಸರ್ವ[ೆೇ]\s*"
        r"(?:ನಂ\.?|ಸಂ\.?|ಸಂಖ್ಯೆ|ನಂಬರ್|ಸ|oe|ಜ್)?"
    ),

    "site_numbers": (
        r"(?<![\w\u0C80-\u0CFF])(?:ನಿವೇಶನ|ಸೈಟ್)\s*"
        + NUMBER_LABEL
    ),

    "khata_numbers": (
        r"ಖಾತ[ೆಾ]\s*"
        + NUMBER_LABEL
    ),

    "pid_numbers": (
        r"(?:ಈ|ಇ|E)?[\s\-]*"
        r"(?:ಪಿ\.?\s*ಐ\.?\s*ಡಿ\.?|PID)"
        r"\s*(?:" + NUMBER_LABEL + r")?"
    ),

    "document_numbers": (
        r"(?:ದಸ್ತಾವೇಜು|ದಾಖಲೆ)\s*"
        + NUMBER_LABEL
    ),

    "assessment_numbers": (
        r"ಅಸೆಸ್ಮೆಂಟ್\s*"
        r"(?:" + NUMBER_LABEL + r")?"
    ),

    "property_numbers": (
        r"(?:ಆಸ್ತಿ|ಆಸ್ತಿಯ|ಸ್ವತ್ತು|ಸ್ವತ್ತಿನ)\s*"
        + NUMBER_LABEL
    ),

    "registration_numbers": (
        r"ನೋಂದಣಿ\s*"
        + NUMBER_LABEL
    ),

    "flat_numbers": (
        r"ಫ್ಲಾಟ್\s*"
        + NUMBER_LABEL
    )
}


# ==================================================
# BOUNDARY SEPARATION
# ==================================================

BOUNDARY_PATTERN = (
    r"ಚಕ್ಕುಬಂದಿಗಳು"
    r"|ಚಕ್ಕುಬಂದಿ"
    r"|ಚಕ್ಕುಬದಿ"
    r"|ಚೆಕ್ಕುಬಂದಿ"
    r"|ಗಡಿಗಳು\s*:"
    r"|bounded\s+(?:as\s+under|by|on)"
    r"|boundaries\s*:"
    r"|east\s+by\s*:"
)


def split_property_sections(text):

    match = re.search(
        BOUNDARY_PATTERN,
        text,
        re.IGNORECASE
    )

    if match is None:

        return text, ""

    return (
        text[:match.start()].strip(),
        text[match.start():].strip()
    )


# ==================================================
# IDENTIFIER VALIDATION
# ==================================================

def validate_identifier(value, remaining_text=""):

    if not value:

        return False, "EMPTY_IDENTIFIER"

    if value.endswith(("/", "-")):

        return False, "INCOMPLETE_IDENTIFIER"

    if remaining_text.startswith(("/", "-")):

        return False, "POSSIBLE_TRUNCATION"

    if not re.fullmatch(
        r"[0-9]+(?:[/\-][0-9A-Za-z]+)*",
        value
    ):

        return False, "INVALID_IDENTIFIER_FORMAT"

    return True, None


# ==================================================
# CONTEXT SAFETY
# ==================================================

def is_loan_account_context(text, position):

    previous_text = text[
        max(0, position - 30):position
    ]

    return bool(

        re.search(
            r"(?:ಸಾಲದ|ಸಾಲಗಾರರ|loan)\s*$",
            previous_text,
            re.IGNORECASE
        )
    )


# ==================================================
# EXTRACT INDIVIDUAL IDENTIFIER GROUPS
# ==================================================

def extract_identifier_groups(
    text,
    field,
    label_pattern
):

    values = []

    invalid_values = []

    evidence = []

    pattern = (

        label_pattern

        + r"\s*[:.]?\s*"

        + r"(" + IDENTIFIER + r")"
    )

    for match in re.finditer(
        pattern,
        text,
        re.IGNORECASE
    ):

        if (

            field == "khata_numbers"

            and is_loan_account_context(
                text,
                match.start()
            )
        ):

            continue

        raw_value = match.group(1)

        # Preserve exact OCR evidence.

        candidates = [

            (raw_value, match.end())
        ]

        # Support lists such as:
        # Survey 108/4, 108/2 ಮತ್ತು 108/3.
        #
        # Limit continuation matching to survey
        # numbers to reduce accidental extraction
        # of dates, prices and measurements.

        if field == "survey_numbers":

            position = match.end()

            continuation_pattern = (

                r"\s*(?:,|ಮತ್ತು|and|&)\s*"

                r"(" + IDENTIFIER + r")"
            )

            while True:

                continuation = re.match(

                    continuation_pattern,

                    text[position:],

                    re.IGNORECASE
                )

                if continuation is None:

                    break

                next_value = continuation.group(1)

                next_position = (
                    position + continuation.end()
                )

                # Avoid consuming ordinary numbers
                # following comma-separated prose.

                if "/" not in next_value:

                    break

                candidates.append(
                    (next_value, next_position)
                )

                position = next_position

        for value, end_position in candidates:

            remaining_text = text[end_position:]

            valid, reason = validate_identifier(

                value,

                remaining_text
            )

            context = text[

                max(0, match.start() - 30):

                min(len(text), end_position + 40)
            ]

            record = {

                "field": field,

                "value": value,

                "valid_format": valid,

                "reason": reason,

                "source_text": context,

                "verified": False
            }

            evidence.append(record)

            if valid:

                if value not in values:

                    values.append(value)

            else:

                invalid_values.append(record)

    return {

        "values": values,

        "invalid_values": invalid_values,

        "evidence": evidence
    }


# ==================================================
# EXTRACT IDENTIFIERS FROM A SECTION
# ==================================================

def extract_section_identifiers(text):

    identifiers = {}

    invalid_identifiers = []

    evidence = []

    for field, pattern in PATTERNS.items():

        result = extract_identifier_groups(

            text,

            field,

            pattern
        )

        identifiers[field] = result["values"]

        invalid_identifiers.extend(
            result["invalid_values"]
        )

        evidence.extend(
            result["evidence"]
        )

    return {

        "identifiers": identifiers,

        "invalid_identifiers": invalid_identifiers,

        "evidence": evidence
    }


# ==================================================
# MAIN KANNADA IDENTIFIER PARSER
# ==================================================

def parse_kannada_identifiers(raw_text):

    text = normalize_text(raw_text)

    subject_text, boundary_text = (
        split_property_sections(text)
    )

    subject = extract_section_identifiers(
        subject_text
    )

    boundary = extract_section_identifiers(
        boundary_text
    )

    review_reasons = []

    if subject["invalid_identifiers"]:

        review_reasons.append(
            "Incomplete or invalid subject identifiers"
        )

    if boundary["invalid_identifiers"]:

        review_reasons.append(
            "Incomplete or invalid boundary identifiers"
        )

    boundary_marker_count = len(

        re.findall(
            BOUNDARY_PATTERN,
            text,
            re.IGNORECASE
        )
    )

    if boundary_marker_count > 1:

        review_reasons.append(
            "Repeated boundary markers require "
            "property schedule verification"
        )

    return {

        "subject_identifiers": (
            subject["identifiers"]
        ),

        "boundary_identifiers": (
            boundary["identifiers"]
        ),

        "invalid_subject_identifiers": (
            subject["invalid_identifiers"]
        ),

        "invalid_boundary_identifiers": (
            boundary["invalid_identifiers"]
        ),

        "subject_evidence": subject["evidence"],

        "boundary_evidence": boundary["evidence"],

        "subject_text": subject_text,

        "boundary_text": boundary_text,

        "requires_review": True,

        "verified": False,

        "review_reasons": review_reasons
    }
