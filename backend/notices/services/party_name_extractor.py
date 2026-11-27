
import re
import unicodedata


# ==================================================
# NAME PATTERNS
# ==================================================

EN_HONORIFIC = (
    r"(?:Mrs|Mr|Ms|Shri|Sri|Smt|Dr)\.?\s+"
)

EN_TOKEN = (
    r"[A-Z][A-Za-z'-]*\.?"
)

EN_NAME = (
    rf"{EN_TOKEN}(?:\s+{EN_TOKEN}){{0,5}}"
)

KN_HONORIFIC = (
    r"(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ|ಡಾ\.?)\s+"
)

KN_TOKEN = r"[\u0C80-\u0CFF.]+"

KN_NAME = (
    rf"{KN_TOKEN}(?:\s+{KN_TOKEN}){{0,5}}"
)

EN_STOP_WORDS = {

    "property", "properties", "village",
    "layout", "road", "street", "floor",
    "office", "bank", "limited", "ltd",
    "company", "public", "notice",
    "document", "schedule", "district",
    "registrar", "court", "owner",
    "advocate", "resident", "residing",
    "of", "the", "in", "and", "have",
    "lost", "mob", "mobile", "no",
    "address", "hereby", "said",
    "authorized", "officer", "llp",
    "private", "plaintiff", "defendant",
    "applicant", "borrower", "holder"
}

KN_STOP_WORDS = {

    "ಸ್ವತ್ತು", "ಸ್ವತ್ತಿನ", "ಆಸ್ತಿ",
    "ಆಸ್ತಿಯ", "ನಿವೇಶನ", "ಸರ್ವೆ",
    "ಗ್ರಾಮ", "ಹೋಬಳಿ", "ತಾಲೂಕು",
    "ಜಿಲ್ಲೆ", "ವಿಳಾಸ", "ವಾಸ",
    "ನಂ", "ಸಂಖ್ಯೆ", "ರಸ್ತೆ",
    "ಬ್ಯಾಂಕ್", "ಶಾಖೆ", "ಕಂಪನಿ",
    "ಪ್ರಕಟಣೆ", "ಸಾರ್ವಜನಿಕರಿಗೆ",
    "ಬಿನ್", "ಕೋಂ", "ಲೇಟ್",
    "ಇವರು", "ಮತ್ತು", "ಸುಮಾರು",
    "ಮಾಲೀಕರು", "ವಕೀಲರು",
    "ಅರ್ಜಿದಾರರು", "ಸಾಲಗಾರರು",
    "ಹೆಸರು", "ನಾನು", "ನನ್ನ"
}



# ==================================================
# ORGANIZATION AND SENTENCE FILTERS
# ==================================================

EN_ORGANIZATION_PATTERN = re.compile(

    r"\b(?:associates|association|"
    r"partners|partnership|"
    r"law\s+firm|law\s+chambers|"
    r"legal\s+services|"
    r"corporation|enterprises|"
    r"industries|consultants|"
    r"developers|builders|"
    r"foundation|society|trust|"
    r"pvt|ltd|llp|limited)\b",

    re.IGNORECASE
)

KN_ORGANIZATION_TERMS = (

    "ಅಸೋಸಿಯೇಟ್ಸ್",
    "ಅಸೋಸಿಯೇಟ್ಸ",
    "ಅಸೋಸಿಯೇಟ್ಸ್‌",
    "ಅಸೋಸಿಯೇಷನ್",
    "ಅಸೋಸಿಯೇಶನ್",
    "ಕಂಪನಿ",
    "ಲಿಮಿಟೆಡ್",
    "ಬ್ಯಾಂಕ್",
    "ಎಂಟರ್‌ಪ್ರೈಸಸ್",
    "ಎಂಟರ್ಪ್ರೈಸಸ್",
    "ಡೆವಲಪರ್ಸ್",
    "ಬಿಲ್ಡರ್ಸ್",
    "ಸಂಸ್ಥೆ",
    "ಸಂಘ"
)

