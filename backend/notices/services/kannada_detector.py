
import re
import unicodedata


# ==================================================
# KANNADA NOTICE KEYWORDS
# ==================================================

NOTICE_TERMS = (
    "ಸಾರ್ವಜನಿಕ ಪ್ರಕಟಣೆ",
    "ಸಾರ್ವಜನಿಕ ಪ್ರಕಟಣಿ",
    "ಸಾರ್ವಜನಿಕ ಸೂಚನೆ",
    "ಸಾರ್ವಜನಿಕರಿಗೆ",
    "ನೋಟಿಸ್",
    "ಸೂಚನೆ",
    "public notice",
)

PROPERTY_TERMS = (
    "ನಿವೇಶನ",
    "ಸ್ಥಿರಾಸ್ತಿ",
    "ಜಮೀನು",
    "ಸರ್ವೆ",
    "ಖಾತೆ ಸಂಖ್ಯೆ",
    "ಸ್ವತ್ತು",
    "ಸ್ವತ್ತಿನ",
    "ಕ್ರಯಪತ್ರ",
    "ಚಕ್ಕುಬಂದಿ",
    "ಪಿ.ಐ.ಡಿ",
    "ಚದರ ಅಡಿ",
    "ಗುಂಟೆ",
    "immovable property",
    "survey no",
)

STRONG_PROPERTY_TERMS = (
    "ನಿವೇಶನ",
    "ಸ್ಥಿರಾಸ್ತಿ",
    "ಜಮೀನು",
    "ಸರ್ವೆ",
    "ಕ್ರಯಪತ್ರ",
    "ಚಕ್ಕುಬಂದಿ",
    "ಪಿ.ಐ.ಡಿ",
    "immovable property",
    "survey no",
)

LEGAL_TERMS = (
    "ಮಾಲೀಕರ",
    "ಮಾಲಕರ",
    "ಕಕ್ಷಿದಾರ",
    "ಆಕ್ಷೇಪಣೆ",
    "ಖರೀದಿ",
    "ಕಳೆದುಹೋಗಿ",
    "ಕಳೆದುಕೊಂಡಿ",
    "ದಸ್ತಾವೇಜು",
    "ನೋಂದಣಿ",
    "ಹಕ್ಕು",
    "ವಕೀಲರು",
    "ಮಾರಾಟ",
    "ಅಡಮಾನ",
)

GOLD_TERMS = (
    "ಚಿನ್ನಾಭರಣ",
    "ಚಿನ್ನದ ಅಭರಣ",
    "ಚಿನ್ನದ ಆಭರಣ",
    "ಅಡವಿಟ್ಟ ಚಿನ್ನ",
    "gold ornaments",
    "gold jewellery",
)

COMPANY_TERMS = (
    "board of directors minutes book",
    "annual general meeting minutes book",
    "attendance sheets",
    "ಸಭೆಯ ನಡಾವಳ ಪುಸ್ತಕ",
)


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize_kannada_text(text):

    text = unicodedata.normalize(
        "NFC",
        text or ""
    )

    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip().casefold()


# ==================================================
# KEYWORD MATCHING
# ==================================================

def matched_terms(text, terms):

    return [
        term
        for term in terms
        if normalize_kannada_text(term) in text
    ]


# ==================================================
# KANNADA SCRIPT IDENTIFICATION
# ==================================================

def contains_kannada(text):

    return bool(
        re.search(
            r"[\u0C80-\u0CFF]",
            text or ""
        )
    )


# ==================================================
# MAIN KANNADA NOTICE CLASSIFIER
# ==================================================

def detect_kannada_notice(raw_text):

    text = normalize_kannada_text(raw_text)

    heading = matched_terms(
        text,
        NOTICE_TERMS
    )

    property_terms = matched_terms(
        text,
        PROPERTY_TERMS
    )

    strong_property = matched_terms(
        text,
        STRONG_PROPERTY_TERMS
    )

    legal = matched_terms(
        text,
        LEGAL_TERMS
    )

    gold = matched_terms(
        text,
        GOLD_TERMS
    )

    company = matched_terms(
        text,
        COMPANY_TERMS
    )

    # ----------------------------------------------
    # Calculate heuristic classification score.
    # ----------------------------------------------

    score = min(
        100,
        (25 if heading else 0)
        + min(len(property_terms), 3) * 10
        + min(len(strong_property), 2) * 10
        + min(len(legal), 5) * 5
    )

    # ----------------------------------------------
    # Classification rules.
    # ----------------------------------------------

    if not contains_kannada(raw_text):

        decision = "REJECT"
        reason = "Kannada script not detected"

    elif (gold or company) and not strong_property:

        decision = "REJECT"

        reason = (
            "Non-property document or gold auction"
        )

    elif gold or company:

        decision = "REVIEW"

        reason = (
            "Conflicting property and exclusion terms"
        )

    elif "sarfaesi" in text:

        decision = "REVIEW"

        reason = (
            "Secured-property notice scope verification"
        )

    elif heading and strong_property and legal:

        decision = "ACCEPT"

        reason = (
            "Property notice with legal context"
        )

    elif len(strong_property) >= 2 and legal:

        decision = "ACCEPT"

        reason = (
            "Strong property and legal context"
        )

    elif property_terms and legal:

        decision = "REVIEW"

        reason = (
            "Insufficient property-specific evidence"
        )

    else:

        decision = "REJECT"

        reason = (
            "Insufficient property notice evidence"
        )

    # ----------------------------------------------
    # Determine classification confidence.
    # ----------------------------------------------

    if decision == "ACCEPT":

        confidence = (
            "HIGH"
            if score >= 70
            else "MEDIUM"
        )

    elif decision == "REVIEW":

        confidence = "LOW"

    else:

        confidence = "LOW"

    # ----------------------------------------------
    # Return compatible detection result.
    # ----------------------------------------------

    return {

        "is_notice": decision == "ACCEPT",

        "notice_type": (
            "ESTATE_PROPERTY_NOTICE"
            if decision == "ACCEPT"
            else None
        ),

        "language": "kn",

        "decision": decision,

        "confidence": confidence,

        "score": score,

        "reason": reason,

        "requires_review": (
            decision in ("ACCEPT", "REVIEW")
        ),

        "matched_terms": {

            "notice_terms": heading,

            "property_terms": property_terms,

            "strong_property_terms": (
                strong_property
            ),

            "legal_terms": legal,

            "gold_terms": gold,

            "company_terms": company

        }
    }
