import re
import unicodedata


HONORIFIC = (
    r"(?i:Mrs|Mr|Ms|Shri|Sri|Smt|Dr)"
    r"(?:[.,]\s*|\s+)"
)

TOKEN = (
    r"(?:[A-Z](?:\.[A-Za-z]+)+\.?"
    r"|\.?[A-Z][A-Za-z'-]*\.?)"
)

NAME = rf"{TOKEN}(?:[ \t]+{TOKEN}){{0,5}}"

ROLE = (
    r"(?i:PLAINTIFFS?|DEFENDANTS?|"
    r"APPELLANTS?|RESPONDENTS?|PETITIONERS?)"
)

RELATIONSHIP = (
    r"(?i:S/o|D/o|W/o|Slo|Dio|Wio|Dyo|0/0)"
)

ROLE_MAP = {
    "PLAINTIFFS": "PLAINTIFF",
    "DEFENDANTS": "DEFENDANT",
    "APPELLANTS": "APPELLANT",
    "RESPONDENTS": "RESPONDENT",
    "PETITIONERS": "PETITIONER"
}


def normalize_role(role):

    role = role.upper()

    return ROLE_MAP.get(role, role)


def extract_court_party_candidates(raw_text):

    text = unicodedata.normalize(
        "NFC", raw_text or ""
    )

    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")

    candidates = []

    # Require court-related context.

    if not re.search(
        r"\b(?:in the court of|"
        r"civil judge|civil court|"
        r"sessions court|court of the)\b",
        text,
        re.IGNORECASE
    ):
        return candidates

    def add(name, role, evidence, method):

        name = re.sub(
            r"\s+", " ", name
        ).strip(" ,:;-")

        if not name:
            return

        candidates.append({
            "name": name,
            "role": normalize_role(role),
            "language": "en",
            "source_text": evidence,
            "extraction_method": method
        })

    # Exclude general narrative and property
    # schedules from litigant extraction.

    stop = re.search(
        r"(?im)^[ \t]*(?:WHEREAS\b|"
        r"SCHEDULE\b|SUMMONS TO\b|"
        r"Given under\b)",
        text
    )

    party_section = (
        text[:stop.start()]
        if stop else text
    )

    flat = re.sub(
        r"\s+", " ", party_section
    )

    # ==========================================
    # 1. Name followed by an explicit court role
    # ==========================================

    suffix_pattern = (

        HONORIFIC

        + rf"(?P<name>{NAME}?)"

        + r"(?:\s*&\s*others)?"

        + r"\s*[.>»v\-]{1,8}\s*"

        + rf"(?P<role>{ROLE})\b"
    )

    for match in re.finditer(
        suffix_pattern, flat
    ):

        add(
            match.group("name"),
            match.group("role"),
            match.group(0),
            "COURT_EXPLICIT_ROLE_SUFFIX"
        )

    # ==========================================
    # 2. BETWEEN / AND declarations
    # ==========================================

    declaration_pattern = (

        r"(?i:\bBETWEEN|\bAND)"

        + r"\s*:?\s*"

        + rf"(?:{HONORIFIC})?"

        + rf"(?P<name>{NAME}?)"

        + r"(?:\s*(?i:&\s*others|"
        r"and\s+another|and\s+anether))?"

        + r"\s*[.>»v\-]*\s*"

        + rf"(?P<role>{ROLE})"

        + r"(?:'s)?\b"
    )

    for match in re.finditer(
        declaration_pattern, flat
    ):

        add(
            match.group("name"),
            match.group("role"),
            match.group(0),
            "COURT_PARTY_DECLARATION"
        )

    # ==========================================
    # 3. Numbered appellants and respondents
    # ==========================================

    # Detect entry boundaries even when a name
    # is corrupted, preventing role leakage.

    entry_pattern = re.compile(

        r"(?m)(?:^|(?<=BETWEEN:)|(?<=AND:))"

        + r"[ \t]*\d{1,3}[.,)]"

        + r"[ \t]*"
    )

    entries = list(
        entry_pattern.finditer(party_section)
    )

    name_pattern = re.compile(

        HONORIFIC

        + rf"(?P<name>{NAME}?)"

        + rf"(?=\s*,|\s+{RELATIONSHIP})"
    )

    for index, entry in enumerate(entries):

        end = (

            entries[index + 1].start()

            if index + 1 < len(entries)

            else len(party_section)
        )

        block = party_section[
            entry.end():end
        ]

        block = re.sub(r"\s+", " ", block)

        match = name_pattern.match(block)

        if not match:
            continue

        context = block[match.end():]

        # Prevent role assignment from a new
        # section or another named party.

        context = re.split(

            r"(?i)\b(?:NOTICE TO|"
            r"BETWEEN|WHEREAS|"
            r"Since dead Represented)\b"

            r"|(?i:\bAND\s*:)",

            context,

            maxsplit=1
        )[0]

        role_pattern = (

            rf"\b(?P<role>{ROLE})"

            + r"\s*(?:NO\.?\s*|110\.?\s*)"

            + r"\d+"
        )

        for role_match in re.finditer(
            role_pattern, context
        ):

            evidence = (

                entry.group(0)

                + block[:match.end()]

                + context[:role_match.end()]
            )

            add(
                match.group("name"),
                role_match.group("role"),
                evidence,
                "COURT_NUMBERED_EXPLICIT_ROLE"
            )

    # ==========================================
    # 4. Explicit numbered defendant list
    # ==========================================

    defendant_section = re.search(

        r"(?i)\bDEFENDANTS?\s*:",

        party_section
    )

    if defendant_section:

        block = party_section[
            defendant_section.end():
        ]

        block = re.sub(r"\s+", " ", block)

        pattern = (

            r"\b\d{1,3}[.)]\s*"

            + HONORIFIC

            + rf"(?P<name>{NAME}?)"

            + rf"(?=\s*,|\s+{RELATIONSHIP})"
        )

        for match in re.finditer(
            pattern, block
        ):

            add(
                match.group("name"),
                "DEFENDANT",
                defendant_section.group(0)
                + " "
                + match.group(0),
                "COURT_EXPLICIT_DEFENDANT_LIST"
            )

    # ==========================================
    # 5. Defendant named in summons
    # ==========================================

    addressed_pattern = (

        r"(?i:\bNOTICE TO DEFENDANT)"

        + r"\s*(?i:To)\s*[, :]\s*"

        + HONORIFIC

        + rf"(?P<name>{NAME}?)"

        + rf"(?=\s*,|\s+{RELATIONSHIP})"
    )

    for match in re.finditer(
        addressed_pattern, flat
    ):

        add(
            match.group("name"),
            "DEFENDANT",
            match.group(0),
            "COURT_ADDRESSED_DEFENDANT"
        )

    # ==========================================
    # 6. Firm representative
    # ==========================================

    partner_pattern = (

        r"(?i:\bby its partner)\s+"

        + HONORIFIC

        + rf"(?P<name>{NAME}?)"

        + r"(?=\s*,)"
    )

    for match in re.finditer(
        partner_pattern, flat
    ):

        add(
            match.group("name"),
            "FIRM_REPRESENTATIVE",
            match.group(0),
            "COURT_FIRM_REPRESENTATIVE"
        )

    # ==========================================
    # 7. Advocate signatures
    # ==========================================

    advocate_suffix = (

        r"(?m)^[ \t]*"

        + rf"(?:{HONORIFIC})?"

        + rf"(?P<name>{NAME}?)"

        + r"[ \t]*,[ \t]*"

        + r"(?i:Advocate)\b"
    )

    advocate_prefix = (

        r"(?m)^[ \t]*"

        + r"(?i:Advocate\s+for)\s+"

        + ROLE

        + r"[ \t]*:[ \t]*"

        + rf"(?P<name>{NAME}?)"

        + r"(?=[ \t]*[,;\n]|$)"
    )

    for pattern in (
        advocate_suffix,
        advocate_prefix
    ):

        for match in re.finditer(
            pattern, text
        ):

            add(
                match.group("name"),
                "ADVOCATE",
                match.group(0),
                "COURT_ADVOCATE_SIGNATURE"
            )

    return candidates
