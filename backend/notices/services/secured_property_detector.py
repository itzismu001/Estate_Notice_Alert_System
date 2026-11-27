
import re
import unicodedata


# ==================================================
# SECURED PROPERTY LEGAL TERMINOLOGY
# ==================================================

LEGAL_TERMS = (
    "sarfaesi",
    "sarfaes",
    "ಸರ್ಫೇಸಿ",
    "ಸರ್ಪೇಸಿ",
    "ಸಾರ್ಫೇಸಿ",
    "ಭದ್ರತಾ ಹಿತಾಸಕ್ತಿ",
    "ಭದ್ರತಾ ಆಸಕ್ತಿ",
    "ಸೆಕ್ಕೂರಿಟಿ ಇಂಟರೆಸ್ಟ್",
    "ಸೆಕ್ಯುರಿಟಿ ಇಂಟರೆಸ್ಟ್",
    "ಸೆಕ್ಕೂರಿಟೈಜೇಶನ್",
    "securitisation",
    "security interest",
    "secured creditor",
    "ಸೆಕ್ಕೂರ್ಡ್ ಕ್ರೆಡಿಟರ್",
)


PROPERTY_TERMS = (
    "immovable property",
    "immovable properties",
    "secured property",
    "mortgaged property",
    "ಸ್ಥಿರಾಸ್ತಿ",
    "ಸ್ಥಿರ ಆಸ್ತಿ",
    "ಸ್ಥಿರಾಸ್ತಿಗಳ",
    "ಸ್ಥಿರಾಸ್ತಿಯ",
    "ಅಡಮಾನಿತ ಆಸ್ತಿ",
    "ಅಡಮಾನಿತ ಸ್ಥಿರಾಸ್ತಿ",
    "ಭದ್ರತಾ ಆಸ್ತಿ",
    "ವಸತಿ ನಿವೇಶನ",
    "survey no",
    "ಸರ್ವೆ ನಂ",
    "ನಿವೇಶನ ನಂ",
    "ಖಾತಾ ನಂ",
    "ಖಾತೆ ಸಂಖ್ಯೆ",
)


DEMAND_TERMS = (
    "demand notice",
    "ಡಿಮಾಂಡ್ ನೋಟಿಸ್",
    "ಡಿಮಾಂಡ್ ನೋಟೀಸ್",
    "ಡಿಮ್ಯಾಂಡ್ ನೋಟಿಸ್",
    "ಡಿಮ್ಯಾಂಡ್ ನೋಟೀಸ್",
)


POSSESSION_TERMS = (
    "possession notice",
    "symbolic possession",
    "physical possession",
    "ಸ್ವಾಧೀನ ಸೂಚನೆ",
    "ಸ್ವಾಧೀನತೆ",
    "ಸಾಂಕೇತಿಕ ಸ್ವಾಧೀನ",
    "ಸ್ವಾಧೀನಪಡಿಸಿಕೊಂಡ",
    "ಸ್ವಾಧೀನಕ್ಕೆ ಪಡೆದುಕೊಂಡ",
    "ಸ್ವಾಧೀನವನ್ನು ಪಡೆದುಕೊಂಡ",
    "ಸ್ವಾಧೀನವನ್ನು ತೆಗೆದುಕೊಳ್ಳಲಾಗಿದೆ",
)


AUCTION_TERMS = (
    "e-auction",
    "auction sale",
    "sale notice",
    "ಹರಾಜು ಮಾರಾಟ",
    "ಇ-ಹರಾಜು",
    "ಈ-ಹರಾಜು",
    "ಹರಾಜು ಮಾಡಲಾಗುವ",
    "ಮೀಸಲು ಬೆಲೆ",
)


GOLD_TERMS = (
    "gold jewellery",
    "gold ornaments",
    "ಚಿನ್ನಾಭರಣ",
    "ಚಿನ್ನದ ಅಭರಣ",
    "ಚಿನ್ನದ ಆಭರಣ",
    "ಅಡವಿಟ್ಟ ಚಿನ್ನ",
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

    text = text.translate(
        str.maketrans(
            "೦೧೨೩೪೫೬೭೮೯",
            "0123456789"
        )
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip().casefold()


# ==================================================
# KEYWORD MATCHING
# ==================================================

def find_terms(text, terms):

    return [
        term
        for term in terms
        if normalize_text(term) in text
    ]


# ==================================================
# LEGAL SECTION DETECTION
# ==================================================

def find_legal_sections(text):

    sections = []

    patterns = {
        "13(2)": r"(?<!\d)13\s*\(\s*2\s*\)",
        "13(4)": r"(?<!\d)13\s*\(\s*4\s*\)",
        "8(1)": r"(?<!\d)8\s*\(\s*1\s*\)",
        "8(6)": r"(?<!\d)8\s*\(\s*6\s*\)",
    }

    for section, pattern in patterns.items():

        if re.search(pattern, text):

            sections.append(section)

    return sections


# ==================================================
# MAIN SECURED PROPERTY DETECTOR
# ==================================================

def detect_secured_property_notice(raw_text):

    text = normalize_text(raw_text)

    legal = find_terms(
        text,
        LEGAL_TERMS
    )

    property_terms = find_terms(
        text,
        PROPERTY_TERMS
    )

    demand = find_terms(
        text,
        DEMAND_TERMS
    )

    possession = find_terms(
        text,
        POSSESSION_TERMS
    )

    auction = find_terms(
        text,
        AUCTION_TERMS
    )

    gold = find_terms(
        text,
        GOLD_TERMS
    )

    sections = find_legal_sections(text)

    has_legal_context = bool(
        legal or sections
    )

    has_property_context = bool(
        property_terms
    )

    has_secured_action = bool(
        demand or possession or auction or sections
    )

    matched = (
        has_legal_context
        and has_property_context
        and has_secured_action
    )

    notice_category = None
    recommended_decision = None

    if matched:

        # Auction notices may mention earlier
        # demand and possession proceedings.

        if auction:

            notice_category = (
                "SECURED_PROPERTY_AUCTION"
            )

        elif possession or "13(4)" in sections:

            notice_category = (
                "SECURED_PROPERTY_POSSESSION"
            )

        elif demand or "13(2)" in sections:

            notice_category = (
                "SECURED_PROPERTY_DEMAND"
            )

        else:

            notice_category = (
                "SECURED_PROPERTY_OTHER"
            )

        recommended_decision = "REVIEW"

    if matched and gold:

        reason = (
            "Conflicting gold and immovable "
            "property evidence requires review"
        )

    elif matched:

        reason = (
            "Secured immovable property notice "
            "requires scope and category verification"
        )

    elif gold and not has_property_context:

        reason = "Gold auction without property evidence"

    else:

        reason = (
            "Insufficient secured property evidence"
        )

    return {

        "is_secured_property_notice": matched,

        "notice_category": notice_category,

        "recommended_decision": recommended_decision,

        "requires_review": matched,

        "reason": reason,

        "legal_terms": legal,

        "property_terms": property_terms,

        "demand_terms": demand,

        "possession_terms": possession,

        "auction_terms": auction,

        "gold_terms": gold,

        "legal_sections": sections

    }
