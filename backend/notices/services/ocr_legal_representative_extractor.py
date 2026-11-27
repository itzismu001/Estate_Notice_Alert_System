"""
Legal representative association for court notices
with separate defendant and respondent numbering.

OCR evidence is preserved without verifying
identity, ownership or legal entitlement.
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

PARENT_PATTERN = re.compile(
    rf"^\s*(?:{HONORIFIC})?"
    rf"(?P<name>{NAME}?)"
    r"\s*,?\s*"
    r"(?i:since dead|deceased)"
    r"\s*,?\s*"
    r"(?i:represented by)"
    r"\s+(?:(?i:his|her|their)\s+)?"
    r"(?i:LR['’]?s|legal representatives?)\b"
)

DEFENDANT_PARENT = re.compile(
    r"^\s*DEFENDANT\s+NO\.?\s*"
    r"(?P<number>\d{1,3})"
    r"\s*[./]?\s*$",
    re.IGNORECASE,
)

RESPONDENT_ENTRY = re.compile(
    r"^\s*(?P<number>\d{1,3})"
    r"\s*[.,)]\s*"
)

RESPONDENT_NAME = re.compile(
    r"^\s*(?P<number>\d{1,3})"
    r"\s*[.,)]\s*"
    rf"(?:{HONORIFIC})?"
    rf"(?P<name>{NAME}?)"
    r"(?=\s*[,;]"
    r"|\s+(?i:W/o|S/o|D/o|aged)"
    r"|$)"
)

DEFENDANT_SUBENTRY = re.compile(
    r"\bDEFENDANT\s+NO\.?\s*"
    r"(?P<number>\d{1,3})"
    r"\s*[(\{|]\s*"
    r"(?P<letter>[a-zA-Z])"
    r"\s*\)",
    re.IGNORECASE,
)

RESPONDENT_LABEL = re.compile(
    r"\bRESPONDENT\s+NO\.?\s*"
    r"(?P<number>\d{1,3})\b",
    re.IGNORECASE,
)

STOP_SECTION = re.compile(
    r"^\s*(?:WHEREAS|SCHEDULE"
    r"|SUMMONS TO|Given under"
    r"|R\d+\s+to\s*R?\d+)\b",
    re.IGNORECASE,
)

RELATIONSHIP_PATTERNS = {

    "WIFE": (
        r"(?:W\s*/\s*o|wife of)"
    ),

    "SON": (
        r"(?:S\s*/\s*o|son of)"
    ),

    "DAUGHTER": (
        r"(?:D\s*/\s*o|daughter of)"
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

    for relationship, marker in (
        RELATIONSHIP_PATTERNS.items()
    ):

        pattern = (
            rf"\b{marker}"
            r"[\s.,]*"
            r"(?:Late[\s.]+)?"
            + re.escape(deceased_name)
            + r"(?=\s|[,.;]|$)"
        )

        if re.search(
            pattern,
            evidence,
            re.IGNORECASE,
        ):

            return relationship

    return None


def extract_ocr_legal_representatives(raw_text):

    text = normalize_text(raw_text)

    lines = text.splitlines()

    associations = []

    for index, line in enumerate(lines):

        parent = PARENT_PATTERN.search(line)

        if not parent:
            continue

        deceased_name = clean_name(
            parent.group("name")
        )

        if not validate_person_name(
            deceased_name, "en"
        ):
            continue

        # Require explicit defendant numbering
        # immediately after the parent statement.

        parent_number = None
        parent_end = None

        for position in range(
            index + 1,
            min(len(lines), index + 3),
        ):

            if (
                RESPONDENT_ENTRY.search(lines[position])
                or STOP_SECTION.search(lines[position])
            ):
                break

            number_match = DEFENDANT_PARENT.search(
                lines[position]
            )

            if number_match:

                parent_number = number_match.group(
                    "number"
                )

                parent_end = position

                break

        if parent_number is None:
            continue

        parent_evidence = "\n".join(
            lines[index:parent_end + 1]
        )

        limit = min(
            len(lines),
            parent_end + 31,
        )

        position = parent_end + 1

        while position < limit:

            entry = lines[position]

            if STOP_SECTION.search(entry):
                break

            entry_match = RESPONDENT_ENTRY.search(
                entry
            )

            if not entry_match:

                position += 1

                continue

            block_start = position

            block_end = position + 1

            # A respondent block cannot cross
            # another numbered entry.

            while block_end < min(
                limit,
                block_start + 8,
            ):

                next_line = lines[block_end]

                if (
                    RESPONDENT_ENTRY.search(next_line)
                    or STOP_SECTION.search(next_line)
                    or PARENT_PATTERN.search(next_line)
                ):
                    break

                block_end += 1

            evidence = "\n".join(
                lines[block_start:block_end]
            )

            position = block_end

            subentries = list(
                DEFENDANT_SUBENTRY.finditer(evidence)
            )

            # Stop at unrelated or ambiguous
            # defendant numbering.

            if len(subentries) != 1:
                break

            subentry = subentries[0]

            if (
                subentry.group("number")
                != parent_number
            ):
                break

            representative = RESPONDENT_NAME.search(
                entry
            )

            if not representative:
                continue

            name = clean_name(
                representative.group("name")
            )

            if not validate_person_name(
                name, "en"
            ):
                continue

            respondent_number = (
                representative.group("number")
            )

            respondent_labels = {
                match.group("number")
                for match in RESPONDENT_LABEL.finditer(
                    evidence
                )
            }

            # Do not associate contradictory
            # respondent numbers.

            if respondent_labels != {
                respondent_number
            }:
                continue

            letter = subentry.group(
                "letter"
            ).lower()

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

                "respondent_number": respondent_number,

                "role": "LEGAL_REPRESENTATIVE",

                "language": "en",

                "relationship": relationship,

                "relationship_uncertain": (
                    relationship is None
                ),

                "association_method": (
                    "OCR_DEFENDANT_SUBENTRY"
                ),

                "raw_defendant_label": (
                    subentry.group(0)
                ),

                "parent_source_text": parent_evidence,

                "source_text": evidence,

                "parent_start_line": index + 1,

                "parent_end_line": parent_end + 1,

                "representative_start_line": (
                    block_start + 1
                ),

                "representative_end_line": block_end,

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
