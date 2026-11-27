"""
English and Kannada secured-property party extraction.

All extracted information is unverified.
Ambiguous financial roles require manual review.
"""

import re
import unicodedata

from notices.services.bank_table_party_extractor import (
    extract_bank_table_parties,
)


from notices.services.party_name_extractor import (
    extract_party_candidates,
    validate_person_name,
    clean_name,
)


BANK_CATEGORIES = {
    "SECURED_PROPERTY_DEMAND",
    "SECURED_PROPERTY_POSSESSION",
    "SECURED_PROPERTY_AUCTION",
    "SECURED_PROPERTY_OTHER",
}


KN_HONORIFIC = (
    r"(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ)"
    r"[.:\s]+"
)

KN_TOKEN = r"[\u0C80-\u0CFF.]+"

KN_NAME = (
    rf"{KN_TOKEN}"
    rf"(?:[ \t]+{KN_TOKEN}){{0,5}}"
)

EN_HONORIFIC = (
    r"(?i:Mr|Mrs|Ms|Sri|Shri|Smt|Dr)"
    r"[.\s]+"
)

EN_TOKEN = (
    r"(?:[A-Z](?:\.[A-Za-z]+)+\.?"
    r"|[A-Z][A-Za-z'-]*\.?)"
)

EN_NAME = (
    rf"{EN_TOKEN}"
    rf"(?:[ \t]+{EN_TOKEN}){{0,5}}"
)


KN_ROLES = {
    "ಸಾಲಗಾರ": "BORROWER",
    "ಸಾಲಗಾರರು": "BORROWER",
    "ಸಹ ಸಾಲಗಾರ": "CO_BORROWER",
    "ಸಹ-ಸಾಲಗಾರ": "CO_BORROWER",
    "ಅರ್ಜಿದಾರ": "APPLICANT",
    "ಸಹ ಅರ್ಜಿದಾರ": "CO_APPLICANT",
    "ಸಹ ಅರ್ಜಿದಾರರು": "CO_APPLICANT",
    "ಜಾಮೀನುದಾರ": "GUARANTOR",
    "ಜಾಮೀನುದಾರರು": "GUARANTOR",
    "ಖಾತರಿದಾರ": "GUARANTOR",
    "ಅಡಮಾನದಾರ": "MORTGAGOR",
}


EN_ROLES = {
    "borrower": "BORROWER",
    "co-borrower": "CO_BORROWER",
    "co borrower": "CO_BORROWER",
    "applicant": "APPLICANT",
    "co-applicant": "CO_APPLICANT",
    "co applicant": "CO_APPLICANT",
    "guarantor": "GUARANTOR",
    "mortgagor": "MORTGAGOR",
    "authorized officer": "AUTHORIZED_OFFICER",
    "authorised officer": "AUTHORIZED_OFFICER",
    "deceased borrower": "DECEASED_BORROWER",
}


# Recognizable institution names.
# These are extraction patterns, not a verified registry.

ORGANIZATION_PATTERNS = [

    (
        r"ಯೂನಿಯನ್\s+ಬ್ಯಾಂಕ್\s+ಆಫ್\s+ಇಂಡಿಯಾ"
        r"|Union Bank of India",
        "Union Bank of India",
    ),

    (
        r"ಐಸಿಐಸಿಐ\s+ಬ್ಯಾಂಕ್"
        r"(?:\s+ಲಿಮಿಟೆಡ್)?"
        r"|ICICI Bank(?: Limited)?",
        "ICICI Bank",
    ),

    (
        r"ಜನ\s*ಸ್ಮಾಲ್\s+ಫೈನಾನ್ಸ್\s*ಬ್ಯಾಂಕ್"
        r"(?:\s+ಲಿಮಿಟೆಡ್)?"
        r"|Jana Small Finance Bank",
        "Jana Small Finance Bank",
    ),

    (
        r"ಐಡಿಬಿಐ\s+ಬ್ಯಾಂಕ್"
        r"(?:\s+ಲಿಮಿಟೆಡ್)?"
        r"|IDBI Bank(?: Limited)?",
        "IDBI Bank",
    ),

    (
        r"ಆರ್ಬಿಎಲ್\s+ಬ್ಯಾಂಕ್"
        r"(?:\s+ಲಿಮಿಟೆಡ್)?"
        r"|RBL Bank(?: Limited)?",
        "RBL Bank",
    ),

    (
        r"ಬ್ಯಾಂಕ್\s+ಆಫ್\s+ಬರೋಡ"
        r"|Bank of Baroda",
        "Bank of Baroda",
    ),

    (
        r"Aptus Value Housing Finance India"
        r"(?: Limited)?",
        "Aptus Value Housing Finance India",
    ),
]


