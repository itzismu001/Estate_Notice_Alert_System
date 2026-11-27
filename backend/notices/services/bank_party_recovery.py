"""
Recover financial party candidates from damaged OCR tables.

Preserve source evidence and avoid inferring individual
financial roles from combined table headings.
"""

import re

from notices.services.bank_hybrid_header_detector import (
    detect_hybrid_financial_headers,
)

from notices.services.bank_table_party_extractor import (
    normalize_text,
    clean_table_party_name,
    is_non_person_text,
    INVALID_NAME_TERMS,
)

from notices.services.party_name_extractor import (
    validate_person_name,
)


TOKEN = r"[\u0C80-\u0CFF.]+"

NAME = rf"{TOKEN}(?:[ \t]+{TOKEN}){{0,4}}"

HONORIFIC = r"(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ)[.:\s]+"

UNSPECIFIED = "FINANCIAL_PARTY_UNSPECIFIED"

RELATIONSHIP = r"ಬಿನ್|ಬಿನ|ಕೋಂ|ಪತ್ನಿ"

BOUNDARY = re.compile(
    r"ಪೂರ್ವಕ್ಕೆ|ಪಶ್ಚಿಮಕ್ಕೆ"
    r"|ಉತ್ತರಕ್ಕೆ|ದಕ್ಷಿಣಕ್ಕೆ"
    r"|ಚಕ್ಕುಬಂದಿ|ಗಡಿಗಳು"
)

STOP = re.compile(
    r"^\s*(?:ಆದುದುರಿಂದ|ದಿನಾಂಕ:"
    r"|ಹರಾಜಿನ ನಿಯಮಗಳು"
    r"|Terms and Conditions"
    r"|ಹರಾಜಿಗೆ ಸಂಬಂಧಿಸಿದ)"
)

ROLE_MAP = {
    "ಸಾಲಗಾರ": "BORROWER",
    "ಸಾಲಗಾರರು": "BORROWER",
    "ಅರ್ಜಿದಾರ": "APPLICANT",
    "ಅರ್ಜಿದಾರರು": "APPLICANT",
    "ಸಹ ಅರ್ಜಿದಾರ": "CO_APPLICANT",
    "ಸಹ ಅರ್ಜಿದಾರರು": "CO_APPLICANT",
    "ಅಡಮಾನದಾರ": "MORTGAGOR",
    "ಅಡಮಾನದಾರರು": "MORTGAGOR",
    "ಜಾಮೀನುದಾರ": "GUARANTOR",
    "ಜಾಮೀನುದಾರರು": "GUARANTOR",
}

EXTRA_INVALID = (
    "ಲೇಔಟ್",
    "ಷೆಡ್ಯೂಲ್",
    "ಮಹಡಿ",
    "ಲಕ್ಷದ",
    "ಸಾವಿರದ",
    "ಸಾಲದ",
    "ದಾಖಲೆಯಲ್ಲಿ",
    "ಸಂಪರ್ಕ",
    "ನೋಟೀಸ್",
    "ಅವಳಿಗೆ",
    "ಅವನಿಗೆ",
)


