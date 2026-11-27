
import re
import unicodedata


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize_location_text(text):

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
# LOCATION LABEL CONFIGURATION
# ==================================================

LOCATION_LABELS = {

    "district": (
        "ಜಿಲ್ಲೆ",
        "ಜಿಲ್ಲೆಯ",
        "ಜಿಲ್ಲ",
        "district"
    ),

    "taluk": (
        "ತಾಲೂಕು",
        "ತಾಲ್ಲೂಕು",
        "ತಾಲ್ಲೂಕಿನ",
        "ತಾಲೂಕಿನ",
        "taluk",
        "taluka"
    ),

    "hobli": (
        "ಹೋಬಳಿ",
        "ಹೋಬಳಿಯ",
        "ಹೋಬಳ",
        "ಹೋಬಖಳ",
        "ಹೋಬಳ.",
        "ಹೋಬಖಳ.",
        "hobli"
    ),

    "village": (
        "ಗ್ರಾಮ",
        "ಗ್ರಾಮದ",
        "ಗ್ರಾಮದಲ್ಲಿ",
        "ಗ್ರಾಮದಲ್ಲಿರುವ",
        "ಗ್ರಾಮದಲ್ಲಿನ",
        "ಗ್ರಾಮಕ್ಕೆ",
        "village"
    ),

    "layout": (
        "ಲೇಔಟ್",
        "ಬಡಾವಣೆ",
        "layout"
    ),

    "gram_panchayat": (
        "ಗ್ರಾಮ ಪಂಚಾಯತ್",
        "ಗ್ರಾಮ ಪಂಚಾಯಿತಿ",
        "gram panchayat"
    )
}


DIRECTION_WORDS = {

    "ಉತ್ತರ",
    "ಗ್ರಾಮಾಂತರ",
    "ನಗರ",
    "ದಕ್ಷಿಣ",
    "ಪೂರ್ವ",
    "ಪಶ್ಚಿಮ",

    "north",
    "south",
    "east",
    "west",
    "urban",
    "rural"
}


STOP_WORDS = {

    "ಸದರಿ",
    "ಸ್ವತ್ತಿನ",
    "ಆಸ್ತಿಯ",
    "ಸಂಬಂಧಿಸಿದ",
    "ಹೊಂದಿರುವ",
    "ಇರುವ",
    "ಮತ್ತು",
    "ಈ",
    "ರವರ",
    "ನಂ",

    "the",
    "of",
    "in",
    "at",
    "and",
    "said",
    "property",
    "bearing",
    "situated",
    "no",
    "number"
}


# Kannada and English place-name characters.

PLACE_TOKEN = (
    r"[A-Za-z\u0C80-\u0CFF]"
    r"[A-Za-z\u0C80-\u0CFF.'\-]*"
)


# ==================================================
# REMOVE DUPLICATE VALUES
# ==================================================

def unique_values(values):

    result = []
    seen = set()

    for value in values:

        value = value.strip(" ,.:;-")

        key = value.casefold()

        if value and key not in seen:

            result.append(value)
            seen.add(key)

    return result


# ==================================================
# EXTRACT LOCATION NAME BEFORE ITS LABEL
# ==================================================

def extract_suffix_locations(
    text,
    field,
    labels
):

    evidence = []

    alternatives = "|".join(

        re.escape(label)

        for label in sorted(
            labels,
            key=len,
            reverse=True
        )
    )

    pattern = (

        r"(?<![\w\u0C80-\u0CFF])"

        r"(" + PLACE_TOKEN + r")"

        r"\s+"

        r"(" + alternatives + r")"

        r"(?![\w\u0C80-\u0CFF])"
    )

    for match in re.finditer(
        pattern,
        text,
        re.IGNORECASE
    ):

        if field == "village":

            remaining = text[match.end():]

            if re.match(
                r"\s+(?:ಪಂಚಾಯತ್|ಪಂಚಾಯಿತಿ|panchayat)",
                remaining,
                re.IGNORECASE
            ):

                continue

        name = match.group(1).strip(".")

        label = match.group(2)

        if name.casefold() in STOP_WORDS:

            continue

        start_position = match.start()

        # Preserve directional taluk and district
        # names such as Bengaluru North.

        if name.casefold() in DIRECTION_WORDS:

            previous_text = text[
                :match.start(1)
            ]

            previous_match = re.search(

                r"(" + PLACE_TOKEN + r")\s+$",

                previous_text
            )

            if previous_match:

                previous_name = (
                    previous_match.group(1)
                )

                if (

                    previous_name.casefold()

                    not in STOP_WORDS
                ):

                    name = (
                        previous_name
                        + " "
                        + name
                    )

                    start_position = (
                        previous_match.start()
                    )

        if len(name) < 2:

            continue

        evidence.append({

            "field": field,

            "value": name,

            "label": label,

            "source_text": text[
                max(0, start_position - 30):
                min(len(text), match.end() + 30)
            ],

            "verified": False
        })

    return evidence