KN_SENTENCE_WORDS = {

    "ಅವರ",
    "ಅವರು",
    "ಅವರಿಗೆ",
    "ಅವರನ್ನು",
    "ಇವರ",
    "ಇವರು",
    "ಇವರಿಗೆ",
    "ಸ್ವಂತ",
    "ಸಂಪೂರ್ಣ",
    "ಸದರಿ",
    "ಮೂಲಕ",
    "ಯಾವುದೇ",
    "ಯಾರಿಂದಲೂ",
    "ತಿಳಿಸಿದ",
    "ತಿಳಿಸಿರುವ",
    "ಸಂಬಂಧಿಸಿದ",
    "ಪ್ರಜ್ಞಾವಸ್ಥೆಯಲ್ಲಿದ್ದಾಗ",
    "ಹೊಂದಿದ್ದರು",
    "ಇರುತ್ತಾರೆ",
    "ಇರುತ್ತೇನೆ",
    "ಮಾಡಿರುತ್ತಾರೆ",
    "ಕಳೆದುಕೊಂಡಿರುತ್ತೇನೆ"
}


def is_organization_name(name, language):

    normalized = unicodedata.normalize(
        "NFC",
        name or ""
    )

    normalized = normalized.replace(
        "\u200c", ""
    ).replace(
        "\u200d", ""
    )

    if language == "en":

        return bool(
            EN_ORGANIZATION_PATTERN.search(
                normalized
            )
        )

    if language == "kn":

        return any(

            term.replace(
                "\u200c", ""
            ).replace(
                "\u200d", ""
            ) in normalized

            for term in KN_ORGANIZATION_TERMS
        )

    return False


def is_sentence_fragment(name, language):

    if language != "kn":
        return False

    tokens = {

        token.strip(".,:;-()")

        for token in name.split()
    }

    if tokens & KN_SENTENCE_WORDS:
        return True

    return False


# ==================================================
# NORMALIZATION
# ==================================================

def normalize_party_text(text):

    text = unicodedata.normalize(
        "NFC",
        text or ""
    )

    text = text.replace(
        "\u200c", ""
    ).replace(
        "\u200d", ""
    )

    text = text.replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )

    return text


def clean_name(name):

    name = re.sub(
        r"\s+",
        " ",
        name or ""
    ).strip(" ,:;-()")

    name = re.sub(
        rf"^(?:{EN_HONORIFIC}|{KN_HONORIFIC})",
        "",
        name,
        flags=re.IGNORECASE
    )

    return name.strip()


# ==================================================
# PERSON NAME FILTERING
# ==================================================

def validate_person_name(name, language):

    name = clean_name(name)

    if is_organization_name(name, language):
        return False

    if is_sentence_fragment(name, language):
        return False

    if not 2 <= len(name) <= 80:
        return False

    if any(char.isdigit() for char in name):
        return False

    tokens = name.split()

    if len(tokens) > 6:
        return False

    normalized_tokens = {

        token.strip(".").casefold()

        for token in tokens
    }

    if language == "en":

        if not re.fullmatch(
            r"[A-Za-z .'-]+",
            name
        ):
            return False

        if normalized_tokens & EN_STOP_WORDS:
            return False

        if not any(
            len(token.strip(".")) >= 2
            for token in tokens
        ):
            return False

    elif language == "kn":

        if not re.fullmatch(
            r"[\u0C80-\u0CFF .]+",
            name
        ):
            return False

        if normalized_tokens & KN_STOP_WORDS:
            return False

        if not re.search(
            r"[\u0C85-\u0CB9]",
            name
        ):
            return False

    else:

        return False

    return True


# ==================================================
# CANDIDATE CONSTRUCTION
# ==================================================

def add_candidate(
    candidates,
    name,
    role,
    language,
    source_text,
    extraction_method
):

    name = clean_name(name)

    if not validate_person_name(
        name,
        language
    ):
        return

    candidates.append({

        "name": name,

        "role": role,

        "language": language,

        "source_text": source_text.strip(),

        "extraction_method": extraction_method,

        "verified": False,

        "requires_review": True
    })


# ==================================================
# ENGLISH PARTY EXTRACTION
# ==================================================

