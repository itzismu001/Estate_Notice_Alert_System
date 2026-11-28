
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

        # Prevent a prefix value from being assigned
        # to the next English location label.
        if match.group(2).isascii():

            prefix_matches = find_english_prefix_locations(
                text
            )

            if any(
                item["_value_start"] <= match.start(1)
                < item["_value_end"]
                for item in prefix_matches
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

def find_english_prefix_locations(text):

    evidence = []

    english_labels = {
        label.casefold(): field
        for field, labels in LOCATION_LABELS.items()
        for label in labels
        if label.isascii()
    }

    alternatives = "|".join(
        re.escape(label)
        for label in sorted(
            english_labels,
            key=len,
            reverse=True
        )
    )

    label_pattern = re.compile(
        r"\b(" + alternatives + r")\b"
        r"(\s*:\s*|\s+)",
        re.IGNORECASE
    )

    stop_words = STOP_WORDS | {
        "raise", "objection", "objections",
        "within", "days", "notice", "public",
        "survey", "plot", "site", "khata",
        "pid", "ward", "pin", "code",
        "measuring", "measurement",
        "bounded", "boundaries",
        "advocate", "office", "court",
        "schedule", "owner", "claim",
        "claims", "hereby", "having",
        "belonging", "located"
    }

    label_words = {
        word
        for label in english_labels
        for word in label.split()
    }

    previous_end = None

    for match in label_pattern.finditer(text):

        label = match.group(1)
        field = english_labels[label.casefold()]

        before = text[:match.start()].rstrip()

        explicit_colon = ":" in match.group(2)

        follows_prefix = (
            previous_end is not None
            and not text[
                previous_end:match.start()
            ].strip()
        )

        starts_context = (
            not before
            or before[-1].isdigit()
            or before[-1] in ",;:("
        )

        if not (
            explicit_colon
            or follows_prefix
            or starts_context
        ):
            continue

        value_start = match.end()
        cursor = value_start
        value_end = value_start
        tokens = []

        for _ in range(4):

            token_match = re.match(
                PLACE_TOKEN,
                text[cursor:]
            )

            if not token_match:
                break

            token = token_match.group()
            cleaned = token.strip(".")
            key = cleaned.casefold()

            if (
                key in stop_words
                or key in label_words
                or not cleaned
            ):
                break

            # Without an explicit colon, use a
            # conservative English place-name heuristic.
            if not explicit_colon:
                if not (
                    cleaned[0].isupper()
                    or key in DIRECTION_WORDS
                ):
                    break

            tokens.append(cleaned)

            value_end = (
                cursor + token_match.end()
            )

            if token.endswith("."):
                break

            whitespace = re.match(
                r"\s+",
                text[value_end:]
            )

            if not whitespace:
                break

            cursor = (
                value_end + whitespace.end()
            )

        if not tokens:
            continue

        value = " ".join(tokens)

        evidence.append({
            "field": field,
            "value": value,
            "label": label,
            "source_text": text[
                max(0, match.start() - 30):
                min(len(text), value_end + 30)
            ],
            "verified": False,
            "_label_start": match.start(),
            "_value_start": value_start,
            "_value_end": value_end
        })

        previous_end = value_end

    return evidence


def extract_prefix_locations(text, field):

    return [
        {
            key: value
            for key, value in item.items()
            if not key.startswith("_")
        }
        for item in find_english_prefix_locations(text)
        if item["field"] == field
    ]


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
