import re
import unicodedata

from copy import deepcopy
from collections import defaultdict


def normalize_party_name(name):

    name = unicodedata.normalize(
        "NFC", name or ""
    )

    name = name.replace("\u200c", "")
    name = name.replace("\u200d", "")

    # Normalize periods and whitespace only.
    # Preserve meaningful spelling differences.

    name = name.replace(".", " ")

    name = re.sub(r"\s+", " ", name)

    return name.strip().casefold()


def extract_party_entry_numbers(candidate):

    evidence = candidate.get(
        "source_text", ""
    )

    method = candidate.get(
        "extraction_method", ""
    )

    numbers = set()

    if method == "COURT_NUMBERED_EXPLICIT_ROLE":

        match = re.match(
            r"\s*(\d{1,3})[.,)]",
            evidence
        )

        if match:
            numbers.add(match.group(1))

    if method == "COURT_EXPLICIT_DEFENDANT_LIST":

        match = re.search(
            r"(?i)defendants?\s*:\s*"
            r"(\d{1,3})[.,)]",
            evidence
        )

        if match:
            numbers.add(match.group(1))

    return numbers


def group_party_variants(candidates):

    buckets = defaultdict(list)

    for index, candidate in enumerate(candidates):

        name = candidate.get("name", "")

        role = candidate.get(
            "role", "UNKNOWN"
        )

        language = candidate.get(
            "language", "unknown"
        )

        normalized = normalize_party_name(name)

        if not normalized:
            continue

        key = (
            normalized,
            role,
            language
        )

        buckets[key].append(
            (index, candidate)
        )

    groups = []

    for key, items in buckets.items():

        normalized, role, language = key

        variants = list(dict.fromkeys(
            candidate["name"]
            for _, candidate in items
        ))

        entry_numbers = set()

        for _, candidate in items:

            entry_numbers.update(
                extract_party_entry_numbers(
                    candidate
                )
            )

        conflicting_entries = (
            len(entry_numbers) > 1
        )

        if conflicting_entries:

            status = "POSSIBLE_DISTINCT_PERSONS"

        elif len(items) > 1:

            status = "POSSIBLE_NAME_VARIANTS"

        else:

            status = "SINGLE_CANDIDATE"

        groups.append({

            "normalized_name": normalized,

            "display_name": variants[0],

            "role": role,

            "language": language,

            "name_variants": variants,

            "candidate_count": len(items),

            "candidate_indices": [
                index for index, _ in items
            ],

            "court_entry_numbers": sorted(
                entry_numbers
            ),

            "grouping_status": status,

            "original_candidates": [
                deepcopy(candidate)
                for _, candidate in items
            ],

            "identity_conflict": conflicting_entries,

            "identity_merged": False,

            "verified": False,

            "requires_review": True,

            "approved_for_search": False,

            "eligible_for_alert": False
        })

    return {

        "original_candidate_count": len(candidates),

        "group_count": len(groups),

        "possible_variant_groups": sum(

            group["grouping_status"]
            == "POSSIBLE_NAME_VARIANTS"

            for group in groups
        ),

        "possible_distinct_person_groups": sum(

            group["identity_conflict"]

            for group in groups
        ),

        "party_groups": groups,

        "identity_merged": False,

        "verified": False,

        "requires_review": True,

        "approved_for_search": False,

        "eligible_for_alert": False
    }