def extract_english_parties(text):

    candidates = []

    flat = re.sub(
        r"\s+",
        " ",
        text
    )

    role_patterns = [

        (
            "PREVIOUS_OWNER",
            r"\bprevious\s+owner\s+"
        ),

        (
            "POA_EXECUTANT",
            r"\bpower\s+of\s+attorney"
            r"\s+executed\s+by\s+"
        ),

        (
            "POA_HOLDER",
            r"\bpower\s+of\s+attorney"
            r"\s+holder\s*,?\s*"
        ),

        (
            "CONTACT_PERSON",
            r"\b(?:please\s+)?"
            r"(?:call|contact)\s+"
        ),

        (
            "OWNER",
            r"\b(?:absolute|lawful|registered|"
            r"property)\s+owner\s+"
        ),

        (
            "LEGAL_HEIR",
            r"\blegal\s+heir\s*[:\-]?\s*"
        ),

        (
            "APPLICANT",
            r"\bapplicant\s*[:\-]?\s*"
        ),

        (
            "PURCHASER",
            r"\b(?:purchaser|buyer)"
            r"\s*[:\-]?\s*"
        ),

        (
            "SELLER",
            r"\b(?:seller|vendor)"
            r"\s*[:\-]?\s*"
        ),

        (
            "PLAINTIFF",
            r"\bplaintiff\s*[:\-]?\s*"
        ),

        (
            "DEFENDANT",
            r"\bdefendant\s*[:\-]?\s*"
        ),

        (
            "BORROWER",
            r"\bborrower\s*[:\-]?\s*"
        )
    ]

    name_end = (

        r"(?=\s*(?:,|;|\(|$"

        r"|-\s*(?:Mob|Mobile)"

        r"|\s+(?:S/o|D/o|W/o|Wio|5/0"

        r"|resident|residing|aged|Mob"

        r"|Mobile|has|have|is|was"

        r"|and|of)\b"

        r"|\.\s+(?:I|\|)\s+))"
    )

    for role, prefix in role_patterns:

        pattern = (

            prefix

            + EN_HONORIFIC

            + rf"(?P<name>{EN_NAME}?)"

            + name_end
        )

        for match in re.finditer(
            pattern,
            flat,
            re.IGNORECASE
        ):

            add_candidate(

                candidates,

                match.group("name"),

                role,

                "en",

                match.group(0),

                "EXPLICIT_ROLE"
            )

    return candidates


# ==================================================
# KANNADA PARTY EXTRACTION
# ==================================================

def extract_kannada_parties(text):

    candidates = []

    flat = re.sub(
        r"\s+",
        " ",
        text
    )

    # First-person declaration.

    declarant_pattern = (

        r"ನಾನು\s*[,:\-]?\s*"

        rf"(?:{KN_HONORIFIC})?"

        rf"(?P<name>{KN_NAME}?)"

        r"(?=\s*(?:ಬಿನ್|ಕೋಂ|ವಾಸ|,))"
    )

    for match in re.finditer(
        declarant_pattern,
        flat
    ):

        add_candidate(

            candidates,

            match.group("name"),

            "DECLARANT",

            "kn",

            match.group(0),

            "FIRST_PERSON_DECLARATION"
        )

    # Explicit father / testator context.

    father_pattern = (

        r"ನನ್ನ\s+ತಂದೆಯವರಾದ\s+"

        rf"(?:{KN_HONORIFIC})?"

        rf"(?P<name>{KN_NAME}?)"

        r"(?=\s*(?:ಬಿನ್|ಕೋಂ|ವಾಸ|,))"
    )

    for match in re.finditer(
        father_pattern,
        flat
    ):

        context = flat[
            match.start():match.end() + 350
        ]

        role = (

            "TESTATOR"

            if re.search(
                r"ಬರೆದುಕೊಟ್ಟಿದ್ದ\s+ಉಯಿಲು",
                context
            )

            else "FATHER"
        )

        add_candidate(

            candidates,

            match.group("name"),

            role,

            "kn",

            context,

            "RELATIONSHIP_CONTEXT"
        )

    # Explicit Kannada legal role labels.

    role_patterns = [

        ("OWNER", r"ಮಾಲೀಕರು?"),

        ("LEGAL_HEIR", r"ವಾರಸುದಾರರು?"),

        ("APPLICANT", r"ಅರ್ಜಿದಾರರು?"),

        ("PURCHASER", r"ಖರೀದಿದಾರರು?"),

        ("SELLER", r"ಮಾರಾಟಗಾರರು?"),

        ("PLAINTIFF", r"ವಾದಿ"),

        ("DEFENDANT", r"ಪ್ರತಿವಾದಿ"),

        ("BORROWER", r"ಸಾಲಗಾರರು?")
    ]

    for role, label in role_patterns:

        pattern = (

            label

            + r"\s*[:\-]\s*"

            + rf"(?:{KN_HONORIFIC})?"

            + rf"(?P<name>{KN_NAME}?)"

            + r"(?=\s*(?:ಬಿನ್|ಕೋಂ|ವಾಸ|,|;|$))"
        )

        for match in re.finditer(
            pattern,
            flat
        ):

            add_candidate(

                candidates,

                match.group("name"),

                role,

                "kn",

                match.group(0),

                "EXPLICIT_ROLE"
            )

    # Borrower list: restrict extraction to the
    # section between borrower and account labels.

    borrower_section = re.search(

        r"ಸಾಲಗಾರರ\s+ಹೆಸರು\s+ಮತ್ತು\s+ವಿಳಾಸ"
        r"\s*[:\-]?\s*(.*?)"
        r"(?=ಖಾತೆ\s*\.?\s*ನಂ|"
        r"ಬರಬೇಕಾದ\s+ಬಾಕಿ|$)",

        flat
    )

    if borrower_section:

        section = borrower_section.group(1)

        pattern = (

            r"(?:^|[0-9]\s*[.)]|"
            r"\([ಎಬಿಸಿ]+\)\.?)\s*"

            + KN_HONORIFIC

            + rf"(?P<name>{KN_NAME}?)"

            + r"(?=\s*(?:ಬಿನ್|ಕೋಂ|"
              r"\(ಸಹ\s+ಅರ್ಜಿದಾರರು\)|,))"
        )

        for match in re.finditer(
            pattern,
            section
        ):

            following = section[
                match.end():match.end() + 40
            ]

            role = (

                "CO_APPLICANT"

                if re.match(
                    r"\s*\(ಸಹ\s+ಅರ್ಜಿದಾರರು\)",
                    following
                )

                else "BORROWER"
            )

            add_candidate(

                candidates,

                match.group("name"),

                role,

                "kn",

                match.group(0) + following,

                "BORROWER_LIST"
            )

    return candidates


