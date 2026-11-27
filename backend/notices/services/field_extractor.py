
import re


# ==================================================
# COMMON EXTRACTION UTILITIES
# ==================================================

def find_value(patterns, text):

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = re.sub(
                r"\s+",
                " ",
                match.group(1)
            ).strip()

            return value or None

    return None


def unique_values(values):

    result = []
    seen = set()

    for value in values:

        value = value.strip()
        key = value.casefold()

        if value and key not in seen:

            seen.add(key)
            result.append(value)

    return result


def first_value(values):

    return values[0] if values else None


# ==================================================
# PROPERTY IDENTIFIER EXTRACTION
# ==================================================

IDENTIFIER_LABELS = {

    "survey_numbers": (
        r"(?:survey|sy\.?)\s*"
        r"(?:numbers?|nos?\.?)"
    ),

    "subdivision_numbers": (
        r"(?:sub[\s-]?division)\s*"
        r"(?:numbers?|nos?\.?)?"
    ),

    "plot_numbers": (
        r"plot\s*(?:numbers?|nos?\.?)"
    ),

    "site_numbers": (
        r"site\s*(?:numbers?|nos?\.?)"
    ),

    "hissa_numbers": (
        r"hissa\s*(?:numbers?|nos?\.?)"
    ),

    "khata_numbers": (
        r"(?:khata|katha)\s*"
        r"(?:numbers?|nos?\.?)"
    ),

    "property_numbers": (
        r"property\s*(?:numbers?|nos?\.?)"
    ),

    "pid_numbers": (
        r"pid\s*(?:numbers?|nos?\.?)?"
    ),

    "tp_numbers": (
        r"(?:tp|town\s+planning)\s*"
        r"(?:numbers?|nos?\.?)"
    ),

    "municipal_numbers": (
        r"municipal\s*(?:numbers?|nos?\.?)"
    ),

    "flat_numbers": (
        r"flat\s*(?:numbers?|nos?\.?)"
    ),

    "khasra_numbers": (
        r"khasra\s*(?:numbers?|nos?\.?)"
    ),

    "document_numbers": (
        r"document\s*(?:numbers?|nos?\.?)"
    ),

}


# Identifiers must contain a numeric component.
IDENTIFIER_VALUE = (
    r"(?:[A-Za-z]{1,5}-)?[A-Za-z]?\d+"
    r"(?:[/-][A-Za-z0-9]+)*"
    r"[A-Za-z]?"
)


def extract_identifiers(text, label_pattern):

    values = []

    pattern = (
        r"\b"
        + label_pattern
        + r"\s*[:\-]?\s*"
        + r"(" + IDENTIFIER_VALUE + r")"
    )

    for match in re.finditer(
        pattern,
        text,
        re.IGNORECASE
    ):

        values.append(match.group(1))

        # Look for additional identifiers
        # separated by commas, "and", or "&".

        remaining = text[match.end():]

        continuation = (
            r"^\s*(?:,|;|and\b|&)\s*"
            r"(" + IDENTIFIER_VALUE + r")"
        )

        while remaining:

            next_match = re.match(
                continuation,
                remaining,
                re.IGNORECASE
            )

            if not next_match:
                break

            values.append(
                next_match.group(1)
            )

            remaining = remaining[
                next_match.end():
            ]

    return unique_values(values)


# ==================================================
# KHASRA NUMBER EXTRACTION
# ==================================================

def extract_khasra_numbers(text):

    values = []

    label = (
        r"\bkhasra\s*"
        r"(?:numbers?|nos?\.?)"
        r"\s*[:\-]?\s*"
    )

    for match in re.finditer(
        label,
        text,
        re.IGNORECASE
    ):

        remaining = text[match.end():]

        # Khasra numbers may contain "min"
        # and land measurement annotations.

        entry_pattern = (
            r"^\s*"
            r"(" + IDENTIFIER_VALUE + r")"
            r"\s*(?:min\b)?"
            r"\s*(?:\([^)]*\))?"
        )

        while remaining:

            entry = re.match(
                entry_pattern,
                remaining,
                re.IGNORECASE
            )

            if not entry:
                break

            values.append(entry.group(1))

            remaining = remaining[entry.end():]

            separator = re.match(
                r"^\s*(?:,|;|and\b|&)\s*",
                remaining,
                re.IGNORECASE
            )

            if not separator:
                break

            remaining = remaining[
                separator.end():
            ]

    return unique_values(values)


# ==================================================
# LOCATION EXTRACTION
# ==================================================

