"""
Compare legal representative associations across OCR sources.

Agreement does not establish identity, ownership,
family relationship or legal entitlement.
"""

from collections import Counter
from copy import deepcopy
from unicodedata import normalize


def relationship_safety_flags():

    return {

        "requires_review": True,

        "verified": False,

        "identity_merged": False,

        "relationship_verified": False,

        "ownership_verified": False,

        "legal_entitlement_verified": False,

        "approved_for_search": False,

        "eligible_for_alert": False,

    }


def normalize_name(value):

    text = normalize(
        "NFC",
        str(value or ""),
    )

    for character in (
        "\u200b",
        "\u200c",
        "\u200d",
        "\ufeff",
    ):

        text = text.replace(character, "")

    return " ".join(
        text.casefold().split()
    )


def normalize_entry(value):

    return "".join(
        str(value or "").casefold().split()
    )


def association_key(item):

    return (

        normalize_name(
            item.get("deceased_person")
        ),

        normalize_entry(
            item.get("deceased_entry_number")
        ),

        normalize_name(
            item.get("representative_name")
        ),

        normalize_entry(
            item.get("representative_entry_number")
        ),

    )


def group_associations(items):

    groups = {}

    for item in items:

        key = association_key(item)

        if not key[0] or not key[2]:

            raise ValueError(
                "Association requires deceased "
                "and representative names."
            )

        groups.setdefault(
            key,
            [],
        ).append(
            deepcopy(item)
        )

    return groups


def relationship_values(items):

    values = set()

    for item in items:

        relationship = item.get(
            "relationship"
        )

        if relationship:

            value = str(
                relationship
            ).strip().upper()

            if value not in (
                "",
                "UNKNOWN",
                "UNSPECIFIED",
            ):

                values.add(value)

        for relationship in (
            item.get("relationship_candidates") or []
        ):

            value = str(
                relationship or ""
            ).strip().upper()

            if value not in (
                "",
                "UNKNOWN",
                "UNSPECIFIED",
            ):

                values.add(value)

    return sorted(values)


def respondent_numbers(items):

    return sorted({

        normalize_entry(
            item.get("respondent_number")
        )

        for item in items

        if item.get("respondent_number")
        is not None

        and normalize_entry(
            item.get("respondent_number")
        )

    })


def has_uncertain_relationship(items):

    return any(

        item.get("relationship_uncertain") is True

        or not item.get("relationship")

        for item in items

    )


def build_comparisons(
    primary_associations,
    secondary_associations=None,
):

    primary_groups = group_associations(
        primary_associations
    )

    secondary_groups = group_associations(
        secondary_associations or []
    )

    keys = sorted(

        set(primary_groups)
        | set(secondary_groups)

    )

    comparisons = []

    for key in keys:

        primary = primary_groups.get(
            key,
            [],
        )

        secondary = secondary_groups.get(
            key,
            [],
        )

        primary_values = relationship_values(
            primary
        )

        secondary_values = relationship_values(
            secondary
        )

        primary_numbers = respondent_numbers(
            primary
        )

        secondary_numbers = respondent_numbers(
            secondary
        )

        combined_values = sorted(

            set(primary_values)
            | set(secondary_values)

        )

        relationship_conflict = (

            len(combined_values) > 1

            or any(

                item.get(
                    "relationship_conflict"
                ) is True

                for item in primary + secondary

            )

        )

        respondent_conflict = (

            len(primary_numbers) > 1

            or len(secondary_numbers) > 1

            or bool(

                primary_numbers

                and secondary_numbers

                and primary_numbers
                != secondary_numbers

            )

        )

        identity_conflict = (

            respondent_conflict

            or any(

                item.get(
                    "identity_conflict"
                ) is True

                for item in primary + secondary

            )

        )

        relationship_incomplete = (

            not primary_values

            or not secondary_values

            or has_uncertain_relationship(
                primary + secondary
            )

        )

        if identity_conflict:

            status = "IDENTITY_CONFLICT"

        elif relationship_conflict:

            status = "RELATIONSHIP_CONFLICT"

        elif secondary_associations is None:

            status = "SECONDARY_NOT_AVAILABLE"

        elif primary and not secondary:

            status = "PRIMARY_ONLY"

        elif secondary and not primary:

            status = "SECONDARY_ONLY"

        elif relationship_incomplete:

            status = "RELATIONSHIP_INCOMPLETE"

        else:

            status = "CONSISTENT_UNVERIFIED"

        comparisons.append({

            "deceased_person_normalized": key[0],

            "deceased_entry_number": key[1],

            "representative_name_normalized": key[2],

            "representative_entry_number": key[3],

            "status": status,

            "primary_relationships": primary_values,

            "secondary_relationships": secondary_values,

            "relationship_candidates": combined_values,

            "selected_relationship": None,

            "primary_respondent_numbers": primary_numbers,

            "secondary_respondent_numbers": secondary_numbers,

            "respondent_number_conflict": respondent_conflict,

            "identity_conflict": identity_conflict,

            "relationship_conflict": relationship_conflict,

            "relationship_incomplete": relationship_incomplete,

            "primary_associations": primary,

            "secondary_associations": secondary,

            "primary_occurrence_count": len(primary),

            "secondary_occurrence_count": len(secondary),

            **relationship_safety_flags(),

        })

    return comparisons


def find_court_entry_conflicts(comparisons):

    groups = {}

    for item in comparisons:

        parent_entry = item[
            "deceased_entry_number"
        ]

        representative_entry = item[
            "representative_entry_number"
        ]

        if not parent_entry or not representative_entry:

            continue

        key = (

            parent_entry,

            representative_entry,

        )

        groups.setdefault(
            key,
            [],
        ).append(item)

    conflicts = []

    for key, items in groups.items():

        names = {

            (

                item["deceased_person_normalized"],

                item["representative_name_normalized"],

            )

            for item in items

        }

        if len(names) <= 1:

            continue

        for item in items:

            item["identity_conflict"] = True

            item["status"] = "IDENTITY_CONFLICT"

        conflicts.append({

            "deceased_entry_number": key[0],

            "representative_entry_number": key[1],

            "name_pairs": [

                list(pair)

                for pair in sorted(names)

            ],

            "status": "IDENTITY_CONFLICT",

            **relationship_safety_flags(),

        })

    return conflicts


def validate_legal_relationships(
    primary_associations,
    secondary_associations=None,
):

    comparisons = build_comparisons(

        primary_associations,

        secondary_associations,

    )

    entry_conflicts = find_court_entry_conflicts(
        comparisons
    )

    status_counts = Counter(

        item["status"]

        for item in comparisons

    )

    return {

        "secondary_available": (
            secondary_associations is not None
        ),

        "primary_association_count": len(
            primary_associations
        ),

        "secondary_association_count": len(
            secondary_associations or []
        ),

        "comparison_count": len(comparisons),

        "status_counts": dict(status_counts),

        "comparisons": comparisons,

        "court_entry_conflicts": entry_conflicts,

        "court_entry_conflict_count": len(
            entry_conflicts
        ),

        "identity_conflict_count": sum(

            item["identity_conflict"]

            for item in comparisons

        ),

        "relationship_conflict_count": sum(

            item["relationship_conflict"]

            for item in comparisons

        ),

        "relationship_incomplete_count": sum(

            item["relationship_incomplete"]

            for item in comparisons

        ),

        **relationship_safety_flags(),

    }
