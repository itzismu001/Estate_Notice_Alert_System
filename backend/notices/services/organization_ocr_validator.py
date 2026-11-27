"""
Conservative dual-OCR organization candidate validation.

Suggested-name agreement does not establish legal identity,
property ownership, mortgage validity or creditor rights.
"""

from collections import Counter, defaultdict
from copy import deepcopy
from difflib import SequenceMatcher

from notices.services.party_ocr_validator import (
    normalize_party_name,
    safety_flags,
)


def organization_safety_flags():

    return {
        **safety_flags(),
        "creditor_rights_verified": False,
        "mortgage_verified": False,
        "organization_identity_verified": False,
    }


def organization_key(candidate):

    name = normalize_party_name(
        candidate.get("suggested_name")
        or candidate.get("name")
    )

    role = candidate.get("role") or ""

    if not name:

        raise ValueError(
            "Organization candidate requires a name."
        )

    return name, role


def group_organizations(candidates):

    groups = defaultdict(list)

    for candidate in candidates:

        key = organization_key(candidate)

        groups[key].append(
            deepcopy(candidate)
        )

    return groups


def get_raw_names(candidates):

    return sorted({

        normalize_party_name(
            item.get("name")
        )

        for item in candidates

        if item.get("name")

    })


def build_organization_comparisons(
    primary_candidates,
    secondary_candidates,
):

    secondary_available = (
        secondary_candidates is not None
    )

    primary = group_organizations(
        primary_candidates
    )

    secondary = group_organizations(
        secondary_candidates or []
    )

    comparisons = []

    for key in sorted(
        primary.keys() | secondary.keys()
    ):

        first = primary.get(key, [])
        second = secondary.get(key, [])

        if not secondary_available:

            status = "SECONDARY_NOT_AVAILABLE"

        elif first and second:

            status = "CONSISTENT_UNVERIFIED"

        elif first:

            status = "PRIMARY_ONLY"

        else:

            status = "SECONDARY_ONLY"

        primary_names = get_raw_names(first)

        secondary_names = get_raw_names(second)

        raw_names_agree = None

        if first and second:

            raw_names_agree = (
                primary_names == secondary_names
            )

        comparisons.append({

            "normalized_suggested_name": key[0],

            "role": key[1],

            "entity_kind": "ORGANIZATION",

            "status": status,

            "primary_raw_names": primary_names,

            "secondary_raw_names": secondary_names,

            "raw_names_agree": raw_names_agree,

            "primary_candidates": first,

            "secondary_candidates": second,

            "primary_occurrence_count": len(first),

            "secondary_occurrence_count": len(second),

            **organization_safety_flags(),

        })

    return comparisons


def find_raw_name_differences(comparisons):

    differences = []

    for item in comparisons:

        if item["raw_names_agree"] is not False:

            continue

        differences.append({

            "normalized_suggested_name": item[
                "normalized_suggested_name"
            ],

            "role": item["role"],

            "primary_raw_names": deepcopy(
                item["primary_raw_names"]
            ),

            "secondary_raw_names": deepcopy(
                item["secondary_raw_names"]
            ),

            "primary_candidates": deepcopy(
                item["primary_candidates"]
            ),

            "secondary_candidates": deepcopy(
                item["secondary_candidates"]
            ),

            "status": "RAW_NAME_DIFFERENCE",

            **organization_safety_flags(),

        })

    return differences