def recover_bank_parties(raw_text):

    text = normalize_text(raw_text)
    lines = text.splitlines()

    headers = detect_hybrid_financial_headers(text)

    candidates = []

    def add(name, role, start, end, method, header):

        name = clean_table_party_name(name)

        if not name:
            return

        if is_non_person_text(name):
            return

        if any(
            term in name
            for term in INVALID_NAME_TERMS
            + EXTRA_INVALID
        ):
            return

        if not validate_person_name(name, "kn"):
            return

        candidates.append({
            "name": name,
            "role": role,
            "language": "kn",
            "entity_kind": "PERSON",
            "source_text": "\n".join(
                lines[start:end + 1]
            ),
            "extraction_method": method,
            "start_line": start + 1,
            "end_line": end + 1,
            "heading_evidence": header["source_text"],
            "role_ambiguous": role == UNSPECIFIED,
            "requires_review": True,
            "verified": False,
            "approved_for_search": False,
            "eligible_for_alert": False,
        })

    for header_index, header in enumerate(headers):

        start = header["end_line"]

        end = min(start + 36, len(lines))

        if header_index + 1 < len(headers):

            end = min(
                end,
                headers[header_index + 1]["start_line"] - 1
            )

        for index in range(start, end):

            line = lines[index]

            if STOP.search(line):
                break

            # Slash-separated parties immediately
            # following a loan account heading.
            if (
                "LOAN_ACCOUNT_TABLE"
                in header["heading_types"]
                and index < start + 3
            ):

                left = re.split(
                    r"\||\(",
                    line,
                    maxsplit=1,
                )[0]

                if re.search(r"[/!]", left):

                    for part in re.split(r"[/!]", left):

                        part = part.strip()

                        if re.fullmatch(NAME, part):

                            add(
                                part,
                                UNSPECIFIED,
                                index,
                                index,
                                "RECOVERY_LOAN_ACCOUNT_PARTY",
                                header,
                            )

            # Numbered entries, including rows where
            # an account column precedes the name.
            numbered = re.search(
                rf"(?:^|\|\s*)"
                rf"\s*(?:[A-Z0-9]+\s+)?"
                rf"(?:\(\d+\)|\d+[.,)])"
                rf"\s*{HONORIFIC}"
                rf"(?P<name>{NAME}?)"
                rf"(?=\s*(?:[,;|\[]|$)"
                rf"|\s+(?:{RELATIONSHIP}"
                rf"|ರೂ|ಲೇಔಟ್|ಷೆಡ್ಯೂಲ್))",
                line,
            )

            if numbered:

                if not BOUNDARY.search(
                    line[:numbered.start()]
                ):

                    add(
                        numbered.group("name"),
                        UNSPECIFIED,
                        index,
                        index,
                        "RECOVERY_NUMBERED_PARTY",
                        header,
                    )

            # A name beginning in the first column
            # followed by a relationship marker.
            relationship = re.match(
                rf"^\s*(?P<name>{NAME}?)"
                rf"\s+(?:{RELATIONSHIP})\s+",
                line,
            )

            if (
                relationship
                and index > start
                and re.search(
                    r"ಶ್ರೀಮತಿ\s*[^\u0C80-\u0CFF]*$",
                    lines[index - 1].split("೧$")[0],
                )
            ):

                add(
                    relationship.group("name"),
                    UNSPECIFIED,
                    index - 1,
                    index,
                    "RECOVERY_MULTILINE_PARTY",
                    header,
                )

            # Explicit names followed by a role
            # on the next OCR line.
            person = re.search(
                rf"(?:^|\.\s+\d+[.,)]\s*"
                rf"|^\s*\d+[.,)]\s*)"
                rf"{HONORIFIC}"
                rf"(?P<name>{NAME}?)"
                rf"(?=\s*(?:[,;|\[]|$)"
                rf"|\s+(?:{RELATIONSHIP}|ರೂ))",
                line,
            )

            if not person:
                continue

            if BOUNDARY.search(line[:person.start()]):
                continue

            role_text = line[person.end():].split("|")[0]

            if index + 1 < end:

                next_line = lines[index + 1]

                # Only inspect the next line's first
                # column, not the property description.
                next_left = next_line.split("|")[0]

                role_text += "\n" + next_left

            role_match = re.search(
                r"\(([^()\n]{2,80})\)",
                role_text,
            )

            if not role_match:
                continue

            # Reject role association when another
            # explicitly named person intervenes.
            intervening_text = role_text[
                :role_match.start()
            ]

            if re.search(
                HONORIFIC,
                intervening_text,
            ):
                continue

            labels = re.split(
                r"\s+ಮತ್ತು\s+|/",
                role_match.group(1),
            )

            roles = []

            for label in labels:

                label = re.sub(
                    r"[-\s]+",
                    " ",
                    label,
                ).strip()

                roles.append(ROLE_MAP.get(label))

            if roles and all(roles):

                for role in roles:

                    add(
                        person.group("name"),
                        role,
                        index,
                        min(index + 1, end - 1),
                        "RECOVERY_EXPLICIT_MULTILINE_ROLE",
                        header,
                    )

    # Preserve separate roles and source occurrences.
    unique = {}

    for item in candidates:

        key = (
            item["name"].casefold(),
            item["role"],
            item["start_line"],
        )

        unique[key] = item

    items = list(unique.values())

    explicit_roles = {
        (
            item["name"].casefold(),
            item["start_line"],
        )
        for item in items
        if item["role"] != UNSPECIFIED
    }

    filtered = []

    for item in items:

        occurrence_key = (
            item["name"].casefold(),
            item["start_line"],
        )

        # Prefer an explicit role over an unspecified
        # role for the same source occurrence.
        if (
            item["role"] == UNSPECIFIED
            and occurrence_key in explicit_roles
        ):
            continue

        # Preserve ambiguity in OCR name separators.
        item["name_boundary_ambiguous"] = (
            item["extraction_method"]
            == "RECOVERY_LOAN_ACCOUNT_PARTY"
            and "!" in item["source_text"]
        )

        item["identity_merged"] = False

        filtered.append(item)

    return filtered