# ==================================================
# ADVOCATE EXTRACTION
# ==================================================

def extract_advocate_candidates(text):

    candidates = []

    flat = re.sub(
        r"\s+",
        " ",
        text
    )

    english_patterns = [

        # Name, Advocate / Name (Advocate)

        (
            rf"^[ \t]*(?:{EN_HONORIFIC})?"
            rf"(?P<name>{EN_NAME})"
            r"[ \t]*(?:,|\()\s*Advocate\b",
            text,
            re.MULTILINE | re.IGNORECASE
        ),

        # Advocate Mr. Name

        (
            r"\bAdvocate\s+"
            + EN_HONORIFIC
            + rf"(?P<name>{EN_NAME}?)"
            + r"(?=\s*(?:,|;|$|"
              r"\s+(?:Mob|Mobile|Office)\b))",
            flat,
            re.IGNORECASE
        ),

        # Advocate: Name

        (
            r"^[ \t]*Advocate\s*[:\-]\s*"
            rf"(?:{EN_HONORIFIC})?"
            rf"(?P<name>{EN_NAME})[ \t]*$",
            text,
            re.MULTILINE | re.IGNORECASE
        )
    ]

    for pattern, source, flags in english_patterns:

        for match in re.finditer(
            pattern,
            source,
            flags
        ):

            add_candidate(

                candidates,

                match.group("name"),

                "ADVOCATE",

                "en",

                match.group(0),

                "ADVOCATE_PATTERN"
            )

    kannada_patterns = [

        (
            r"^[ \t]*(?:ವಕೀಲರು|ನ್ಯಾಯವಾದಿಗಳು)"
            r"\s*[:\-]\s*"
            rf"(?:{KN_HONORIFIC})?"
            rf"(?P<name>{KN_NAME})[ \t]*$"
        ),

        (
            rf"^[ \t]*(?:{KN_HONORIFIC})?"
            rf"(?P<name>{KN_NAME})"
            r"\s*,\s*(?:ವಕೀಲರು|ನ್ಯಾಯವಾದಿಗಳು)"
        )
    ]

    for pattern in kannada_patterns:

        for match in re.finditer(
            pattern,
            text,
            re.MULTILINE
        ):

            add_candidate(

                candidates,

                match.group("name"),

                "ADVOCATE",

                "kn",

                match.group(0),

                "ADVOCATE_PATTERN"
            )

    return candidates


# ==================================================
# DEDUPLICATION
# ==================================================