def find_possible_organization_variations(
    comparisons,
    similarity_threshold,
):

    primary_only = [

        item for item in comparisons

        if item["status"] == "PRIMARY_ONLY"

    ]

    secondary_only = [

        item for item in comparisons

        if item["status"] == "SECONDARY_ONLY"

    ]

    variations = []

    for first in primary_only:

        for second in secondary_only:

            if first["role"] != second["role"]:

                continue

            first_name = first[
                "normalized_suggested_name"
            ]

            second_name = second[
                "normalized_suggested_name"
            ]

            if first_name == second_name:

                continue

            if min(
                len(first_name),
                len(second_name),
            ) < 5:

                continue

            similarity = SequenceMatcher(

                None,

                first_name,

                second_name,

            ).ratio()

            if similarity < similarity_threshold:

                continue

            variations.append({

                "primary_name": first_name,

                "secondary_name": second_name,

                "role": first["role"],

                "similarity": round(similarity, 4),

                "status": "POSSIBLE_NAME_VARIATION",

                "primary_candidates": deepcopy(
                    first["primary_candidates"]
                ),

                "secondary_candidates": deepcopy(
                    second["secondary_candidates"]
                ),

                **organization_safety_flags(),

            })

    return variations


def find_organization_role_differences(
    comparisons,
):

    names = defaultdict(
        lambda: {
            "primary": set(),
            "secondary": set(),
        }
    )

    for item in comparisons:

        name = item[
            "normalized_suggested_name"
        ]

        if item["primary_candidates"]:

            names[name]["primary"].add(
                item["role"]
            )

        if item["secondary_candidates"]:

            names[name]["secondary"].add(
                item["role"]
            )

    differences = []

    for name, roles in names.items():

        first = roles["primary"]
        second = roles["secondary"]

        if not first or not second:

            continue

        if first == second:

            continue

        differences.append({

            "normalized_suggested_name": name,

            "primary_roles": sorted(first),

            "secondary_roles": sorted(second),

            "status": "ROLE_DIFFERENCE",

            **organization_safety_flags(),

        })

    return differences


def find_organization_differences(
    comparisons,
):

    primary_names = {

        item["normalized_suggested_name"]

        for item in comparisons

        if item["primary_candidates"]

    }

    secondary_names = {

        item["normalized_suggested_name"]

        for item in comparisons

        if item["secondary_candidates"]

    }

    if primary_names == secondary_names:

        return []

    return [{

        "primary_names": sorted(
            primary_names
        ),

        "secondary_names": sorted(
            secondary_names
        ),

        "primary_only_names": sorted(
            primary_names - secondary_names
        ),

        "secondary_only_names": sorted(
            secondary_names - primary_names
        ),

        "common_names": sorted(
            primary_names & secondary_names
        ),

        "status": "ORGANIZATION_DIFFERENCE",

        **organization_safety_flags(),

    }]


def validate_organization_candidates(
    primary_candidates,
    secondary_candidates=None,
    similarity_threshold=0.80,
):

    if not 0 <= similarity_threshold <= 1:

        raise ValueError(
            "Similarity threshold must be "
            "between zero and one."
        )

    primary_candidates = (
        primary_candidates or []
    )

    comparisons = build_organization_comparisons(

        primary_candidates,

        secondary_candidates,

    )

    raw_differences = find_raw_name_differences(
        comparisons
    )

    variations = []
    role_differences = []
    organization_differences = []

    if secondary_candidates is not None:

        variations = (
            find_possible_organization_variations(
                comparisons,
                similarity_threshold,
            )
        )

        role_differences = (
            find_organization_role_differences(
                comparisons
            )
        )

        organization_differences = (
            find_organization_differences(
                comparisons
            )
        )

    return {

        "secondary_available": (
            secondary_candidates is not None
        ),

        "primary_candidate_count": len(
            primary_candidates
        ),

        "secondary_candidate_count": len(
            secondary_candidates or []
        ),

        "comparison_count": len(comparisons),

        "status_counts": dict(Counter(

            item["status"]

            for item in comparisons

        )),

        "comparisons": comparisons,

        "raw_name_differences": raw_differences,

        "raw_name_difference_count": len(
            raw_differences
        ),

        "possible_name_variations": variations,

        "possible_name_variation_count": len(
            variations
        ),

        "role_differences": role_differences,

        "role_difference_count": len(
            role_differences
        ),

        "organization_differences": (
            organization_differences
        ),

        "organization_difference_count": len(
            organization_differences
        ),

        "similarity_threshold": (
            similarity_threshold
        ),

        **organization_safety_flags(),

    }
