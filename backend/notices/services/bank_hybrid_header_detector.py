"""
Combine legacy and multiline financial table headings.

Preserve existing coverage while rejecting narrative matches.
Heading candidates are not verified table geometry.
"""

import re

from notices.services.bank_table_header_detector import (
    detect_financial_table_headers,
    normalize_header_text,
)

from notices.services.bank_table_party_extractor import (
    TABLE_HEADER,
)


PERSON_START = re.compile(
    r"^\s*(?:(?:\(\d+\)|\d+[.,)])\s*)?"
    r"(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ"
    r"|Mr|Mrs|Ms|Sri)"
    r"[.:\s]+",
    re.IGNORECASE,
)

NARRATIVE_PATTERN = re.compile(
    r"ಆದಾಗ್ಯೂ|ಕೆಳಕಂಡಂತೆ ತಿಳಿಸಲಾದ"
    r"|ನೀವು|ಪಡೆದಿರುತ್ತೀರಿ"
    r"|hereby|whereas|undersigned",
    re.IGNORECASE,
)


def detect_hybrid_financial_headers(raw_text):

    text = normalize_header_text(raw_text)
    lines = text.splitlines()
    candidates = []

    # Preserve legacy heading detection.
    for index, line in enumerate(lines, 1):

        if TABLE_HEADER.search(line):

            candidates.append({
                "start_line": index,
                "end_line": index,
                "heading_types": [
                    "LEGACY_FINANCIAL_HEADER"
                ],
                "detection_methods": ["LEGACY"],
            })

    # Add improved multiline headings.
    for item in detect_financial_table_headers(text):

        start = item["start_line"]
        end = item["end_line"]

        # Reject narrative matches without a name column.
        if (
            NARRATIVE_PATTERN.search(
                item["source_text"]
            )
            and not item["matched_features"][
                "name_column"
            ]
        ):
            continue

        # Do not consume a person's row as a heading.
        for line_number in range(start, end + 1):

            if PERSON_START.search(
                lines[line_number - 1]
            ):

                end = line_number - 1
                break

        if end < start:
            continue

        candidates.append({
            "start_line": start,
            "end_line": end,
            "heading_types": [
                item["heading_type"]
            ],
            "detection_methods": ["MULTILINE"],
        })

    candidates.sort(
        key=lambda item: (
            item["start_line"],
            item["end_line"],
        )
    )

    merged = []

    for item in candidates:

        if (
            merged
            and item["start_line"]
            <= merged[-1]["end_line"] + 1
        ):

            previous = merged[-1]

            previous["end_line"] = max(
                previous["end_line"],
                item["end_line"],
            )

            previous["heading_types"] = sorted(
                set(
                    previous["heading_types"]
                    + item["heading_types"]
                )
            )

            previous["detection_methods"] = sorted(
                set(
                    previous["detection_methods"]
                    + item["detection_methods"]
                )
            )

        else:

            merged.append(dict(item))

    for item in merged:

        item["source_text"] = "\n".join(
            lines[
                item["start_line"] - 1:
                item["end_line"]
            ]
        )

        item["first_candidate_line"] = (
            item["end_line"] + 1
        )

        item["requires_review"] = True
        item["verified"] = False
        item["approved_for_search"] = False
        item["eligible_for_alert"] = False

    return merged
