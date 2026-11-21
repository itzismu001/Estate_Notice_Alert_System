NOTICE_TERMS = [
    "public notice",
    "legal notice",
    "notice to the public",
]

PROPERTY_TERMS = [
    "land",
    "said land",
    "said property",
    "immovable property",
    "survey number",
    "survey no",
    "plot number",
    "plot no",
    "village",
    "property",
]

LEGAL_TERMS = [
    "claim",
    "objection",
    "ownership",
    "title",
    "sale deed",
    "sale transaction",
    "proposed sale",
    "transfer",
    "mortgage",
    "legal heirs",
    "encumbrance",
    "right, title",
]

ESTATE_CONTEXT_TERMS = [
    "owner",
    "absolute owner",
    "right, title and interest",
    "sale transaction",
    "proposed sale",
    "transfer",
    "conveyance",
    "property documents",
]

IRRELEVANT_TERMS = [
    "e-tender",
    "tender documents",
    "earnest money",
    "bid submission",
    "technical bid",
    "recruitment",
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

    matched_estate_terms = [
        term for term in ESTATE_CONTEXT_TERMS if term in text_lower
    ]

    matched_irrelevant_terms = [
        term for term in IRRELEVANT_TERMS if term in text_lower
    ]

    score = (
        len(matched_property_terms) * 15
        + len(matched_legal_terms) * 10
        + len(matched_estate_terms) * 20
    )

    if matched_irrelevant_terms and len(matched_estate_terms) < 2:
        classification = "NOT_RELEVANT"
        confidence = "LOW"

    elif len(matched_property_terms) >= 1 and len(matched_estate_terms) >= 1:
        classification = "ESTATE_PROPERTY_NOTICE"
        confidence = "HIGH" if score >= 70 else "MEDIUM"

    else:
        classification = "NOT_RELEVANT"
        confidence = "LOW"

    return {
        "is_notice": classification == "ESTATE_PROPERTY_NOTICE",
        "notice_type": classification,
        "confidence": confidence,
        "score": min(score, 100),
        "matched_notice_terms": matched_notice_terms,
        "matched_property_terms": matched_property_terms,
        "matched_legal_terms": matched_legal_terms,
        "matched_estate_terms": matched_estate_terms,
        "matched_irrelevant_terms": matched_irrelevant_terms,
    }
