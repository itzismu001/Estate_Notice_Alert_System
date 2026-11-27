
import re

from notices.services.location_extractor import (
    normalize_location_text,
    extract_property_locations
)

from notices.services.location_validator import (
    validate_location_candidates
)


# ==================================================
# PROPERTY DESCRIPTION MARKERS
# ==================================================

PROPERTY_MARKERS = (

    "schedule property",

    "scheduled property",

    "schedule of property",

    "property schedule",

    "description of property",

    "description of immovable property",

    "immovable property bearing",

    "property bearing",

    "property situated",

    "property located",

    "ಸ್ವತ್ತಿನ ವಿವರ",
    "ಸ್ಥತ್ತಿನ ವಿವರ",
    "ಪಹಣಿಯ ವಿವರ",

    "ಸ್ವತ್ತಿನ ವಿವರಣೆ",

    "ಸ್ಥಿರಾಸ್ತಿಯ ವಿವರ",

    "ಸ್ಥಿರ ಆಸ್ತಿಯ ವಿವರಣೆ",

    "ಆಸ್ತಿಯ ವಿವರ",

    "ಅಡಮಾನಿತ ಆಸ್ತಿಯ ವಿವರ",

    "ಷೆಡ್ಯೂಲ್ ಸ್ವತ್ತು",

    "ಷೆಡ್ಯೂಲ್ ಆಸ್ತಿ",

    "ಪೆಡ್ಯೂಲ್ ಸ್ಥತ್ತಿನ ವಿವರ"
)


# ==================================================
# PROPERTY IDENTIFIER MARKERS
# ==================================================

IDENTIFIER_PATTERN = (

    r"(?:"

    r"\bsurvey\s*(?:no\.?|number)"

    r"|\bsy\.?\s*no\.?"

    r"|\bsite\s*(?:no\.?|number)"

    r"|\bplot\s*(?:no\.?|number)"

    r"|\bpid\s*(?:no\.?|number)?"

    r"|ಸರ್ವ[ೆೇ]\s*(?:ನಂ\.?|ಸಂ\.?|ಸಂಖ್ಯೆ)"

    r"|(?:ನಿವೇಶನ|ಸೈಟ್)\s*"

    r"(?:ನಂ\.?|ಸಂ\.?|ಸಂಖ್ಯೆ)"

    r")"

    r"\s*[:.]?\s*\d+"
)


# ==================================================
# NON-PROPERTY ADDRESS MARKERS
# ==================================================

NON_PROPERTY_MARKERS = (

    "advocate office",
    "advocate ba",
    "advocate llb",
    "advocate ll.b",
    "advocate, office",
    "office :",
    "office:",
    "mobile :",
    "mobile:",
    "e-mail id",

    "advocate's office",

    "office address",

    "registered office",

    "branch office",

    "address of advocate",

    "residential address",

    "residing at",

    "resident of",

    "borrower address",

    "ವಕೀಲರು",

    "ವಕೀಲರ ವಿಳಾಸ",

    "ಕಛೇರಿ ವಿಳಾಸ",

    "ಕಚೇರಿ ವಿಳಾಸ",

    "ನೋಂದಾಯಿತ ಕಛೇರಿ",

    "ಶಾಖಾ ಕಛೇರಿ",

    "ಶಾಖಾ ಕಚೇರಿ",

    "ವಾಸ ನಂ",
    "ವಾಸ "
)


# ==================================================
# BOUNDARY MARKERS
# ==================================================

BOUNDARY_PATTERN = (

    r"ಚಕ್ಕುಬಂದಿಗಳು"

    r"|ಚಕ್ಕುಬಂದಿ"

    r"|ಚಕ್ಕುಬದಿ"

    r"|ಚೆಕ್ಕುಬಂದಿ"

    r"|bounded\s+(?:by|on|as\s+under)"

    r"|boundaries\s*:"

    r"|east\s+by\s*:"
)


# ==================================================
# FIND TEXT MARKERS
# ==================================================

def find_markers(text, markers):

    pattern = "|".join(

        re.escape(marker)

        for marker in sorted(
            markers,
            key=len,
            reverse=True
        )
    )

    return list(

        re.finditer(

            pattern,

            text,

            re.IGNORECASE
        )
    )


# ==================================================
# FIND EXPLICIT PROPERTY DESCRIPTION SECTIONS
# ==================================================