def deduplicate_party_candidates(candidates):

    from notices.services.party_variant_grouper import (
        extract_party_entry_numbers
    )

    unique = {}

    for candidate in candidates:

        entry_numbers = sorted(
            extract_party_entry_numbers(candidate)
        )

        court_entry_key = (
            tuple(entry_numbers)
            if entry_numbers
            else None
        )

        key = (

            candidate["name"].casefold(),

            candidate["role"],

            candidate["language"],

            court_entry_key
        )

        if key not in unique:

            item = dict(candidate)

            item["evidence"] = [
                candidate["source_text"]
            ]

            item["court_entry_numbers"] = (
                entry_numbers
            )

            item["identity_merged"] = False

            item["verified"] = False

            item["requires_review"] = True

            unique[key] = item

        else:

            evidence = unique[key]["evidence"]

            if candidate["source_text"] not in evidence:

                evidence.append(
                    candidate["source_text"]
                )

    results = list(unique.values())

    identity_buckets = {}

    for item in results:

        identity_key = (

            item["name"].casefold(),

            item["role"],

            item["language"]
        )

        identity_buckets.setdefault(
            identity_key, []
        ).append(item)

    for items in identity_buckets.values():

        all_entries = set()

        for item in items:

            all_entries.update(
                item["court_entry_numbers"]
            )

        conflict = len(all_entries) > 1

        for item in items:

            item["identity_conflict"] = conflict

            item["identity_merged"] = False

    return results


# ==================================================
# COMMON MULTILINGUAL ENTRY POINT
# ==================================================



# ==================================================
# EXTENDED PERSON NAME PATTERNS
# ==================================================

EXT_EN_HONORIFIC = (
    r"(?:Mrs|Mr|Ms|Shri|Sri|Smt|Dr)"
    r"(?:\.\s*|\s+)"
)

EXT_EN_TOKEN = (
    r"(?:[A-Z](?:\.[A-Z])+\.?"
    r"|[A-Z][A-Za-z'-]*\.?)"
)

EXT_EN_NAME = (
    rf"{EXT_EN_TOKEN}"
    rf"(?:[ \t]+{EXT_EN_TOKEN}){{0,5}}"
)

EXT_KN_HONORIFIC = (
    r"(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ|ಡಾ)"
    r"\.?\s+"
)

EXT_KN_NAME = (
    r"[\u0C80-\u0CFF.]+"
    r"(?:[ \t]+[\u0C80-\u0CFF.]+){0,4}"
)


# ==================================================
# EXTENDED ENGLISH CLIENT AND OWNER EXTRACTION
# ==================================================

def extract_extended_english_parties(text):

    candidates = []

    flat = re.sub(r"\s+", " ", text)

    name_end = (
        r"(?=\s*(?:[,;()]|$)"
        r"|\s+(?:S/o|D/o|W/o|"
        r"aged|residing|resident|"
        r"has|have|is|was|"
        r"intends|intending|"
        r"being|represented|"
        r"hereby|and)\b)"
    )

    client_pattern = (

        r"\b(?:my|our)\s+client"

        r"\s*[,:\-]?\s*"

        rf"(?:{EXT_EN_HONORIFIC})?"

        rf"(?P<name>{EXT_EN_NAME}?)"

        + name_end
    )

    owner_pattern = (

        r"\b(?:absolute|lawful|registered|"
        r"original|property)\s+owner"

        r"\s*[,:\-]?\s*"

        rf"(?:{EXT_EN_HONORIFIC})?"

        rf"(?P<name>{EXT_EN_NAME}?)"

        + name_end
    )

    reverse_owner_pattern = (

        EXT_EN_HONORIFIC

        + rf"(?P<name>{EXT_EN_NAME}?)"

        + r"\s*,?\s*"

        r"(?:being|is|was)\s+"

        r"(?:the\s+)?"

        r"(?:absolute|lawful|registered|"
        r"original|property)\s+owner\b"
    )

    patterns = [

        ("CLIENT", client_pattern),

        ("OWNER", owner_pattern),

        ("OWNER", reverse_owner_pattern)
    ]

    for role, pattern in patterns:

        for match in re.finditer(
            pattern,
            flat
        ):

            add_candidate(

                candidates,

                match.group("name"),

                role,

                "en",

                match.group(0),

                "EXTENDED_ENGLISH_ROLE"
            )

    return candidates


