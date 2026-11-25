
import re


NOTICE_TERMS = [
    "public notice",
    "legal notice",
    "notice to the public",
    "notice is hereby given",
    "notice hereby given",
    "general public is hereby informed",
    "notice to general public",
    "notice to the general public",
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
    "site number",
    "site no",
    "village",
    "property",
    "hissa number",
    "hissa no",
    "khata number",
    "khata no",
    "property number",
    "property no",
    "schedule property",
    "scheduled property",
    "municipal number",
    "flat number",
    "flat no",
    "agricultural land",
]


PROPERTY_IDENTIFIER_TERMS = [
    "survey number",
    "survey no",
    "sy no",
    "plot number",
    "plot no",
    "site number",
    "site no",
    "hissa number",
    "hissa no",
    "khata number",
    "khata no",
    "subdivision number",
    "sub division number",
    "property number",
    "property no",
    "municipal number",
    "flat number",
    "flat no",
    "pid number",
    "pid no",
    "immovable property",
    "sale deed",
    "property documents",
    "title deed",
]


STRONG_PROPERTY_TERMS = [
    "said property",
    "said land",
    "immovable property",
    "schedule property",
    "scheduled property",
    "agricultural land",
    "property documents",
    "title deed",
    "sale deed",
    "property ownership",
    "property dispute",
    "property transaction",
    "ownership of property",
    "ownership of land",
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
    "right title",
    "inheritance",
    "partition deed",
    "gift deed",
    "release deed",
    "registered sale deed",
    "title deed",
    "property dispute",
    "litigation",
]


ESTATE_CONTEXT_TERMS = [
    "owner",
    "absolute owner",
    "right title and interest",
    "sale transaction",
    "proposed sale",
    "transfer",
    "conveyance",
    "property documents",
    "legal heirs",
    "purchaser",
    "vendor",
    "title deed",
    "ownership of property",
    "ownership of land",
]


STRONG_LEGAL_TERMS = [
    "absolute owner",
    "ownership",
    "sale deed",
    "registered sale deed",
    "sale transaction",
    "proposed sale",
    "legal heirs",
    "mortgage",
    "encumbrance",
    "right title and interest",
    "title deed",
    "partition deed",
    "gift deed",
    "release deed",
    "inheritance",
    "property dispute",
    "conveyance",
]


NOTICE_CONTEXT_TERMS = [
    "any person",
    "any persons",
    "any objections",
    "raise objections",
    "claims or objections",
    "within 15 days",
    "within 14 days",
    "hereby informed",
    "hereby notified",
    "lost property documents",
    "claim or objection",
    "submit objections",
    "persons having any claim",
    "any right title or interest",
]


IRRELEVANT_TERMS = [
    "e tender",
    "tender documents",
    "earnest money",
    "bid submission",
    "technical bid",
    "recruitment",
    "job vacancies",
    "applications are invited",
    "environmental clearance",
    "environmental public hearing",
    "pollution control board",
    "environmental impact assessment",
    "eia notification",
    "industrial project",
    "production capacity",
    "building bye laws",
    "building by laws",
    "change of name",
]


def normalize_text(text):

    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def match_terms(text, terms):

    matches = []
    occupied = []

    # Match longer phrases first.
    sorted_terms = sorted(
        terms,
        key=len,
        reverse=True
    )

    for term in sorted_terms:

        pattern = (
            r"\b"
            + re.escape(normalize_text(term))
            + r"s?\b"
        )

        for match in re.finditer(pattern, text):

            start, end = match.span()

            overlaps = any(
                start < existing_end
                and end > existing_start
                for existing_start, existing_end
                in occupied
            )

            if not overlaps:

                matches.append(term)

                occupied.append(
                    (start, end)
                )

                break

    return matches


