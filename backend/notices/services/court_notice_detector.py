
import re
import unicodedata


# ==================================================
# COURT-RELATED TERMINOLOGY
# ==================================================

COURT_TERMS = (

    "in the court of",
    "civil court",
    "civil judge",
    "district judge",
    "senior civil judge",
    "hon'ble court",
    "court of the",
    "court notice",
    "court summons",
    "city civil court",
    "judicial magistrate",
    "ನ್ಯಾಯಾಲಯ",
    "ನ್ಯಾಯಾಧೀಶ",
    "ಸಿವಿಲ್ ನ್ಯಾಯಾಲಯ",
    "ನ್ಯಾಯಾಲಯದ ಸೂಚನೆ",
    "ನ್ಯಾಯಾಲಯದ ಸಮನ್ಸ್",
)


PROCEEDING_TERMS = (

    "plaintiff",
    "defendant",
    "petitioner",
    "respondent",
    "summons",
    "civil suit",
    "partition suit",
    "suit for partition",
    "pending adjudication",
    "pending litigation",
    "injunction",
    "decree",
    "appearance before",
    "ವಾದಿ",
    "ಪ್ರತಿವಾದಿ",
    "ದಾವೆ",
    "ಸಮನ್ಸ್",
    "ತಡೆಯಾಜ್ಞೆ",
)


# ==================================================
# PROPERTY-RELATED TERMINOLOGY
# ==================================================

PROPERTY_TERMS = (

    "immovable property",
    "agricultural land",
    "schedule property",
    "scheduled property",
    "suit schedule property",
    "schedule of property",
    "property schedule",
    "survey number",
    "survey no",
    "sy. no",
    "sy.no",
    "site number",
    "site no",
    "plot number",
    "plot no",
    "khata number",
    "khata no",
    "ಸ್ಥಿರಾಸ್ತಿ",
    "ಸ್ಥಿರ ಆಸ್ತಿ",
    "ಜಮೀನು",
    "ನಿವೇಶನ",
    "ಸರ್ವೆ",
    "ಖಾತೆ ಸಂಖ್ಯೆ",
    "ಚಕ್ಕುಬಂದಿ",
)


PROPERTY_DISPUTE_TERMS = (

    "partition",
    "property dispute",
    "land dispute",
    "declaration of title",
    "ownership dispute",
    "right title and interest",
    "separate possession",
    "permanent injunction",
    "temporary injunction",
    "disputed property",
    "ಭಾಗಪತ್ರ",
    "ಆಸ್ತಿ ವಿವಾದ",
    "ಜಮೀನು ವಿವಾದ",
    "ಹಕ್ಕು",
)


# ==================================================
# NON-PROPERTY PROCEEDINGS
# ==================================================

NON_PROPERTY_TERMS = (

    "recovery of money",
    "money recovery",
    "recovery of loan",
    "money suit",
    "dishonour of cheque",
    "cheque bounce",
    "divorce",
    "dissolution of marriage",
    "maintenance petition",
    "criminal complaint",
    "ಹಣ ವಸೂಲಾತಿ",
    "ವಿಚ್ಛೇದನ",
)


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

    text = text.replace("’", "'")

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
    ).strip().casefold()


def find_terms(text, terms):

    return [

        term

        for term in terms

        if normalize_text(term) in text
    ]


# ==================================================
# COURT CASE NUMBER EXTRACTION
# ==================================================

def extract_case_numbers(text):

    pattern = (

        r"\b("
        r"(?:[o0]\s*\.?\s*s"
        r"|r\s*\.?\s*a"
        r"|r\s*\.?\s*s"
        r"|e\s*\.?\s*p"
        r"|m\s*\.?\s*c)"
        r"\.?\s*"
        r"(?:no\.?\s*)?"
        r"\d+\s*/\s*\d{4}"
        r")\b"
    )

    return list(dict.fromkeys(

        match.strip()

        for match in re.findall(
            pattern,
            text,
            re.IGNORECASE
        )
    ))


# ==================================================
# MAIN COURT NOTICE CLASSIFIER
# ==================================================

def detect_property_court_notice(raw_text):

    text = normalize_text(raw_text)

    court_terms = find_terms(
        text,
        COURT_TERMS
    )

    proceeding_terms = find_terms(
        text,
        PROCEEDING_TERMS
    )

    property_terms = find_terms(
        text,
        PROPERTY_TERMS
    )

    dispute_terms = find_terms(
        text,
        PROPERTY_DISPUTE_TERMS
    )

    non_property_terms = find_terms(
        text,
        NON_PROPERTY_TERMS
    )

    case_numbers = extract_case_numbers(
        raw_text or ""
    )

    # Court references alone are insufficient.

    has_court_context = bool(
        court_terms or case_numbers
    )

    has_proceeding_context = bool(
        proceeding_terms or case_numbers
    )

    has_property_context = bool(
        property_terms
    )

    matched = (

        has_court_context

        and has_proceeding_context

        and has_property_context
    )

    if matched and non_property_terms:

        reason = (
            "Court proceeding contains both "
            "property and non-property evidence"
        )

    elif matched:

        reason = (
            "Court proceeding contains "
            "immovable property evidence"
        )

    elif has_court_context:

        reason = (
            "Court proceeding without "
            "sufficient property evidence"
        )

    else:

        reason = "Court notice not identified"

    category = None

    if matched:

        category = "PROPERTY_COURT_NOTICE"

        if "partition" in dispute_terms:

            category = "PROPERTY_PARTITION_PROCEEDING"

        elif any(

            "injunction" in term

            for term in dispute_terms
        ):

            category = "PROPERTY_INJUNCTION_PROCEEDING"

    return {

        "is_property_court_notice": matched,

        "notice_category": category,

        "recommended_decision": (
            "REVIEW" if matched else None
        ),

        "requires_review": matched,

        "reason": reason,

        "case_numbers": case_numbers,

        "court_terms": court_terms,

        "proceeding_terms": proceeding_terms,

        "property_terms": property_terms,

        "dispute_terms": dispute_terms,

        "non_property_terms": non_property_terms
    }
