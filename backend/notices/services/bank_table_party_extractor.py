"""
Conservative extraction of financial parties from OCR tables.

Preserves OCR evidence.
Does not verify identities or infer individual financial roles
from combined table headings.
"""

import re
import unicodedata


KN_TOKEN = r"[\u0C80-\u0CFF.]+"
KN_NAME = rf"{KN_TOKEN}(?:[ \t]+{KN_TOKEN}){{0,4}}"

HONORIFIC = r"(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ)[. \t]+"

UNSPECIFIED = "FINANCIAL_PARTY_UNSPECIFIED"

ROLE_LABELS = {
    "ಸಾಲಗಾರ": "BORROWER",
    "ಸಾಲಗಾರರು": "BORROWER",
    "ಸಹ ಸಾಲಗಾರ": "CO_BORROWER",
    "ಸಹ-ಸಾಲಗಾರ": "CO_BORROWER",
    "ಅರ್ಜಿದಾರ": "APPLICANT",
    "ಸಹ ಅರ್ಜಿದಾರ": "CO_APPLICANT",
    "ಸಹ ಅರ್ಜಿದಾರರು": "CO_APPLICANT",
    "ಸಹ-ಅರ್ಜಿದಾರ": "CO_APPLICANT",
    "ಜಾಮೀನುದಾರ": "GUARANTOR",
    "ಜಾಮೀನುದಾರರು": "GUARANTOR",
    "ಖಾತರಿದಾರ": "GUARANTOR",
    "ಅಡಮಾನದಾರ": "MORTGAGOR",
}

TABLE_HEADER = re.compile(
    r"(?:ಸಾಲಗಾರ|ಅರ್ಜಿದಾರ|ಜಾಮೀನುದಾರ|ಖಾತರಿದಾರ)"
    r".{0,100}(?:ಹೆಸರು|ವಿಳಾಸ)"
    r"|(?:borrower|applicant|guarantor)"
    r".{0,100}(?:name|address)",
    re.IGNORECASE,
)

STOP_SECTION = re.compile(
    r"^\s*(?:ಹರಾಜಿನ ದಿನಾಂಕ|ಮಾರಾಟದ ನಿಯಮ"
    r"|ಷರತ್ತುಗಳು|Terms and Conditions"
    r"|Date of Auction)",
    re.IGNORECASE,
)

PROPERTY_TERMS = re.compile(
    r"ಸ್ಥಿರಾಸ್ತಿ|ಸಕಲ ಸಮಸ್ತ|ಷೆಡ್ಯೂಲ್"
    r"|ನಿವೇಶನ|ಅಸೆಸ್‌ಮೆಂಟ್|ಅಸೆಸ್ಮೆಂಟ್"
    r"|ಪೂರ್ವಕ್ಕೆ|ಪಶ್ಚಿಮಕ್ಕೆ|ಉತ್ತರಕ್ಕೆ|ದಕ್ಷಿಣಕ್ಕೆ"
)

INVALID_NAME_TERMS = (
    "ವಿಳಾಸ", "ಸಾಲಗಾರ", "ಜಾಮೀನುದಾರ",
    "ಖಾತರಿದಾರ", "ನಿವೇಶನ", "ಸ್ಥಿರಾಸ್ತಿ",
    "ಗ್ರಾಮ", "ಹೋಬಳಿ", "ತಾಲೂಕು",
    "ಬ್ಯಾಂಕ್", "ಮೊತ್ತ", "ದಿನಾಂಕ",
    "ಪೂರ್ವಕ್ಕೆ", "ಪಶ್ಚಿಮಕ್ಕೆ",
    "ಉತ್ತರಕ್ಕೆ", "ದಕ್ಷಿಣಕ್ಕೆ",
    "ಸಂಖ್ಯೆ", "ಅಧಿಕಾರಿ", "ಮತ್ತು",
    "ರಸ್ತೆ", "ಬಾಕಿ", "ದಾಖಲೆ",
    "ಆಸ್ತಿ", "ಸಕಲ", "ಸಮಸ್ತ",
)



NON_PERSON_TERMS = (
    "ನೀರು",
    "ವಿದ್ಯುತ್",
    "ನೈರ್ಮಲ್ಯ",
    "ವ್ಯವಸ್ಥೆ",
    "ಸೌಲಭ್ಯ",
    "ಒಟ್ಟು",
    "ಸಹಿ",
    "ನೀಡಲಾಗುತ್ತಿದೆ",
    "ಹೊಸದಾಗಿ",
    "ವಿಸ್ತೀರ್ಣ",
    "ಎಕರೆ",
    "ಗುಂಟೆ",
    "ಜಮೀನು",
)

NON_PARTY_SLASH_CONTEXT = re.compile(
    r"ಸೌಲಭ್ಯ|ವಿದ್ಯುತ್|ನೈರ್ಮಲ್ಯ"
    r"|ವಿಸ್ತೀರ್ಣ|ಎಕರೆ|ಗುಂಟೆ"
    r"|ಸರ್ವೆ|ಸಹಿ|ನೀಡಲಾಗುತ್ತಿದೆ"
    r"|ಪೂರ್ವಕ್ಕೆ|ಪಶ್ಚಿಮಕ್ಕೆ"
    r"|ಉತ್ತರಕ್ಕೆ|ದಕ್ಷಿಣಕ್ಕೆ"
    r"|ಒಟ್ಟು"
)


