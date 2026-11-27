
import re


def find_value(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return None


def find_party_names(text):
    clean_text = re.sub(r"\s+", " ", text)

    # Case 1: Multiple numbered owners
    owner_section = re.search(
        r"owners?\s*\(1\)(.*?)(?=both resident|resident of|Any entity|Any person)",
        clean_text,
        re.IGNORECASE
    )

    if owner_section:
        matches = re.findall(
            r"\(\d+\)\s*(?:Mr\.?|Mrs\.?|Ms\.?)?\s*"
            r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)"
            r"(?=\s+(?:D/o|S/o|both resident))",
            owner_section.group(0),
            re.IGNORECASE
        )

        if matches:
            return [name.strip() for name in matches]

    # Case 2: Numbered sellers
    seller_section = re.search(
        r"from\s*\[1\](.*?)(?=The aforesaid persons)",
        clean_text,
        re.IGNORECASE
    )

    if seller_section:
        matches = re.findall(
            r"\[\d+\]\s*SHRI\s+(.+?)(?=,\s*S/o)",
            seller_section.group(0),
            re.IGNORECASE
        )

        if matches:
            return [name.strip().title() for name in matches]

    # Case 3: Name after belonging to
    match = re.search(
        r"belonging to\s+(.+?)(?:,\s*have|\s+have)",
        clean_text,
        re.IGNORECASE
    )

    if match:
        return [match.group(1).strip()]

    # Case 4: Name from notice signature
    match = re.search(
        r"\n\s*([A-Z][A-Z ]{3,})\s*\n\s*D-\d+",
        text
    )

    if match:
        return [match.group(1).strip().title()]

    return None


def extract_notice_fields(text):

    fields = {
        "party_names": find_party_names(text),

        "village": find_value([
            r"village\s+([A-Za-z ]+?)(?=,|\s+Tehsil|\s+Taluk|\s+District)",
            r"village\s*[:\-]?\s*([A-Za-z ]+)",
        ], text),

        "taluk": find_value([
            r"(?:taluk|taluka|tehsil)\s+([A-Za-z ]+?)(?=,|\s+New Delhi|\s+District)",
            r"(?:taluk|taluka|tehsil)\s*[:\-]?\s*([A-Za-z ]+)",
        ], text),

        "district": find_value([
            r"district\s*[:\-]?\s*([A-Za-z ]+)",
        ], text),

        "survey_number": find_value([
            r"(?:survey\s*(?:no\.?|number)|sy\.?\s*no\.?)\s*[:\-]?\s*([\d/-]+)",
        ], text),

        "subdivision_number": find_value([
            r"(?:subdivision|sub-division)\s*(?:no\.?|number)?\s*[:\-]?\s*([\d/,-]+)",
        ], text),

        "plot_number": find_value([
            r"(?:plot\s*(?:no\.?|number))\s*[:\-]?\s*([\w/-]+)",
        ], text),

        "tp_number": find_value([
            r"(?:tp\s*(?:no\.?|number)|town planning number)\s*[:\-]?\s*([\w/-]+)",
        ], text),

        "publication_date": find_value([
            r"(?:date of publication|published on|date)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        ], text),

        "response_deadline": find_value([
            r"within\s+(?:a\s+period\s+of\s+)?(\d+)\s*(?:\([^)]+\)\s*)?days",
        ], text),
    }

    return fields