# ==================================================
# EXTENDED KANNADA CLIENT AND OWNER EXTRACTION
# ==================================================

def extract_extended_kannada_parties(text):

    candidates = []

    flat = re.sub(r"\s+", " ", text)

    name_end = (

        r"(?=\s*(?:[,;()]|$)"

        r"|\s+(?:ಬಿನ್|ಕೋಂ|ವಾಸ|"
        r"ಇವರು|ಇವರ|ಅವರು|ಅವರ|"
        r"ಸುಮಾರು|ಮತ್ತು|ರವರು|"
        r"ರವರೆಂದು|ಅವರಿಗೆ))"
    )

    role_patterns = [

        (
            "CLIENT",

            r"(?:ನನ್ನ|ನಮ್ಮ)?\s*"
            r"ಕಕ್ಷಿದಾರ(?:ರಾದ|ರಾಗಿರುವ|ರು)"
        ),

        (
            "OWNER",

            r"(?:ಮೂಲ\s+)?"
            r"(?:ಮಾಲೀಕರಾದ|ಮಾಲಕರಾದ|"
            r"ಮಾಲೀಕರಾಗಿರುವ|ಮಾಲಕರಾಗಿರುವ)"
        )
    ]

    for role, label in role_patterns:

        pattern = (

            label

            + r"\s*[,:\-]?\s*"

            + rf"(?:{EXT_KN_HONORIFIC})?"

            + rf"(?P<name>{EXT_KN_NAME}?)"

            + name_end
        )

        for match in re.finditer(
            pattern,
            flat
        ):

            add_candidate(

                candidates,

                match.group("name"),

                role,

                "kn",

                match.group(0),

                "EXTENDED_KANNADA_ROLE"
            )

    return candidates


# ==================================================
# EXTENDED ADVOCATE SIGNATURE EXTRACTION
# ==================================================

def extract_extended_advocates(text):

    candidates = []

    english_patterns = [

        # Sd/- Leelaraju, Advocate

        (
            r"^[ \t]*(?:Sd|SD|sd)"
            r"\s*/?\s*-?\s*"

            rf"(?:{EXT_EN_HONORIFIC})?"

            rf"(?P<name>{EXT_EN_NAME}?)"

            r"[ \t]*[,()]?[ \t]*"

            r"Advocate\b"
        ),

        # Name followed by Advocate on next line.

        (
            rf"^[ \t]*(?:{EXT_EN_HONORIFIC})?"

            rf"(?P<name>{EXT_EN_NAME})"

            r"[ \t]*\n[ \t]*"

            r"Advocate\b"
        ),

        # Advocate: Name

        (
            r"^[ \t]*Advocate[ \t]*[:\-][ \t]*"

            rf"(?:{EXT_EN_HONORIFIC})?"

            rf"(?P<name>{EXT_EN_NAME})"

            r"(?=[ \t]*(?:,|$))"
        )
    ]

    for pattern in english_patterns:

        for match in re.finditer(
            pattern,
            text,
            re.MULTILINE
        ):

            add_candidate(

                candidates,

                match.group("name"),

                "ADVOCATE",

                "en",

                match.group(0),

                "EXTENDED_ADVOCATE_SIGNATURE"
            )

    kannada_patterns = [

        # Kannada name followed by advocate role.

        (
            r"^[ \t]*"

            r"(?:ಸಹಿ\s*[:/\-]?\s*)?"

            rf"(?:{EXT_KN_HONORIFIC})?"

            rf"(?P<name>{EXT_KN_NAME}?)"

            r"[ \t]*,?[ \t]*"

            r"(?:ವಕೀಲರು|ನ್ಯಾಯವಾದಿಗಳು)"

            r"(?=[ \t]*(?:[,.;:]|$))"
        ),

        # Kannada advocate on next line.

        (
            rf"^[ \t]*(?:{EXT_KN_HONORIFIC})?"

            rf"(?P<name>{EXT_KN_NAME})"

            r"[ \t]*\n[ \t]*"

            r"(?:ವಕೀಲರು|ನ್ಯಾಯವಾದಿಗಳು)"

            r"(?=[ \t]*(?:[,.;:]|$))"
        )
    ]

    for pattern in kannada_patterns:

        for match in re.finditer(
            pattern,
            text,
            re.MULTILINE
        ):

            add_candidate(

                candidates,

                match.group("name"),

                "ADVOCATE",

                "kn",

                match.group(0),

                "EXTENDED_ADVOCATE_SIGNATURE"
            )

    return candidates