# ==================================================
# EXTRACT EXPLICIT ENGLISH LOCATION LABELS
# ==================================================

def extract_prefix_locations(text, field):

    evidence = []

    label = field.replace("_", " ")

    pattern = (

        r"\b"

        + re.escape(label)

        + r"\s*:\s*"

        + r"(" + PLACE_TOKEN

        + r"(?:\s+" + PLACE_TOKEN + r"){0,3})"
    )

    for match in re.finditer(
        pattern,
        text,
        re.IGNORECASE
    ):

        value = match.group(1).strip()

        tokens = value.split()

        cleaned = []

        for token in tokens:

            if token.casefold() in STOP_WORDS:

                break

            cleaned.append(token)

        value = " ".join(cleaned)

        if not value:

            continue

        evidence.append({

            "field": field,

            "value": value,

            "label": label,

            "source_text": text[
                max(0, match.start() - 30):
                min(len(text), match.end() + 30)
            ],

            "verified": False
        })

    return evidence


# ==================================================
# PIN CODE EXTRACTION
# ==================================================

def extract_pin_codes(text):

    return unique_values(

        re.findall(
            r"(?<!\d)[1-9]\d{5}(?!\d)",
            text
        )
    )


# ==================================================
# WARD NUMBER EXTRACTION
# ==================================================

def extract_ward_numbers(text):

    pattern = (

        r"(?:ವಾರ್ಡ್|ward)"

        r"\s*"

        r"(?:ನಂ\.?|ಸಂ\.?|ಸಂಖ್ಯೆ|no\.?|number)?"

        r"\s*[:.]?\s*"

        r"(\d{1,3})(?!\d)"
    )

    return unique_values(

        re.findall(
            pattern,
            text,
            re.IGNORECASE
        )
    )


# ==================================================
# MAIN LOCATION EXTRACTOR
# ==================================================

def extract_property_locations(raw_text):

    text = normalize_location_text(raw_text)

    candidates = {}
    evidence = []

    for field, labels in LOCATION_LABELS.items():

        suffix_results = (
            extract_suffix_locations(
                text,
                field,
                labels
            )
        )

        prefix_results = (
            extract_prefix_locations(
                text,
                field
            )
        )

        field_evidence = (
            suffix_results
            + prefix_results
        )

        candidates[field] = unique_values([

            item["value"]

            for item in field_evidence
        ])

        evidence.extend(field_evidence)

    candidates["pin_code"] = (
        extract_pin_codes(text)
    )

    candidates["ward_number"] = (
        extract_ward_numbers(text)
    )

    # Explicit state references only.
    # Do not infer state from the newspaper.

    candidates["state"] = unique_values(

        re.findall(

            r"(?<![\w\u0C80-\u0CFF])"
            r"(?:ಕರ್ನಾಟಕ|Karnataka)"
            r"(?![\w\u0C80-\u0CFF])",

            text,
            re.IGNORECASE
        )
    )

    ambiguous_fields = [

        field

        for field, values in candidates.items()

        if len(values) > 1
    ]

    # These are candidate locations, not verified
    # associations with the subject property.

    return {

        "location_candidates": candidates,

        "location_evidence": evidence,

        "ambiguous_location_fields": (
            ambiguous_fields
        ),

        "property_address": None,

        "requires_review": True,

        "verified": False,

        "review_reasons": [

            "Location candidates require subject "
            "property association verification",

            "Party, advocate and bank addresses "
            "may appear in the same notice"
        ]
    }