FINANCIAL_ROLES = {
    "BUSINESS_REPRESENTATIVE",

    "BORROWER",
    "CO_BORROWER",
    "APPLICANT",
    "CO_APPLICANT",
    "GUARANTOR",
    "MORTGAGOR",
    "DECEASED_BORROWER",
    "AUTHORIZED_OFFICER",
    "FINANCIAL_PARTY_UNSPECIFIED",

}


def normalize_bank_text(text):

    text = unicodedata.normalize(
        "NFC", text or ""
    )

    return (
        text.replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )


def normalize_role_label(value):

    value = re.sub(
        r"\s*-\s*", "-", value
    )

    return re.sub(
        r"\s+", " ", value
    ).strip().casefold()


def add_bank_candidate(
    candidates,
    name,
    role,
    language,
    evidence,
    method,
):

    name = clean_name(name)

    if not validate_person_name(
        name, language
    ):
        return

    if role not in FINANCIAL_ROLES:
        return

    candidates.append({

        "name": name,

        "role": role,

        "language": language,

        "entity_kind": "PERSON",

        "source_text": evidence.strip(),

        "extraction_method": method,

        "role_ambiguous": (
            role == "FINANCIAL_PARTY_UNSPECIFIED"
        ),

        "verified": False,

        "requires_review": True,

        "approved_for_search": False,

        "eligible_for_alert": False,

    })


def extract_bank_organizations(text):

    organizations = []

    for pattern, suggested_name in (
        ORGANIZATION_PATTERNS
    ):

        matches = list(
            re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            )
        )

        if not matches:
            continue

        evidence = list(dict.fromkeys(
            match.group(0)
            for match in matches
        ))

        organizations.append({

            "name": evidence[0],

            "suggested_name": suggested_name,

            "role": "SECURED_CREDITOR_CANDIDATE",

            "entity_kind": "ORGANIZATION",

            "source_text": evidence[0],

            "evidence": evidence,

            "verified": False,

            "requires_review": True,

            "approved_for_search": False,

            "eligible_for_alert": False,

        })

    return organizations


def extract_english_bank_parties(text):

    candidates = []

    role_pattern = "|".join(

        re.escape(role)

        for role in sorted(
            EN_ROLES,
            key=len,
            reverse=True,
        )
    )

    # Explicit role followed by a person's name.

    pattern = (

        rf"\b(?P<role>(?i:{role_pattern}))"

        rf"\s*:\s*"

        rf"(?:{EN_HONORIFIC})?"

        rf"(?P<name>{EN_NAME}?)"

        r"(?=\s*(?:[,;|\n()]|$)"

        r"|\s+(?i:S/o|D/o|W/o|aged|residing)\b)"

    )

    for match in re.finditer(
        pattern, text
    ):

        role = EN_ROLES.get(
            normalize_role_label(
                match.group("role")
            )
        )

        if role:

            add_bank_candidate(
                candidates,
                match.group("name"),
                role,
                "en",
                match.group(0),
                "BANK_ENGLISH_ROLE_PREFIX",
            )

    # Name followed by an explicit role.

    suffix_pattern = (

        rf"{EN_HONORIFIC}"

        rf"(?P<name>{EN_NAME}?)"

        rf"\s*\((?P<role>(?i:{role_pattern}))\)"

    )

    for match in re.finditer(
        suffix_pattern, text
    ):

        role = EN_ROLES.get(
            normalize_role_label(
                match.group("role")
            )
        )

        if role:

            add_bank_candidate(
                candidates,
                match.group("name"),
                role,
                "en",
                match.group(0),
                "BANK_ENGLISH_ROLE_SUFFIX",
            )

    return candidates


