"""
Combine standard and OCR-specific legal representative
extraction without merging unverified person identities.
"""

import re
import unicodedata

from copy import deepcopy
from collections import defaultdict

from notices.services.legal_representative_extractor import (
    extract_legal_representatives,
)

from notices.services.ocr_legal_representative_extractor import (
    extract_ocr_legal_representatives,
)


def normalize_name(name):

    return re.sub(
        r"\s+",
        " ",
        unicodedata.normalize(
            "NFC", name or ""
        ),
    ).strip().casefold()


def association_key(item):

    return (
        normalize_name(item["deceased_person"]),
        item["deceased_entry_number"],
        normalize_name(item["representative_name"]),
        item["representative_entry_number"],
        item.get("respondent_number"),
        item.get("parent_start_line"),
        item.get("representative_start_line"),
    )


def build_evidence(item):

    return {

        "association_method": item[
            "association_method"
        ],

        "parent_source_text": item[
            "parent_source_text"
        ],

        "source_text": item["source_text"],

        "raw_defendant_label": item.get(
            "raw_defendant_label"
        ),

        "parent_start_line": item.get(
            "parent_start_line"
        ),

        "parent_end_line": item.get(
            "parent_end_line"
        ),

        "representative_start_line": item.get(
            "representative_start_line"
        ),

        "representative_end_line": item.get(
            "representative_end_line"
        ),

        "relationship": item.get("relationship"),

    }


def consolidate_associations(candidates):

    groups = {}

    for candidate in candidates:

        item = deepcopy(candidate)

        key = association_key(item)

        evidence = build_evidence(item)

        if key not in groups:

            item["evidence"] = []

            item["association_methods"] = []

            item["relationship_candidates"] = []

            groups[key] = item

        group = groups[key]

        if evidence not in group["evidence"]:

            group["evidence"].append(evidence)

        method = item["association_method"]

        if method not in group["association_methods"]:

            group["association_methods"].append(
                method
            )

        relationship = item.get("relationship")

        if (
            relationship
            and relationship not in
            group["relationship_candidates"]
        ):

            group["relationship_candidates"].append(
                relationship
            )

    associations = list(groups.values())

    for item in associations:

        relationships = item[
            "relationship_candidates"
        ]

        item["relationship_conflict"] = (
            len(relationships) > 1
        )

        item["relationship"] = (
            relationships[0]
            if len(relationships) == 1
            else None
        )

        item["relationship_uncertain"] = (
            item["relationship"] is None
        )

        item["identity_conflict"] = False

        item["identity_merged"] = False

        item["requires_review"] = True

        item["verified"] = False

        item["ownership_verified"] = False

        item["legal_entitlement_verified"] = False

        item["approved_for_search"] = False

        item["eligible_for_alert"] = False

    # Detect different names associated with
    # the same numbered representative entry.

    entry_groups = defaultdict(list)

    for item in associations:

        entry_key = (

            item["deceased_entry_number"],

            item["representative_entry_number"],

        )

        entry_groups[entry_key].append(item)

    for items in entry_groups.values():

        identities = {

            (
                normalize_name(
                    item["deceased_person"]
                ),

                normalize_name(
                    item["representative_name"]
                ),
            )

            for item in items

        }

        if len(identities) > 1:

            for item in items:

                item["identity_conflict"] = True

    return associations


def extract_hybrid_legal_representatives(raw_text):

    standard = extract_legal_representatives(
        raw_text
    )

    ocr_specific = (
        extract_ocr_legal_representatives(
            raw_text
        )
    )

    candidates = (

        standard["associations"]

        + ocr_specific["associations"]

    )

    associations = consolidate_associations(
        candidates
    )

    return {

        "associations": associations,

        "association_count": len(associations),

        "standard_count": standard[
            "association_count"
        ],

        "ocr_specific_count": ocr_specific[
            "association_count"
        ],

        "raw_association_count": len(candidates),

        "identity_conflict_count": sum(

            item["identity_conflict"]

            for item in associations

        ),

        "relationship_conflict_count": sum(

            item["relationship_conflict"]

            for item in associations

        ),

        "requires_review": True,

        "verified": False,

        "approved_for_search": False,

        "eligible_for_alert": False,

    }
