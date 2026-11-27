"""
Conservative dual-OCR party candidate validation.

Agreement between OCR sources does not verify identity,
ownership, legal entitlement, or financial responsibility.
"""

import re
import unicodedata

from copy import deepcopy
from collections import defaultdict, Counter
from difflib import SequenceMatcher


def safety_flags():

    return {
        "requires_review": True,
        "identity_merged": False,
        "verified": False,
        "ownership_verified": False,
        "legal_entitlement_verified": False,
        "approved_for_search": False,
        "eligible_for_alert": False,
    }


def normalize_party_name(name):

    name = unicodedata.normalize(
        "NFC",
        name or "",
    )

    name = name.replace("\u200c", "")
    name = name.replace("\u200d", "")

    name = re.sub(
        r"[.\s]+",
        " ",
        name,
    )

    return name.strip().casefold()


def get_entry_numbers(candidate):

    numbers = candidate.get(
        "court_entry_numbers"
    ) or []

    return tuple(sorted({

        str(number).strip()

        for number in numbers

        if number is not None
        and str(number).strip()

    }))


def candidate_key(candidate):

    return (

        normalize_party_name(
            candidate["name"]
        ),

        candidate["role"],

        candidate["language"],

        get_entry_numbers(candidate),

    )


def group_candidates(candidates):

    groups = defaultdict(list)

    for candidate in candidates:

        key = candidate_key(candidate)

        groups[key].append(
            deepcopy(candidate)
        )

    return groups


def build_comparison_groups(
    primary_candidates,
    secondary_candidates,
):

    secondary_available = (
        secondary_candidates is not None
    )

    primary = group_candidates(
        primary_candidates
    )

    secondary = group_candidates(
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

        comparisons.append({

            "normalized_name": key[0],

            "role": key[1],

            "language": key[2],

            "court_entry_numbers": list(
                key[3]
            ),

            "status": status,

            "primary_candidates": first,

            "secondary_candidates": second,

            "primary_occurrence_count": len(
                first
            ),

            "secondary_occurrence_count": len(
                second
            ),

            **safety_flags(),

        })

    return comparisons


def find_possible_name_variations(
    comparisons,
    similarity_threshold=0.80,
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

            if (
                first["language"]
                != second["language"]
            ):
                continue

            first_entries = first[
                "court_entry_numbers"
            ]

            second_entries = second[
                "court_entry_numbers"
            ]

            # Do not suggest spelling variations
            # across different explicit court entries.

            if (
                first_entries
                and second_entries
                and first_entries != second_entries
            ):
                continue

            first_name = first[
                "normalized_name"
            ]

            second_name = second[
                "normalized_name"
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

                "language": first["language"],

                "similarity": round(
                    similarity, 4
                ),

                "primary_entry_numbers": (
                    first_entries
                ),

                "secondary_entry_numbers": (
                    second_entries
                ),

                "status": "POSSIBLE_NAME_VARIATION",

                "primary_candidates": deepcopy(
                    first["primary_candidates"]
                ),

                "secondary_candidates": deepcopy(
                    second["secondary_candidates"]
                ),

                **safety_flags(),

            })

    return variations


def find_role_differences(comparisons):

    names = defaultdict(
        lambda: {
            "primary": set(),
            "secondary": set(),
        }
    )

    for item in comparisons:

        key = (

            item["normalized_name"],

            item["language"],

            tuple(item["court_entry_numbers"]),

        )

        if item["primary_candidates"]:

            names[key]["primary"].add(
                item["role"]
            )

        if item["secondary_candidates"]:

            names[key]["secondary"].add(
                item["role"]
            )

    differences = []

    for key, roles in names.items():

        if not roles["primary"]:
            continue

        if not roles["secondary"]:
            continue

        if roles["primary"] == roles["secondary"]:
            continue

        differences.append({

            "normalized_name": key[0],

            "language": key[1],

            "court_entry_numbers": list(
                key[2]
            ),

            "primary_roles": sorted(
                roles["primary"]
            ),

            "secondary_roles": sorted(
                roles["secondary"]
            ),

            "status": "ROLE_DIFFERENCE",

            **safety_flags(),

        })

    return differences


def find_entry_number_differences(
    comparisons,
):

    names = defaultdict(
        lambda: {
            "primary": set(),
            "secondary": set(),
        }
    )

    for item in comparisons:

        key = (

            item["normalized_name"],

            item["role"],

            item["language"],

        )

        entries = tuple(
            item["court_entry_numbers"]
        )

        if item["primary_candidates"]:

            names[key]["primary"].add(
                entries
            )

        if item["secondary_candidates"]:

            names[key]["secondary"].add(
                entries
            )

    differences = []

    for key, entries in names.items():

        first = entries["primary"]
        second = entries["secondary"]

        if not first or not second:
            continue

        if first == second:
            continue

        if not any(first | second):
            continue

        differences.append({

            "normalized_name": key[0],

            "role": key[1],

            "language": key[2],

            "primary_entry_groups": [

                list(group)

                for group in sorted(first)

            ],

            "secondary_entry_groups": [

                list(group)

                for group in sorted(second)

            ],

            "status": "ENTRY_NUMBER_DIFFERENCE",

            **safety_flags(),

        })

    return differences


def validate_party_candidates(
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

    comparisons = build_comparison_groups(

        primary_candidates,

        secondary_candidates,

    )

    variations = []
    role_differences = []
    entry_differences = []

    if secondary_candidates is not None:

        variations = find_possible_name_variations(

            comparisons,

            similarity_threshold,

        )

        role_differences = find_role_differences(
            comparisons
        )

        entry_differences = (
            find_entry_number_differences(
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

        "comparison_count": len(
            comparisons
        ),

        "status_counts": dict(Counter(

            item["status"]

            for item in comparisons

        )),

        "comparisons": comparisons,

        "possible_name_variations": variations,

        "role_differences": role_differences,

        "entry_number_differences": (
            entry_differences
        ),

        "possible_name_variation_count": len(
            variations
        ),

        "role_difference_count": len(
            role_differences
        ),

        "entry_number_difference_count": len(
            entry_differences
        ),

        "similarity_threshold": (
            similarity_threshold
        ),

        **safety_flags(),

    }