def detect_notice(text):

    clean_text = normalize_text(text)

    # ----------------------------------------
    # STEP 1: Extract keyword evidence
    # ----------------------------------------

    matched_notice_terms = match_terms(
        clean_text,
        NOTICE_TERMS
    )

    matched_property_terms = match_terms(
        clean_text,
        PROPERTY_TERMS
    )

    matched_identifier_terms = match_terms(
        clean_text,
        PROPERTY_IDENTIFIER_TERMS
    )

    matched_strong_property_terms = match_terms(
        clean_text,
        STRONG_PROPERTY_TERMS
    )

    matched_legal_terms = match_terms(
        clean_text,
        LEGAL_TERMS
    )

    matched_estate_terms = match_terms(
        clean_text,
        ESTATE_CONTEXT_TERMS
    )

    matched_strong_legal_terms = match_terms(
        clean_text,
        STRONG_LEGAL_TERMS
    )

    matched_context_terms = match_terms(
        clean_text,
        NOTICE_CONTEXT_TERMS
    )

    matched_irrelevant_terms = match_terms(
        clean_text,
        IRRELEVANT_TERMS
    )

    # ----------------------------------------
    # STEP 2: Calculate detection score
    # ----------------------------------------

    score = (
        min(len(matched_notice_terms), 1) * 25
        + min(len(matched_property_terms), 3) * 10
        + min(len(matched_identifier_terms), 2) * 15
        + min(len(matched_legal_terms), 3) * 5
        + min(len(matched_estate_terms), 2) * 5
        + min(len(matched_context_terms), 2) * 10
    )

    score = min(score, 100)

    # ----------------------------------------
    # STEP 3: Evaluate evidence
    # ----------------------------------------

    has_notice_heading = bool(
        matched_notice_terms
    )

    has_property_identifier = bool(
        matched_identifier_terms
    )

    has_strong_property_context = bool(
        matched_strong_property_terms
    )

    has_strong_legal_context = bool(
        matched_strong_legal_terms
    )

    has_legal_context = bool(
        matched_legal_terms
        or matched_estate_terms
    )

    has_notice_context = bool(
        matched_context_terms
    )

    has_irrelevant_context = bool(
        matched_irrelevant_terms
    )

    is_notice = False

    # ----------------------------------------
    # STEP 4: Classification rules
    # ----------------------------------------

    # Reject unrelated notices unless substantial
    # property-specific and legal evidence exists.

    if has_irrelevant_context and not (
        has_notice_heading
        and has_property_identifier
        and has_strong_legal_context
        and has_notice_context
    ):

        is_notice = False

    # CASE 1:
    # Explicit notice with property identifiers.

    elif (
        has_notice_heading
        and has_property_identifier
    ):

        is_notice = True

    # CASE 2:
    # Property notice without numeric identifiers,
    # but with strong property and legal evidence.

    elif (
        has_notice_heading
        and has_strong_property_context
        and has_strong_legal_context
    ):

        is_notice = True

    # CASE 3:
    # Notice heading missing due to OCR errors.

    elif (
        has_property_identifier
        and has_legal_context
        and has_notice_context
    ):

        is_notice = True

    # CASE 4:
    # Strong property and legal context,
    # supported by public notice language.

    elif (
        has_strong_property_context
        and has_strong_legal_context
        and has_notice_context
    ):

        is_notice = True

    # ----------------------------------------
    # STEP 5: Final classification
    # ----------------------------------------

    if is_notice:

        classification = "ESTATE_PROPERTY_NOTICE"

        confidence = (
            "HIGH"
            if score >= 70
            else "MEDIUM"
        )

    else:

        classification = "NOT_RELEVANT"
        confidence = "LOW"

    # ----------------------------------------
    # STEP 6: Return compatible output
    # ----------------------------------------

    return {
        "is_notice": is_notice,
        "notice_type": classification,
        "confidence": confidence,
        "score": score,
        "matched_notice_terms": matched_notice_terms,
        "matched_property_terms": matched_property_terms,
        "matched_legal_terms": matched_legal_terms,
        "matched_estate_terms": matched_estate_terms,
        "matched_irrelevant_terms": matched_irrelevant_terms,
        "matched_identifier_terms": matched_identifier_terms,
        "matched_context_terms": matched_context_terms,
        "matched_strong_property_terms": matched_strong_property_terms,
        "matched_strong_legal_terms": matched_strong_legal_terms,
    }