def extract_kannada_bank_parties(text):

    candidates = []

    # Explicit Kannada role labels.

    role_pattern = "|".join(

        re.escape(role)

        for role in sorted(
            KN_ROLES,
            key=len,
            reverse=True,
        )
    )

    pattern = (

        rf"(?P<role>{role_pattern})"

        rf"\s*:\s*"

        rf"{KN_HONORIFIC}"

        rf"(?P<name>{KN_NAME}?)"

        r"(?=\s*(?:[,;|\n()]|$)"

        r"|\s+(?:ಬಿನ್|ಕೋಂ|ವಿಳಾಸ|ನಂ)\b)"

    )

    for match in re.finditer(
        pattern, text
    ):

        role = KN_ROLES.get(
            normalize_role_label(
                match.group("role")
            )
        )

        if role:

            add_bank_candidate(
                candidates,
                match.group("name"),
                role,
                "kn",
                match.group(0),
                "BANK_KANNADA_ROLE_PREFIX",
            )

    # Direct role suffix, including multiple roles.

    suffix_pattern = (

        rf"{KN_HONORIFIC}"

        rf"(?P<name>{KN_NAME}?)"

        r"\s*(?:ರೂ\.\s*)?"

        r"\(\s*(?P<roles>[^)\n]{2,90})\)"

    )

    for match in re.finditer(
        suffix_pattern, text
    ):

        labels = re.split(
            r"\s+ಮತ್ತು\s+|/",
            match.group("roles"),
        )

        roles = [

            KN_ROLES.get(
                normalize_role_label(label)
            )

            for label in labels
        ]

        if not roles or not all(roles):
            continue

        for role in roles:

            add_bank_candidate(
                candidates,
                match.group("name"),
                role,
                "kn",
                match.group(0),
                "BANK_KANNADA_ROLE_SUFFIX",
            )

    # Deceased borrower context.

    deceased_pattern = (

        r"\(ಮೃತ\s+ಸಾಲಗಾರರ\s+ಆಸ್ತಿ\)"

        rf"\s*{KN_HONORIFIC}"

        rf"(?P<name>{KN_NAME}?)"

        r"(?=\s+(?:ಲೇಟ್|ಬಿನ್|ಕೋಂ|ವಿಳಾಸ)"

        r"|\s*[,;|\n])"

    )

    for match in re.finditer(
        deceased_pattern, text
    ):

        add_bank_candidate(
            candidates,
            match.group("name"),
            "FINANCIAL_PARTY_UNSPECIFIED",
            "kn",
            match.group(0),
            "BANK_DECEASED_PROPERTY_CONTEXT",
        )

    return candidates


def extract_kannada_officers(text):

    candidates = []

    for line in text.splitlines():

        if not re.search(
            r"ಅಧಿಕೃತ\s+ಅಧಿಕಾರಿ",
            line,
        ):
            continue

        pattern = (

            rf"{KN_HONORIFIC}"

            rf"(?P<name>{KN_NAME}?)"

            r"(?=\s*(?:ನಂ\s*[:.]"

            r"|ಸಂಪರ್ಕ\s+ಸಂಖ್ಯೆ"

            r"|ದೂರವಾಣಿ"

            r"|[,;]"

            r"|$))"

        )

        for match in re.finditer(
            pattern, line
        ):

            add_bank_candidate(
                candidates,
                match.group("name"),
                "AUTHORIZED_OFFICER",
                "kn",
                line,
                "BANK_KANNADA_OFFICER",
            )

    return candidates


def extract_combined_role_parties(text):

    candidates = []

    lines = text.splitlines()

    for index, line in enumerate(lines):

        # A combined heading cannot establish
        # which individual has which financial role.

        if not re.search(
            r"ಸಾಲಗಾರರು?\s+ಮತ್ತು\s+"
            r"ಜಾಮೀನುದಾರರ\s+ಹೆಸರು\s+"
            r"ಮತ್ತು\s+ವಿಳಾಸ\s*:",
            line,
        ):
            continue

        section = line.split(":", 1)[-1]

        parts = re.split(
            r"\s+ಮತ್ತು\s+",
            section,
        )

        for part in parts:

            match = re.match(

                rf"\s*{KN_HONORIFIC}"

                rf"(?P<name>{KN_NAME})",

                part.strip(),

            )

            if match:

                add_bank_candidate(
                    candidates,
                    match.group("name").rstrip("."),
                    "FINANCIAL_PARTY_UNSPECIFIED",
                    "kn",
                    line,
                    "BANK_COMBINED_ROLE_HEADING",
                )

    return candidates


def deduplicate_bank_candidates(candidates):

    unique = {}

    for item in candidates:

        key = (

            item["name"].casefold(),

            item["role"],

            item["language"],

        )

        if key not in unique:

            unique[key] = dict(item)

            unique[key]["evidence"] = [
                item["source_text"]
            ]

        else:

            evidence = unique[key]["evidence"]

            if item["source_text"] not in evidence:

                evidence.append(
                    item["source_text"]
                )

    return list(unique.values())