def extract_property_sections(text):

    text = normalize_location_text(text)

    markers = find_markers(
        text,
        PROPERTY_MARKERS
    )

    sections = []

    for index, marker in enumerate(markers):

        start = marker.start()

        end = (

            markers[index + 1].start()

            if index + 1 < len(markers)

            else len(text)
        )

        section = text[start:end]

        # Exclude later non-property addresses.

        stop_markers = find_markers(

            section[marker.end() - start:],

            NON_PROPERTY_MARKERS
        )

        if stop_markers:

            end = (

                marker.end()

                + stop_markers[0].start()
            )

            section = text[start:end]

        # Boundary descriptions can contain
        # neighbouring property locations.

        boundary = re.search(

            BOUNDARY_PATTERN,

            section,

            re.IGNORECASE
        )

        if boundary:

            end = start + boundary.start()

            section = text[start:end]

        if section.strip():

            sections.append({

                "text": section.strip(),

                "start": start,

                "end": end,

                "method": "EXPLICIT_PROPERTY_SECTION",

                "marker": marker.group(),

                "verified": False
            })

    return sections


# ==================================================
# IDENTIFIER PROXIMITY FALLBACK
# ==================================================

def extract_identifier_contexts(
    text,
    window=180
):

    text = normalize_location_text(text)

    contexts = []

    for match in re.finditer(

        IDENTIFIER_PATTERN,

        text,

        re.IGNORECASE
    ):

        start = max(

            0,

            match.start() - window
        )

        end = min(

            len(text),

            match.end() + window
        )

        # Restrict context to text after the most
        # recent non-property address marker.

        previous_markers = find_markers(

            text[start:match.start()],

            NON_PROPERTY_MARKERS
        )

        if previous_markers:

            start += previous_markers[-1].end()

        # Stop before later address markers.

        following_markers = find_markers(

            text[match.end():end],

            NON_PROPERTY_MARKERS
        )

        if following_markers:

            end = (

                match.end()

                + following_markers[0].start()
            )

        # Prevent crossing into a boundary section.

        boundary = re.search(

            BOUNDARY_PATTERN,

            text[match.end():end],

            re.IGNORECASE
        )

        if boundary:

            end = (

                match.end()

                + boundary.start()
            )

        # A previous boundary marker makes this
        # identifier's property role uncertain.

        previous_boundary = re.search(

            BOUNDARY_PATTERN,

            text[:match.start()],

            re.IGNORECASE
        )

        if previous_boundary:

            continue

        prefix = text[start:match.start()]

        property_transitions = list(

            re.finditer(

                r"ಇವರುಗಳೇ|ಇವರೇ|"
                r"whereas|"
                r"in respect of|"
                r"property situated",

                prefix,

                re.IGNORECASE
            )
        )

        if property_transitions:

            start += property_transitions[-1].end()

        context = text[start:end].strip()

        if context:

            contexts.append({

                "text": context,

                "start": start,

                "end": end,

                "method": "IDENTIFIER_PROXIMITY",

                "marker": match.group(),

                "verified": False
            })

    return contexts


# ==================================================
# MAIN LOCATION ASSOCIATION
# ==================================================

def associate_property_locations(raw_text):

    text = normalize_location_text(
        raw_text
    )

    # Preserve every location in the original notice.

    original_locations = validate_location_candidates(

        text,

        extract_property_locations(text)
    )

    sections = extract_property_sections(
        text
    )

    method = "EXPLICIT_PROPERTY_SECTION"

    if not sections:

        sections = extract_identifier_contexts(
            text
        )

        method = "IDENTIFIER_PROXIMITY"

    if not sections:

        method = "NO_PROPERTY_CONTEXT"

    candidates = {}

    evidence = []

    for section in sections:

        section_result = (
            validate_location_candidates(

                section["text"],

                extract_property_locations(
                    section["text"]
                )
            )
        )

        section_candidates = section_result[
            "normalized_location_candidates"
        ]

        for field, values in section_candidates.items():

            candidates.setdefault(
                field,
                []
            )

            for value in values:

                existing = [

                    item.casefold()

                    for item in candidates[field]
                ]

                if value.casefold() not in existing:

                    candidates[field].append(value)

                evidence.append({

                    "field": field,

                    "value": value,

                    "association_method": (
                        section["method"]
                    ),

                    "source_text": section["text"],

                    "verified": False
                })

    ambiguous_fields = [

        field

        for field, values in candidates.items()

        if len(values) > 1
    ]

    return {

        "association_method": method,

        "property_location_candidates": candidates,

        "all_notice_location_candidates": (

            original_locations[
                "normalized_location_candidates"
            ]
        ),

        "property_sections": sections,

        "location_association_evidence": evidence,

        "ambiguous_location_fields": ambiguous_fields,

        "property_address": None,

        "requires_review": True,

        "verified": False,

        "review_reasons": [

            "Property location association is heuristic",

            "Location candidates require human verification",

            "Multiple property schedules may require separation"
        ]
    }
