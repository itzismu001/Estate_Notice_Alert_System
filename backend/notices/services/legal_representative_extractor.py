"""
Extract candidate legal representative associations.

Numbered court subentries must match an explicitly
identified deceased parent entry.

All associations require manual review.
"""

import re
import unicodedata

from notices.services.party_name_extractor import (
    validate_person_name,
)


HONORIFIC = (
    r"(?i:Mr|Mrs|Ms|Sri|Shri|Smt|Dr)"
    r"(?:\.\s*|\s+)"
)

TOKEN = (
    r"(?:[A-Z](?:\.[A-Z])+\.?"
    r"|[A-Z][A-Za-z'-]*\.?)"
)

NAME = rf"{TOKEN}(?:[ \t]+{TOKEN}){{0,5}}"

PARENT_ENTRY = re.compile(
    r"^\s*(?P<number>\d{1,3})[.)]\s*"
    rf"(?:{HONORIFIC})?"
    rf"(?P<name>{NAME}?)"
    r"\s*,?\s*"
    r"(?i:since dead|deceased)"
    r"\s*,?\s*"
    r"(?i:represented by)"
    r"\s+(?:(?i:his|her|their)\s+)?"
    r"(?i:LR['’]?s|legal representatives?)\b"
)

SUBENTRY = re.compile(
    r"^\s*(?P<number>\d{1,3})"
    r"\s*\(\s*(?P<letter>[a-zA-Z])\s*\)"
    r"[.,:]?\s*"
    rf"(?:{HONORIFIC})?"
    rf"(?P<name>{NAME}?)"
    r"(?=\s*[,;]"
    r"|\s+(?i:W/o|S/o|D/o|aged)"
    r"|$)"
)

NEXT_ENTRY = re.compile(
    r"^\s*\d{1,3}[.)]\s*"
)

STOP_SECTION = re.compile(
    r"^\s*(?:WHEREAS|SCHEDULE"
    r"|SUMMONS TO|Given under)\b",
    re.IGNORECASE,
)

RELATIONSHIPS = {

    "WIFE": re.compile(
        r"\b(?:W\s*/\s*o|wife of)\b",
        re.IGNORECASE,
    ),

    "SON": re.compile(
        r"\b(?:S\s*/\s*o|son of)\b",
        re.IGNORECASE,
    ),

    "DAUGHTER": re.compile(
        r"\b(?:D\s*/\s*o|daughter of)\b",
        re.IGNORECASE,
    ),

}


def normalize_text(text):

    return (
        unicodedata.normalize("NFC", text or "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )


def clean_name(name):

    return re.sub(
        r"\s+", " ", name or ""
    ).strip(" ,:;")


def extract_relationship(evidence, deceased_name):

    # Require the deceased person's name after
    # the explicit relationship marker.
    for role, pattern in RELATIONSHIPS.items():

        match = pattern.search(evidence)

        if not match:
            continue

        following = evidence[match.end():]

        related_pattern = (
            r"^\s*(?:Late\s+)?"
            rf"(?:{HONORIFIC})?"
            + re.escape(deceased_name)
            + r"(?=\s|[,.;]|$)"
        )

        if re.search(
            related_pattern,
            following,
            re.IGNORECASE,
        ):
            return role

    return None


def extract_legal_representatives(raw_text):

    text = normalize_text(raw_text)

    lines = text.splitlines()

    associations = []

    for index, line in enumerate(lines):

        # Allow the representation statement
        # to continue onto the following line.
        window = line
        parent_end = index

        parent = PARENT_ENTRY.search(window)

        if not parent and index + 1 < len(lines):

            following = lines[index + 1]

            if not (
                NEXT_ENTRY.search(following)
                or SUBENTRY.search(following)
                or STOP_SECTION.search(following)
            ):

                window += " " + following

                parent = PARENT_ENTRY.search(
                    window
                )

                if parent:
                    parent_end = index + 1

        if not parent:
            continue

        parent_number = parent.group("number")

        deceased_name = clean_name(
            parent.group("name")
        )

        if not validate_person_name(
            deceased_name, "en"
        ):
            continue

        # Restrict the search to the immediate
        # numbered representation section.
        limit = min(
            len(lines),
            parent_end + 31,
        )

        for position in range(
            parent_end + 1,
            limit,
        ):

            entry = lines[position]

            if STOP_SECTION.search(entry):
                break

            if NEXT_ENTRY.search(entry):
                break

            representative = SUBENTRY.search(
                entry
            )

            if not representative:
                continue

            if (
                representative.group("number")
                != parent_number
            ):
                break

            name = clean_name(
                representative.group("name")
            )

            if not validate_person_name(
                name, "en"
            ):
                continue

            letter = representative.group(
                "letter"
            ).lower()

            evidence_lines = [entry]

            # Include a maximum of two
            # continuation lines.
            for following_index in range(
                position + 1,
                min(len(lines), position + 3),
            ):

                following = lines[
                    following_index
                ]

                if (
                    NEXT_ENTRY.search(following)
                    or SUBENTRY.search(following)
                    or STOP_SECTION.search(following)
                ):
                    break

                evidence_lines.append(following)

            evidence = "\n".join(
                evidence_lines
            )

            relationship = extract_relationship(
                evidence,
                deceased_name,
            )

            associations.append({

                "deceased_person": deceased_name,

                "deceased_entry_number": (
                    parent_number
                ),

                "representative_name": name,

                "representative_entry_number": (
                    f"{parent_number}({letter})"
                ),

                "role": "LEGAL_REPRESENTATIVE",

                "language": "en",

                "relationship": relationship,

                "association_method": (
                    "NUMBERED_COURT_SUBENTRY"
                ),

                "parent_source_text": window,

                "source_text": evidence,

                "parent_start_line": index + 1,

                "parent_end_line": parent_end + 1,

                "representative_start_line": (
                    position + 1
                ),

                "representative_end_line": (
                    position + len(evidence_lines)
                ),

                "identity_merged": False,

                "ownership_verified": False,

                "legal_entitlement_verified": False,

                "requires_review": True,

                "verified": False,

                "approved_for_search": False,

                "eligible_for_alert": False,

            })

    return {

        "associations": associations,

        "association_count": len(associations),

        "requires_review": True,

        "verified": False,

        "approved_for_search": False,

        "eligible_for_alert": False,

    }