def extract_location(text, label_pattern):

    pattern = (
        r"\b(?:"
        + label_pattern
        + r")\b"
        + r"[ \t]*[:\-]?[ \t]*"
        + r"([A-Za-z][A-Za-z .'-]*?)"
        + r"(?="
        + r",|;|\n|$"
        + r"|\s+(?:"
        + r"taluk|taluka|tehsil|tahsil|"
        + r"district|hobli|state|"
        + r"situated|bearing|measuring|"
        + r"survey|raise|government|govt|"
        + r"karnataka|haryana"
        + r")\b)"
    )

    value = find_value(
        [pattern],
        text
    )

    if value:
        return value.rstrip(" .")

    return None


# ==================================================
# PARTY NAME EXTRACTION
# ==================================================

def find_party_names(text):

    clean_text = re.sub(
        r"\s+",
        " ",
        text
    )

    # Case 1: Multiple numbered owners.

    owner_section = re.search(
        r"owners?\s*\(1\)(.*?)"
        r"(?=both resident|resident of|"
        r"Any entity|Any person)",
        clean_text,
        re.IGNORECASE
    )

    if owner_section:

        matches = re.findall(
            r"\(\d+\)\s*"
            r"(?:Mr\.?|Mrs\.?|Ms\.?)?\s*"
            r"([A-Z][A-Za-z]+"
            r"(?:\s+[A-Z][A-Za-z]+)*)"
            r"(?=\s+(?:D/o|S/o|both resident))",
            owner_section.group(0),
            re.IGNORECASE
        )

        if matches:

            return unique_values(matches)

    # Case 2: Numbered sellers.

    seller_section = re.search(
        r"from\s*\[1\](.*?)"
        r"(?=The aforesaid persons)",
        clean_text,
        re.IGNORECASE
    )

    if seller_section:

        matches = re.findall(
            r"\[\d+\]\s*SHRI\s+"
            r"(.+?)(?=,\s*S/o)",
            seller_section.group(0),
            re.IGNORECASE
        )

        if matches:

            return unique_values([
                name.strip().title()
                for name in matches
            ])

    # Case 3: Name after "belonging to".

    match = re.search(
        r"belonging to\s+(.+?)"
        r"(?:,\s*have|\s+have)",
        clean_text,
        re.IGNORECASE
    )

    if match:

        return [match.group(1).strip()]

    # Case 4: Explicit absolute owner.

    match = re.search(
        r"(?:absolute|lawful|registered)"
        r"\s+owner\s+"
        r"(?:Mr\.?|Mrs\.?|Ms\.?|Shri)?\s*"
        r"([A-Za-z][A-Za-z .'-]+?)"
        r"(?=\s+(?:S/o|D/o|W/o|"
        r"residing|resident)|,)",
        clean_text,
        re.IGNORECASE
    )

    if match:

        return [match.group(1).strip()]

    # A signature alone does not establish
    # whether the person owns the property.

    return None


# ==================================================
# ADVOCATE NAME EXTRACTION
# ==================================================

def find_advocate_name(text):

    return find_value([

        r"(?:^|\n)[ \t]*"
        r"([A-Za-z][A-Za-z .'-]{3,60})"
        r"[ \t]*\n[ \t]*Advocate\b",

        r"\bAdvocate[ \t]*[:\-][ \t]*"
        r"([A-Za-z][A-Za-z .'-]+)"

    ], text)


# ==================================================
# DATE AND DEADLINE EXTRACTION
# ==================================================

DATE_PATTERN = (
    r"\d{1,2}[./-]"
    r"\d{1,2}[./-]"
    r"\d{2,4}"
)


def extract_publication_date(text):

    return find_value([

        r"\b(?:date of publication|published on)"
        r"\s*[:\-]?\s*("
        + DATE_PATTERN + r")"

    ], text)


def extract_notice_date(text):

    return find_value([

        r"(?:^|\n)[ \t]*"
        r"(?:notice date|date|dated)"
        r"[ \t]*[:\-]?[ \t]*("
        + DATE_PATTERN + r")"

    ], text)


