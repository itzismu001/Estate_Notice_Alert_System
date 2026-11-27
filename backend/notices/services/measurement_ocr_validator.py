"""Compare measurement occurrences without verifying property identity."""

from collections import defaultdict, Counter
from copy import deepcopy

from notices.services.agricultural_area_extractor import (
    safety_flags,
)


def measurement_key(item):

    kind = item.get("measurement_type")

    if kind == "STANDARD_AREA":
        return (
            kind,
            item.get("area_role"),
            item.get("area_value"),
            item.get("area_unit"),
        )

    if kind == "AGRICULTURAL_AREA":
        return (
            kind,
            item.get("normalized_total_guntas"),
        )

    if kind == "LINEAR_DIMENSION":
        return (
            kind,
            item.get("dimension_context_role"),
            item.get("direction"),
            item.get("dimension_value"),
            item.get("dimension_unit"),
        )

    if kind == "DIMENSION_PAIR":

        first = item.get("first_dimension", {})
        second = item.get("second_dimension", {})

        return (
            kind,
            first.get("dimension_value"),
            first.get("dimension_unit"),
            second.get("dimension_value"),
            second.get("dimension_unit"),
        )

    # Ambiguous expressions must not be treated
    # as verified numeric measurements.

    return (
        kind,
        item.get("reason"),
        item.get("raw_measurement"),
    )


def measurement_safety():

    return {
        **safety_flags(),
        "property_association_verified": False,
        "measurement_verified": False,
        "eligible_for_area_calculation": False,
        "calculated_area": None,
    }


def validate_measurements(
    primary_candidates,
    secondary_candidates=None,
):

    primary = defaultdict(list)
    secondary = defaultdict(list)

    secondary_available = secondary_candidates is not None

    for item in primary_candidates or []:
        primary[measurement_key(item)].append(item)

    for item in secondary_candidates or []:
        secondary[measurement_key(item)].append(item)

    groups = []
    counts = Counter()

    keys = list(dict.fromkeys(
        list(primary) + list(secondary)
    ))

    for key in keys:

        first = primary.get(key, [])
        second = secondary.get(key, [])

        if not secondary_available:
            status = "SECONDARY_NOT_AVAILABLE"

        elif first and second:

            if len(first) != len(second):
                status = "OCCURRENCE_COUNT_MISMATCH"

            elif len(first) > 1:
                status = "MULTIPLE_OCCURRENCES_UNRESOLVED"

            else:
                status = "CONSISTENT_UNVERIFIED"

        elif first:
            status = "PRIMARY_ONLY"

        else:
            status = "SECONDARY_ONLY"

        counts[status] += 1

        groups.append({
            "comparison_key": list(key),
            "status": status,
            "primary_candidates": deepcopy(first),
            "secondary_candidates": deepcopy(second),
            "primary_count": len(first),
            "secondary_count": len(second),
            "selected_measurement": None,
            "property_identity_matched": False,
            **measurement_safety(),
        })

    # Different values sharing a direction or area type
    # are potential conflicts, not proven conflicts.

    possible_conflicts = []

    if secondary_available:

        for first in groups:

            if first["status"] != "PRIMARY_ONLY":
                continue

            a = first["primary_candidates"][0]

            for second in groups:

                if second["status"] != "SECONDARY_ONLY":
                    continue

                b = second["secondary_candidates"][0]

                if a.get("measurement_type") != b.get(
                    "measurement_type"
                ):
                    continue

                kind = a.get("measurement_type")

                if kind == "LINEAR_DIMENSION":

                    same_context = (
                        a.get("direction") is not None
                        and a.get("direction") == b.get("direction")
                        and a.get("dimension_unit")
                        == b.get("dimension_unit")
                        and a.get("dimension_context_role")
                        == b.get("dimension_context_role")
                    )

                elif kind == "STANDARD_AREA":

                    same_context = (
                        a.get("area_unit") == b.get("area_unit")
                    )

                elif kind == "AGRICULTURAL_AREA":
                    same_context = True

                else:
                    same_context = False

                if same_context:

                    possible_conflicts.append({
                        "status": "POSSIBLE_VALUE_CONFLICT",
                        "primary_candidate": deepcopy(a),
                        "secondary_candidate": deepcopy(b),
                        "selected_measurement": None,
                        "property_identity_matched": False,
                        **measurement_safety(),
                    })

    return {
        "comparison_groups": groups,
        "comparison_count": len(groups),
        "status_counts": dict(counts),
        "possible_conflicts": possible_conflicts,
        "possible_conflict_count": len(possible_conflicts),
        "secondary_available": secondary_available,
        "selected_measurement": None,
        **measurement_safety(),
    }
