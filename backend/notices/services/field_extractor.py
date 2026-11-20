import re


def find_value(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_notice_fields(text):

    fields = {
        "party_names": find_value([
            r"(?:Mr\.?|Mrs\.?|Ms\.?)\s+([A-Z][A-Za-z ]+)",
            r"(?:owner|applicant|claimant)\s*[:\-]\s*([^\n]+)",
        ], text),

        "village": find_value([
            r"village\s*[:\-]?\s*([A-Za-z ]+)",
        ], text),

        "taluk": find_value([
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
            r"(?:dated|date of publication|published on)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ], text),

        "response_deadline": find_value([
            r"(?:reply|respond|raise objections|submit objections)\s*(?:within)\s*(\d+)\s*days",
        ], text),
    }

    return fields
