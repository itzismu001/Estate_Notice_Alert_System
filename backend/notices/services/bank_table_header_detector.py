"""
Detect financial table headings in English and Kannada OCR.

Heading detection does not establish a person's financial role.
All detected headings remain unverified.
"""

import re
import unicodedata


ROLE_PATTERN = re.compile(
    r"ಸಾಲಗಾರ|ಸಾಲದಾರ|ಜಾಮೀನು"
    r"|ಖಾತರಿ|ಅಡಮಾನ|ಅರ್ಜಿದಾರ"
    r"|borrower|guarantor|mortgagor|applicant",
    re.IGNORECASE,
)

NAME_PATTERN = re.compile(
    r"ಹೆಸರು|name",
    re.IGNORECASE,
)

ACCOUNT_PATTERN = re.compile(
    r"ಸಾಲದ\s+ಖಾತ[ೆಾ]"
    r"|loan\s+account",
    re.IGNORECASE,
)

FINANCIAL_COLUMN_PATTERN = re.compile(
    r"ಬಾಕಿ\s+ಮೊತ್ತ?"
    r"|ಡಿಮಾಂಡ್|ಮೀಸಲು\s+ಬೆಲೆ"
    r"|ಇಎಂಡಿ|ಸ್ವಾಧೀನ|ಸ್ನಾಧೀನ"
    r"|amount|demand|reserve\s+price",
    re.IGNORECASE,
)

PROPERTY_COLUMN_PATTERN = re.compile(
    r"ಆಸ್ತಿ|ಸ್ಥಿರಾಸ್ತಿ|ಸಿರಾಸ್ತಿ"
    r"|property|schedule",
    re.IGNORECASE,
)

TABLE_STRUCTURE_PATTERN = re.compile(
    r"\||ಕ್ರ\.|ಕ್ರ\s|ಸಂ\.|ನಂ\."
    r"|serial\s+no",
    re.IGNORECASE,
)

ENTRY_PATTERN = re.compile(
    r"^\s*(?:\(\d+\)|\d+[.,)])"
    r"\s*(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ"
    r"|Mr|Mrs|Ms|Sri)",
    re.IGNORECASE,
)


def normalize_header_text(text):

    return (
        unicodedata.normalize("NFC", text or "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )


def detect_financial_table_headers(raw_text):

    text = normalize_header_text(raw_text)
    lines = text.splitlines()
    candidates = []

    for start in range(len(lines)):

        for size in (1, 2, 3, 4):

            end = start + size

            if end > len(lines):
                break

            block = lines[start:end]

            # Do not include numbered person entries
            # inside the heading.
            if any(
                ENTRY_PATTERN.search(line)
                for line in block
            ):
                break

            joined = " ".join(block)

            # Avoid long narrative paragraphs.
            if len(joined) > 400:
                continue

            role = bool(
                ROLE_PATTERN.search(joined)
            )

            name = bool(
                NAME_PATTERN.search(joined)
            )

            account = bool(
                ACCOUNT_PATTERN.search(joined)
            )

            financial = bool(
                FINANCIAL_COLUMN_PATTERN.search(joined)
            )

            property_column = bool(
                PROPERTY_COLUMN_PATTERN.search(joined)
            )

            structure = bool(
                TABLE_STRUCTURE_PATTERN.search(joined)
            )

            heading_type = None

            if account and name and financial:

                heading_type = "LOAN_ACCOUNT_TABLE"

            elif role and name and (
                financial or structure
            ):

                heading_type = "FINANCIAL_PARTY_TABLE"

            elif (
                role
                and financial
                and property_column
                and structure
            ):

                heading_type = "AUCTION_OR_PROPERTY_TABLE"

            if heading_type is None:
                continue

            # Check for a plausible nearby person entry.
            following = "\n".join(
                lines[end:min(end + 8, len(lines))]
            )

            nearby_person_marker = bool(
                re.search(
                    r"ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ"
                    r"|(?:Mr|Mrs|Ms|Sri)\.?\s",
                    following,
                    re.IGNORECASE,
                )
            )

            nearby_slash_entry = bool(
                re.search(
                    r"[\u0C80-\u0CFF. ]{2,40}"
                    r"[/!][\u0C80-\u0CFF. ]{2,40}",
                    following,
                )
            )

            if not (
                nearby_person_marker
                or nearby_slash_entry
            ):
                continue

            candidates.append({
                "start_line": start + 1,
                "end_line": end,
                "heading_type": heading_type,
                "source_text": "\n".join(block),
                "matched_features": {
                    "financial_role": role,
                    "name_column": name,
                    "loan_account": account,
                    "financial_column": financial,
                    "property_column": property_column,
                    "table_structure": structure,
                },
                "requires_review": True,
                "verified": False,
                "eligible_for_alert": False,
            })

            break

    # Remove overlapping heading candidates.
    # Prefer headings with stronger column evidence.
    ranked = sorted(
        candidates,
        key=lambda item: (
            -sum(item["matched_features"].values()),
            item["end_line"] - item["start_line"],
            item["start_line"],
        ),
    )

    selected = []

    for item in ranked:

        overlaps = any(
            item["start_line"] <= other["end_line"]
            and item["end_line"] >= other["start_line"]
            for other in selected
        )

        if not overlaps:
            selected.append(item)

    return sorted(
        selected,
        key=lambda item: item["start_line"],
    )
