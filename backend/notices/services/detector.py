import re


NOTICE_TERMS = [
    "public notice",
    "legal notice",
    "court notice",
    "notice to the public",
]

PROPERTY_TERMS = [
    "land",
    "property",
    "survey number",
    "survey no",
    "plot number",
    "plot no",
    "village",
    "immovable property",
]

LEGAL_TERMS = [
    "claim",
    "objection",
    "legal heirs",
    "ownership",
    "title deed",
    "sale deed",
    "mortgage",
]


def detect_notice(text):
    text_lower = text.lower()

    matched_notice_terms = [
        term for term in NOTICE_TERMS if term in text_lower
    ]

    matched_property_terms = [
        term for term in PROPERTY_TERMS if term in text_lower
    ]

    matched_legal_terms = [
        term for term in LEGAL_TERMS if term in text_lower
    ]

    score = (
        len(matched_notice_terms) * 30
        + len(matched_property_terms) * 15
        + len(matched_legal_terms) * 10
    )

    score = min(score, 100)

    if not matched_notice_terms or not matched_property_terms:
        classification = "NOT_RELEVANT"
        confidence = "LOW"

    elif score >= 70:
        classification = "ESTATE_PROPERTY_NOTICE"
        confidence = "HIGH"

    elif score >= 45:
        classification = "ESTATE_PROPERTY_NOTICE"
        confidence = "MEDIUM"

    else:
        classification = "NOT_RELEVANT"
        confidence = "LOW"

    return {
        "is_notice": classification == "ESTATE_PROPERTY_NOTICE",
        "notice_type": classification,
        "confidence": confidence,
        "score": score,
        "matched_notice_terms": matched_notice_terms,
        "matched_property_terms": matched_property_terms,
        "matched_legal_terms": matched_legal_terms,
    }