# ==================================================
# OWNERSHIP AND TRANSACTION PARTY EXTRACTION
# ==================================================

def extract_transaction_parties(text):

    candidates = []

    flat = re.sub(r"\s+", " ", text)

    honorific = (
        r"(?i:Mrs|Mr|Ms|Shri|Sri|Smt|Dr)"
        r"(?:\.\s*|\s+)"
    )

    name = EXT_EN_NAME

    relationship = (
        r"(?i:S/o|D/o|W/o|"
        r"son of|daughter of|wife of)"
    )

    name_end = (
        rf"(?=\s*(?:[,;()]|$)"
        rf"|\s+{relationship}"
        r"|\s+(?i:and|residing|"
        r"resident|being|is|was|"
        r"intends|intending)\b)"
    )

    def add_english(match, role, method):

        add_candidate(
            candidates,
            match.group("name"),
            role,
            "en",
            match.group(0),
            method
        )

    # --------------------------------------------------
    # Explicit owner with an intervening relationship
    # --------------------------------------------------

    owner_statement = (

        honorific

        + rf"(?P<name>{name}?)"

        + r"\s*,\s*"

        + relationship

        + r"\.?\s*"

        + r"(?:(?i:Late)\s+)?"

        + rf"(?:{honorific})?"

        + rf"{name}?"

        + r"\s*,?\s*"

        + r"(?i:is|was|being)\s+"

        + r"(?i:the)\s+"

        + r"(?i:absolute|sole|lawful|registered)"

        + r"\s+(?i:owner)\b"
    )

    for match in re.finditer(
        owner_statement,
        flat
    ):

        add_english(
            match,
            "OWNER",
            "EXPLICIT_OWNER_RELATIONSHIP"
        )

    # --------------------------------------------------
    # Property owner following a purchase statement
    # --------------------------------------------------

    purchase_owner = (

        r"(?i:\bfrom\s+(?:its|the)\s+owner)"

        + r"\s+"

        + honorific

        + rf"(?P<name>{name}?)"

        + name_end
    )

    for match in re.finditer(
        purchase_owner,
        flat
    ):

        add_english(
            match,
            "OWNER",
            "PURCHASE_FROM_OWNER"
        )

    # --------------------------------------------------
    # Explicit vendor
    # --------------------------------------------------

    vendor_pattern = (

        r"(?i:\bfrom\s+(?:the\s+)?vendors?)"

        + r"\s+"

        + rf"(?:{honorific}|Sn\.\s*)"

        + rf"(?P<name>{name}?)"

        + name_end
    )

    for match in re.finditer(
        vendor_pattern,
        flat
    ):

        add_english(
            match,
            "VENDOR",
            "EXPLICIT_VENDOR"
        )

    # --------------------------------------------------
    # Multiple owners after an explicit owner label
    # --------------------------------------------------

    owner_list_start = re.compile(

        r"(?i:\b(?:from\s+its\s+owners|"
        r"owners\s+namely|"
        r"joint\s+owners\s+namely))"

        r"\s*[:\-]?\s*"
    )

    owner_item = re.compile(

        rf"{honorific}"

        rf"(?P<name>{name}?)"

        + name_end
    )

    separator = re.compile(
        r"\s*(?:,\s*(?:and\s+)?|"
        r"\band\b\s+|&\s*)",
        re.IGNORECASE
    )

    for start in owner_list_start.finditer(flat):

        position = start.end()

        # Read only consecutive explicitly named owners.
        # Stop when relationship or narrative text begins.

        for _ in range(10):

            match = owner_item.match(
                flat,
                position
            )

            if not match:
                break

            add_candidate(
                candidates,
                match.group("name"),
                "OWNER",
                "en",
                flat[start.start():match.end()],
                "EXPLICIT_MULTIPLE_OWNERS"
            )

            next_separator = separator.match(
                flat,
                match.end()
            )

            if not next_separator:
                break

            position = next_separator.end()

    # --------------------------------------------------
    # Numbered owners/sellers section
    # --------------------------------------------------

    section_pattern = re.compile(

        r"(?im)^[ \t]*OWNERS\s*/\s*SELLERS"

        r"[ \t]*:[ \t]*"
    )

    section_stop = re.compile(

        r"(?im)^[ \t]*(?:"
        r"INTENDING\s+BUYER|"
        r"BUYER|BORROWER|"
        r"PURCHASER|SCHEDULE|"
        r"ADVOCATE|CONTACT)"

        r"\b"
    )

    numbered_owner = re.compile(

        r"(?m)^[ \t]*\d{1,2}"

        r"[.)][ \t]*"

        + honorific

        + rf"(?P<name>{name}?)"

        + name_end
    )

    for section in section_pattern.finditer(text):

        block = text[
            section.end():section.end() + 800
        ]

        stop = section_stop.search(block)

        if stop:
            block = block[:stop.start()]

        for match in numbered_owner.finditer(block):

            for role in ("OWNER", "SELLER"):

                add_candidate(
                    candidates,
                    match.group("name"),
                    role,
                    "en",
                    section.group(0) + "\n"
                    + match.group(0),
                    "NUMBERED_OWNER_SELLER_SECTION"
                )

    # --------------------------------------------------
    # Intending buyer before an explicit role label
    # --------------------------------------------------

    buyer_pattern = (

        honorific

        + rf"(?P<name>{name}?)"

        + r"\s*,\s*"

        + r"(?i:the)\s+"

        + r"(?i:intending\s+buyer)"

        + r"(?:\s*/\s*(?i:borrower))?"

        + r"\b"
    )

    for match in re.finditer(
        buyer_pattern,
        flat
    ):

        add_english(
            match,
            "INTENDING_BUYER",
            "EXPLICIT_INTENDING_BUYER"
        )

    # --------------------------------------------------
    # Attorney appointment with relationship
    # --------------------------------------------------

    attorney_pattern = (

        r"(?i:\bappointed\s+to)\s+"

        + honorific

        + rf"(?P<name>{name}?)"

        + r"\s+"

        + relationship

        + r"\.?\s*"

        + rf"(?:{honorific})?"

        + rf"{name}?"

        + r"\s*,\s*"

        + r"(?i:as\s+an?\s+attorney)\b"
    )

    for match in re.finditer(
        attorney_pattern,
        flat
    ):

        add_english(
            match,
            "ATTORNEY",
            "EXPLICIT_ATTORNEY_APPOINTMENT"
        )

    # --------------------------------------------------
    # Kannada original owner with purchase context
    # --------------------------------------------------

    kannada_owner = (

        r"(?:ಮೂಲ\s+)?"

        r"(?:ಮಾಲಕರಾದ|ಮಾಲೀಕರಾದ)"

        r"\s*[:,-]?\s*"

        r"(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ)"

        r"\.?\s*"

        rf"(?P<name>{EXT_KN_NAME}?)"

        r"\s+ರವರಿಂದ\s+ಖರೀದಿಸಲು"
    )

    for match in re.finditer(
        kannada_owner,
        flat
    ):

        add_candidate(
            candidates,
            match.group("name"),
            "OWNER",
            "kn",
            match.group(0),
            "KANNADA_PURCHASE_FROM_OWNER"
        )

    return candidates


def extract_party_candidates(raw_text):

    text = normalize_party_text(raw_text)

    candidates = []

    candidates.extend(
        extract_english_parties(text)
    )

    candidates.extend(
        extract_kannada_parties(text)
    )

    candidates.extend(
        extract_advocate_candidates(text)
    )

    candidates.extend(
        extract_extended_english_parties(text)
    )

    candidates.extend(
        extract_extended_kannada_parties(text)
    )

    candidates.extend(
        extract_extended_advocates(text)
    )

    candidates.extend(
        extract_transaction_parties(text)
    )

    from notices.services.court_party_extractor import (
        extract_court_party_candidates
    )

    for item in extract_court_party_candidates(raw_text):

        add_candidate(
            candidates,
            item["name"],
            item["role"],
            item["language"],
            item["source_text"],
            item["extraction_method"]
        )

    candidates = deduplicate_party_candidates(
        candidates
    )

    return {

        "party_candidates": candidates,

        "candidate_count": len(candidates),

        "roles_found": sorted({

            candidate["role"]

            for candidate in candidates
        }),

        "requires_review": True,

        "verified": False,

        "approved_for_search": False,

        "eligible_for_alert": False
    }