def integrate_recovered_bank_parties(
    existing_candidates,
    recovered_candidates,
):
    """
    Preserve existing and recovered financial party
    candidates without merging identities.
    """

    from copy import deepcopy

    combined = deepcopy(existing_candidates)

    existing_keys = {
        (
            item["name"].casefold(),
            item["role"],
            item["language"],
        )
        for item in existing_candidates
    }

    for candidate in recovered_candidates:

        item = deepcopy(candidate)

        key = (
            item["name"].casefold(),
            item["role"],
            item["language"],
        )

        item["existing_name_role_match"] = (
            key in existing_keys
        )

        item["evidence"] = [{
            "source_text": item["source_text"],
            "extraction_method": item[
                "extraction_method"
            ],
            "start_line": item["start_line"],
            "end_line": item["end_line"],
            "heading_evidence": item[
                "heading_evidence"
            ],
        }]

        item["requires_review"] = True
        item["verified"] = False
        item["approved_for_search"] = False
        item["eligible_for_alert"] = False
        item["identity_merged"] = False

        combined.append(item)

    return combined



def integrate_recovered_organizations(
    existing_candidates,
    raw_text,
    notice_category,
):
    """
    Preserve existing organizations and append supported
    recovery suggestions without verifying legal identity.
    """

    from copy import deepcopy

    from notices.services.organization_recovery import (
        recover_organization_candidates,
    )

    from notices.services.organization_ocr_validator import (
        organization_key,
    )

    candidates = deepcopy(existing_candidates)

    existing_keys = {
        organization_key(item)
        for item in candidates
    }

    recovered = recover_organization_candidates(
        raw_text,
        notice_category,
    )

    for item in recovered["organization_candidates"]:

        key = organization_key(item)

        if key in existing_keys:
            continue

        candidates.append(deepcopy(item))

        existing_keys.add(key)

    return candidates


def extract_bank_party_candidates(
    raw_text,
    notice_category,
):

    category = str(
        notice_category or ""
    ).upper()

    result = {

        "applicable": (
            category in BANK_CATEGORIES
        ),

        "notice_category": category,

        "party_candidates": [],

        "organization_candidates": [],

        "candidate_count": 0,

        "organization_count": 0,

        "requires_review": True,

        "verified": False,

        "approved_for_search": False,

        "eligible_for_alert": False,

    }

    if not result["applicable"]:
        return result

    text = normalize_bank_text(
        raw_text
    )

    candidates = []

    # Preserve previously extracted financial roles.

    existing = extract_party_candidates(
        raw_text
    )

    for item in existing["party_candidates"]:

        if item["role"] not in FINANCIAL_ROLES:
            continue

        for evidence in (
            item.get("evidence")
            or [item["source_text"]]
        ):

            add_bank_candidate(
                candidates,
                item["name"],
                item["role"],
                item["language"],
                evidence,
                "EXISTING_PARTY_EXTRACTION",
            )

    candidates.extend(
        extract_english_bank_parties(text)
    )

    candidates.extend(
        extract_kannada_bank_parties(text)
    )

    candidates.extend(
        extract_kannada_officers(text)
    )

    candidates.extend(
        extract_combined_role_parties(text)
    )

    # Table-aware financial party candidates.
    for item in extract_bank_table_parties(text):

        # Avoid adding an unspecified role when the
        # same OCR name already has an explicit role.
        if item["role"] == "FINANCIAL_PARTY_UNSPECIFIED":
            if any(
                candidate["name"].casefold()
                == item["name"].casefold()
                and candidate["role"]
                != "FINANCIAL_PARTY_UNSPECIFIED"
                for candidate in candidates
            ):
                continue

        add_bank_candidate(
            candidates,
            item["name"],
            item["role"],
            item["language"],
            item["source_text"],
            item["extraction_method"],
        )

    candidates = deduplicate_bank_candidates(
        candidates
    )

    # Preserve recovered candidate evidence.
    from notices.services.bank_party_recovery import (
        recover_bank_parties,
    )

    recovered_candidates = recover_bank_parties(
        raw_text
    )

    candidates = integrate_recovered_bank_parties(
        candidates,
        recovered_candidates,
    )

    organizations = integrate_recovered_organizations(
        extract_bank_organizations(text),
        raw_text,
        notice_category,
    )

    result.update({

        "party_candidates": candidates,

        "organization_candidates": organizations,

        "candidate_count": len(candidates),

        "organization_count": len(organizations),

    })

    return result