def clean_table_party_name(name):

    name = re.split(
        r"\s+(?:ಇವರೆಲ್ಲರ|ಇವರಿಬ್ಬರ|ಇವರ"
        r"|ಅವರೆಲ್ಲರ|ಅವರಿಬ್ಬರ|ಅವರ)"
        r"(?=\s|$|[.,:;])",
        name,
        maxsplit=1,
    )[0]

    return name.strip(" ,;:/|.")


def is_non_person_text(name):

    return any(
        term in name
        for term in NON_PERSON_TERMS
    )


def normalize_text(text):
    return (
        unicodedata.normalize("NFC", text or "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )


def extract_bank_table_parties(raw_text):
    text = normalize_text(raw_text)
    lines = text.splitlines()
    candidates = []

    def add(name, role, evidence, method, line_number):
        name = re.sub(r"\s+", " ", name).strip(" ,;:/|")

        name = clean_table_party_name(name)

        if is_non_person_text(name):
            return

        if not name or len(name) < 2 or len(name) > 80:
            return

        if any(term in name for term in INVALID_NAME_TERMS):
            return

        if re.search(r"\d", name):
            return

        candidates.append({
            "name": name,
            "role": role,
            "language": "kn",
            "source_text": evidence.strip(),
            "extraction_method": method,
            "line_number": line_number,
        })

    # Find financial party table headings.
    header_indices = [
        i for i, line in enumerate(lines)
        if TABLE_HEADER.search(line)
    ]

    # Process explicit representative statements.
    # No borrower role is inferred.
    for index, line in enumerate(lines):
        match = re.search(
            rf"ಪ್ರತಿನಿಧಿತ\s+{HONORIFIC}"
            rf"(?P<name>{KN_NAME}?)"
            r"(?=\s*[,;|]|\s+ಬಿನ್|$)",
            line,
        )

        if match:
            add(
                match.group("name"),
                "BUSINESS_REPRESENTATIVE",
                line,
                "BANK_TABLE_REPRESENTATIVE",
                index + 1,
            )

    # Process only bounded financial party table sections.
    for header_index in header_indices:

        for index in range(
            header_index + 1,
            min(header_index + 36, len(lines))
        ):
            line = lines[index]

            if STOP_SECTION.search(line):
                break

            # Remove recognizable property-column content.
            left = re.split(
                r"\||\[|ಸ್ಥಿರಾಸ್ತಿ|ಸಕಲ ಸಮಸ್ತ"
                r"|ಷೆಡ್ಯೂಲ್|ಸಾಲದ ದಾಖಲೆ",
                line,
                maxsplit=1,
            )[0]

            # Ignore address-only lines.
            if re.match(
                r"^\s*(?:ವಿಳಾಸ|ಇನ್ನೊಂದು ವಿಳಾಸ)",
                left,
            ):
                continue

            # Slash-separated names in the party column.
            if (
                re.search(r"[/!]", left)
                and not NON_PARTY_SLASH_CONTEXT.search(left)
                and not left.rstrip().endswith("/-")
            ):
                for part in re.split(r"[/!]", left):
                    part = part.strip()

                    part = re.sub(
                        rf"^{HONORIFIC}", "", part
                    )

                    if re.fullmatch(KN_NAME, part):
                        add(
                            part,
                            UNSPECIFIED,
                            line,
                            "BANK_TABLE_SLASH_PARTY",
                            index + 1,
                        )

            # Numbered or honorific-based party entries.
            # Keep the role unspecified unless explicitly stated.
            pattern = (
                rf"{HONORIFIC}"
                rf"(?P<name>{KN_NAME}?)"
                r"(?=\s*(?:[,;(/|]|$)"
                r"|\s+(?:ಬಿನ್|ಕೋಂ|ರೂ|ಲೇಟ್|ವಿಳಾಸ))"
            )

            for match in re.finditer(pattern, left):

                # Exclude names embedded in boundary descriptions.
                prefix = left[:match.start()]

                if PROPERTY_TERMS.search(prefix):
                    continue

                if re.search(
                    r"ಬಿನ್|ಕೋಂ|ಪತ್ನಿ|ಮಗ|ಮಗಳು",
                    prefix,
                ):
                    continue

                name = match.group("name")
                role = UNSPECIFIED

                suffix = left[match.end():]

                role_match = re.match(
                    r"\s*\(([^)\n]{2,80})\)",
                    suffix,
                )

                if role_match:
                    labels = re.split(
                        r"\s+ಮತ್ತು\s+|/",
                        role_match.group(1),
                    )

                    roles = [
                        ROLE_LABELS.get(label.strip())
                        for label in labels
                    ]

                    if roles and all(roles):
                        for explicit_role in roles:
                            add(
                                name,
                                explicit_role,
                                line,
                                "BANK_TABLE_EXPLICIT_ROLE",
                                index + 1,
                            )
                        continue

                add(
                    name,
                    role,
                    line,
                    "BANK_TABLE_PARTY_CANDIDATE",
                    index + 1,
                )

    unique = {}

    for item in candidates:
        key = (
            item["name"].casefold(),
            item["role"],
            item["line_number"],
        )
        unique[key] = item

    return list(unique.values())
