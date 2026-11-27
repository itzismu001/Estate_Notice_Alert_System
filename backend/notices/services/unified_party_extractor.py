"""
Unified multilingual party extraction service.

Coordinates existing extraction modules without
merging identities or establishing legal ownership.
"""

from copy import deepcopy
from collections import Counter

from notices.services.party_name_extractor import (
    extract_party_candidates,
)

from notices.services.bank_party_extractor import (
    extract_bank_party_candidates,
)

from notices.services.inheritance_party_extractor import (
    extract_inheritance_parties,
)

from notices.services.hybrid_legal_representative_extractor import (
    extract_hybrid_legal_representatives,
)

from notices.services.party_ocr_validator import (
    normalize_party_name,
    validate_party_candidates,
    safety_flags,
)

from notices.services.organization_ocr_validator import (
    validate_organization_candidates,
)

from notices.services.legal_relationship_ocr_validator import (
    validate_legal_relationships,
)


def wrap_party_candidate(candidate, module):

    return {

        "name": candidate["name"],

        "normalized_name": normalize_party_name(
            candidate["name"]
        ),

        "role": candidate["role"],

        "language": candidate["language"],

        "module": module,

        "court_entry_numbers": deepcopy(
            candidate.get("court_entry_numbers") or []
        ),

        "original_candidate": deepcopy(candidate),

        **safety_flags(),

    }


def wrap_legal_representative(association):

    return {

        "name": association["representative_name"],

        "normalized_name": normalize_party_name(
            association["representative_name"]
        ),

        "role": "LEGAL_REPRESENTATIVE",

        "language": association["language"],

        "module": "LEGAL_REPRESENTATIVE",

        "court_entry_numbers": [

            association["representative_entry_number"]

        ],

        "original_candidate": deepcopy(
            association
        ),

        **safety_flags(),

    }


def extract_source_parties(
    raw_text,
    notice_category="",
):

    raw_text = raw_text or ""

    notice_category = notice_category or ""

    general = extract_party_candidates(
        raw_text
    )

    inheritance = extract_inheritance_parties(
        raw_text
    )

    bank = extract_bank_party_candidates(

        raw_text,

        notice_category,

    )

    representatives = (
        extract_hybrid_legal_representatives(
            raw_text
        )
    )

    module_results = {

        "GENERAL": general["party_candidates"],

        "INHERITANCE": inheritance[
            "party_candidates"
        ],

        "BANK": bank["party_candidates"],

    }

    candidates = []

    module_counts = Counter()

    for module, items in module_results.items():

        module_counts[module] = len(items)

        for item in items:

            candidates.append(
                wrap_party_candidate(
                    item,
                    module,
                )
            )

    associations = representatives[
        "associations"
    ]

    module_counts["LEGAL_REPRESENTATIVE"] = len(
        associations
    )

    for item in associations:

        candidates.append(
            wrap_legal_representative(
                item
            )
        )

    organizations = deepcopy(
        bank["organization_candidates"]
    )

    return {

        "notice_category": notice_category,

        "party_candidates": candidates,

        "candidate_count": len(candidates),

        "organization_candidates": organizations,

        "organization_count": len(organizations),

        "legal_representative_associations": (
            deepcopy(associations)
        ),

        "legal_representative_count": len(
            associations
        ),

        "module_counts": dict(module_counts),

        "raw_text": raw_text,

        **safety_flags(),

    }


def extract_unified_parties(
    primary_text,
    secondary_text=None,
    notice_category="",
    similarity_threshold=0.80,
):

    primary = extract_source_parties(

        primary_text,

        notice_category,

    )

    secondary = None

    if secondary_text and secondary_text.strip():

        secondary = extract_source_parties(

            secondary_text,

            notice_category,

        )

    validation = validate_party_candidates(

        primary["party_candidates"],

        secondary["party_candidates"]
        if secondary is not None
        else None,

        similarity_threshold=similarity_threshold,

    )

    organization_validation = validate_organization_candidates(

        primary["organization_candidates"],

        secondary["organization_candidates"]
        if secondary is not None
        else None,

        similarity_threshold=similarity_threshold,

    )

    legal_relationship_validation = validate_legal_relationships(

        primary["legal_representative_associations"],

        secondary["legal_representative_associations"]
        if secondary is not None
        else None,

    )

    module_counts = Counter(
        primary["module_counts"]
    )

    if secondary is not None:

        module_counts.update(
            secondary["module_counts"]
        )

    primary_count = primary[
        "candidate_count"
    ]

    secondary_count = (

        secondary["candidate_count"]

        if secondary is not None

        else 0

    )

    return {

        "notice_category": notice_category or "",

        "primary": primary,

        "secondary": secondary,

        "secondary_available": (
            secondary is not None
        ),

        "ocr_texts_identical": (

            primary_text == secondary_text

            if secondary is not None

            else None

        ),

        "primary_candidate_count": primary_count,

        "secondary_candidate_count": secondary_count,

        "total_candidate_occurrences": (
            primary_count + secondary_count
        ),

        "comparison_count": validation[
            "comparison_count"
        ],

        "status_counts": validation[
            "status_counts"
        ],

        "party_validation": validation,

        "module_counts": dict(module_counts),

        "organization_validation": organization_validation,

        "legal_relationship_validation": (
            legal_relationship_validation
        ),

        "organization_validation_pending": False,

        "legal_relationship_validation_pending": False,

        **safety_flags(),

    }