def extract_response_deadline(text):

    pattern = (
        r"\bwithin\s+"
        r"(?:a\s+period\s+of\s+)?"
        r"(\d+)\s*"
        r"(?:\([^)]+\)\s*)?"
        r"(days?|weeks?|months?)\b"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:

        return None, None

    value = match.group(1)
    unit = match.group(2).lower().rstrip("s")

    return value, unit


# ==================================================
# MAIN STRUCTURED FIELD EXTRACTOR
# ==================================================


# ==================================================
# OCR TEXT PREPROCESSING
# ==================================================

def preprocess_notice_text(text):

    text = text or ""

    # Normalize line endings.
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove common OCR border artifacts.
    text = re.sub(
        r"[|{}]+[ \t]*(?=\n|$)",
        "",
        text
    )

    # Repair selected broken words.
    broken_words = {
        r"\bsit-\s*\nuated\b": "situated",
        r"\bmeasur-\s*\ning\b": "measuring",
        r"\binher-\s*\nitance\b": "inheritance",
        r"\bregis-\s*\ntered\b": "registered",
        r"\bfail-\s*\ning\b": "failing",
        r"\bmis-\s*\nplaced\b": "misplaced",
    }

    for pattern, replacement in broken_words.items():

        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE
        )

    # Correct noise only in explicit contexts.
    corrections = {

        # Correct a Roman numeral OCR error
        # specifically within the Part-I address format.

        r"\bPart[ \t]*-[ \t]*\|(?=[ \t]*[,;.)]|\s|$)": "Part-I",

        r"\blagreed\b": "agreed",

        r"\bicharges\b": "charges",

        r"(\bwithin\s+\d+\s+)idays\b": r"\1days",
    }

    for pattern, replacement in corrections.items():

        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE
        )

    return text


# ==================================================
# PROPERTY BEARING NUMBERS
# ==================================================

def extract_bearing_numbers(text):

    values = []

    pattern = (
        r"\bbearing\s+"
        r"(?:property\s+)?"
        r"(?:nos?\.?|numbers?)"
        r"\s*[:\-]?\s*"
        r"(" + IDENTIFIER_VALUE + r")"
    )

    for match in re.finditer(
        pattern,
        text,
        re.IGNORECASE
    ):

        # Require nearby property context.
        preceding = text[
            max(0, match.start() - 350):
            match.start()
        ]

        if not re.search(
            r"\b(?:property|land|premises|"
            r"building|floor|plot|site|house)\b",
            preceding,
            re.IGNORECASE
        ):
            continue

        # Do not treat deed references as
        # property numbers.

        if re.search(
            r"(?:deed|document|registration)"
            r"[^.!?\n]{0,45}$",
            preceding,
            re.IGNORECASE
        ):
            continue

        values.append(match.group(1))

    return unique_values(values)


# ==================================================
# REAL-WORLD OWNER NAME EXTRACTION
# ==================================================

def extract_named_owners(text):

    clean_text = re.sub(r"\s+", " ", text)

    owner_section = re.search(

        r"\bowners?\s+namely\s*[:\-]?\s*"

        r"(.+?)"

        r"(?=\(\s*say\s+owners?\s*\)"
        r"|,\s*free\s+from"
        r"|,\s*residing"
        r"|both\s+resident"
        r"|any\s+other\s+person"
        r"|$)",

        clean_text,
        re.IGNORECASE
    )

    if not owner_section:
        return None

    section = owner_section.group(1)

    pattern = (

        r"(?:^|,|\band\b|\(\s*[ivx\d]+\s*\))"

        r"\s*['\"]?\s*"

        r"(?:Shri|Sri|Smt\.?|Mr\.?|Mrs\.?|Ms\.?)"

        r"\s+['\"]?"

        r"([A-Za-z][A-Za-z .'-]*?)"

        r"\s*(?=(?:S|D|W)\s*/\s*o\b)"
    )

    matches = re.findall(
        pattern,
        section,
        re.IGNORECASE
    )

    names = unique_values(matches)

    return names or None


# ==================================================
# PROPERTY ADDRESS EXTRACTION
# ==================================================

def extract_property_address(text):

    pattern = (

        r"\bsituated\s+(?:at|in)\s+"

        r"(.+?)"

        r"(?=\s*\("
        r"|,\s*measuring\b"
        r"|\s+measuring\b"
        r"|,\s*from\b"
        r"|\s+from\s+(?:its|the)\b"
        r"|;\s*"
        r"|$)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return None

    value = re.sub(
        r"\s+",
        " ",
        match.group(1)
    ).strip(" ,.")

    # Avoid capturing a large portion of the
    # notice when address boundaries are unclear.

    if len(value) > 250:
        return None

    return value or None


# ==================================================
# PROPERTY AREA AND LAND SHARE
# ==================================================

def extract_property_area(text):

    pattern = (

        r"\bmeasuring\s+"

        r"(\d[\d,]*(?:\.\d+)?)\s*"

        r"(sq\.?\s*(?:yds?\.?|yards?|"
        r"ft\.?|feet|mtrs?\.?|metres?|meters?)"
        r"|square\s+(?:yards?|feet|metres?|meters?)"
        r"|acres?|guntas?|hectares?)\b"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None, None

    value = match.group(1)

    unit = re.sub(
        r"[\s.]",
        "",
        match.group(2).lower()
    )

    unit_mapping = {
        "sqyd": "square_yards",
        "sqyds": "square_yards",
        "sqyard": "square_yards",
        "sqyards": "square_yards",
        "squareyard": "square_yards",
        "squareyards": "square_yards",
        "sqft": "square_feet",
        "sqfeet": "square_feet",
        "squarefeet": "square_feet",
        "sqmtr": "square_metres",
        "sqmtrs": "square_metres",
        "sqmetre": "square_metres",
        "sqmetres": "square_metres",
        "sqmeter": "square_metres",
        "sqmeters": "square_metres",
        "squaremetre": "square_metres",
        "squaremetres": "square_metres",
        "squaremeter": "square_metres",
        "squaremeters": "square_metres",
        "acre": "acres",
        "acres": "acres",
        "gunta": "guntas",
        "guntas": "guntas",
        "hectare": "hectares",
        "hectares": "hectares",
    }

    return value, unit_mapping.get(unit, unit)


def extract_land_share(text):

    return find_value([

        r"(\d+(?:\.\d+)?)\s*%\s*"
        r"undivided\s+share"

    ], text)


# ==================================================
# REGISTRATION AND SALE DEED DETAILS
# ==================================================

def extract_registration_numbers(text):

    return extract_identifiers(

        text,

        r"registration\s*(?:numbers?|nos?\.?)"
    )


def extract_sale_deed_date(text):

    return find_value([

        r"\bsale\s+deed\s+dated\s*("
        + DATE_PATTERN + r")"

    ], text)


# ==================================================
# EXTENDED ADVOCATE EXTRACTION
# ==================================================

def extract_parenthesized_advocate(text):

    return find_value([

        r"(?:^|\n)[ \t]*"
        r"([A-Za-z][A-Za-z .'-]{2,60}?)"
        r"[ \t]*\(\s*advocate\s*\)"

    ], text)



def extract_notice_fields(text):

    text = preprocess_notice_text(text)

    identifiers = {}

    for field_name, label_pattern in (
        IDENTIFIER_LABELS.items()
    ):

        identifiers[field_name] = (
            extract_identifiers(
                text,
                label_pattern
            )
        )

    identifiers["property_numbers"] = unique_values(
        identifiers["property_numbers"]
        + extract_bearing_numbers(text)
    )

    identifiers["khasra_numbers"] = (
        extract_khasra_numbers(text)
    )

    deadline, deadline_unit = (
        extract_response_deadline(text)
    )

    area, area_unit = extract_property_area(text)

    registration_numbers = extract_registration_numbers(text)

    # Preserve existing scalar fields for
    # compatibility with the current pipeline.

    fields = {

        "party_names": (
            extract_named_owners(text)
            or find_party_names(text)
        ),

        "village": extract_location(
            text,
            r"villages?"
        ),

        "taluk": extract_location(
            text,
            r"taluk|taluka|tehsil|tahsil"
        ),

        "district": extract_location(
            text,
            r"district|dist\.?"
        ),

        "hobli": extract_location(
            text,
            r"hobli"
        ),

        "survey_number": first_value(
            identifiers["survey_numbers"]
        ),

        "subdivision_number": first_value(
            identifiers["subdivision_numbers"]
        ),

        "plot_number": first_value(
            identifiers["plot_numbers"]
        ),

        "tp_number": first_value(
            identifiers["tp_numbers"]
        ),

        "site_number": first_value(
            identifiers["site_numbers"]
        ),

        "hissa_number": first_value(
            identifiers["hissa_numbers"]
        ),

        "khata_number": first_value(
            identifiers["khata_numbers"]
        ),

        "property_number": first_value(
            identifiers["property_numbers"]
        ),

        "pid_number": first_value(
            identifiers["pid_numbers"]
        ),

        "municipal_number": first_value(
            identifiers["municipal_numbers"]
        ),

        "flat_number": first_value(
            identifiers["flat_numbers"]
        ),

        "khasra_number": first_value(
            identifiers["khasra_numbers"]
        ),

        "publication_date": (
            extract_publication_date(text)
        ),

        "notice_date": (
            extract_notice_date(text)
        ),

        "response_deadline": deadline,

        "response_deadline_unit": deadline_unit,

        "advocate_name": (
            extract_parenthesized_advocate(text)
            or find_advocate_name(text)
        ),

        "property_address": extract_property_address(text),

        "property_area": area,

        "property_area_unit": area_unit,

        "land_share_percentage": extract_land_share(text),

        "registration_number": first_value(
            registration_numbers
        ),

        "registration_numbers": registration_numbers,

        "sale_deed_date": extract_sale_deed_date(text),

    }

    # Include complete lists of identifiers.

    fields.update(identifiers)

    return fields

