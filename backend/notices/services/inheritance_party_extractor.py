"""
Conservative English and Kannada inheritance extraction.

Family relationships do not establish legal heir status.
All extracted identities and roles require manual review.
"""

import re
import unicodedata

from notices.services.party_name_extractor import (
    validate_person_name,
)


EN_HONORIFIC = (
    r"(?i:Mr|Mrs|Ms|Sri|Shri|Smt|Dr)"
    r"(?:\.\s*|\s+)"
)

EN_TOKEN = (
    r"(?:[A-Z](?:\.[A-Z])+\.?"
    r"|[A-Z][A-Za-z'-]*\.?)"
)

EN_NAME = (
    rf"{EN_TOKEN}(?:[ \t]+{EN_TOKEN}){{0,5}}"
)

KN_HONORIFIC = (
    r"(?:ಶ್ರೀಮತಿ|ಶ್ರೀ|ಕುಮಾರಿ)[.:\s]+"
)

KN_TOKEN = r"[\u0C80-\u0CFF.]+"

KN_NAME = (
    rf"{KN_TOKEN}(?:[ \t]+{KN_TOKEN}){{0,4}}"
)

KN_WILL_PATTERN = re.compile(
    r"(?<![\u0C80-\u0CFF])"
    r"(?:ಉಯಿಲು|ಉಯಿಲ್|ವಿಲ್|ಮರಣಶಾಸನ"
    r"|ಇಚ್ಛಾಪತ್ರ|ವಸಿಯತ್ತು|ವಸಿಯತ್)"
    r"(?![\u0C80-\u0CFF])"
)

EN_WILL_PATTERN = re.compile(
    r"\b(?:last will|will deed|testament"
    r"|testator|testatrix|probate"
    r"|bequeathed|bequest)\b",
    re.IGNORECASE,
)

EN_BOUNDARY = re.compile(
    r"^\s*(?:East|West|North|South)"
    r"\s+by\s*:",
    re.IGNORECASE,
)

KN_BOUNDARY = re.compile(
    r"^\s*(?:ಪೂರ್ವಕ್ಕೆ|ಪಶ್ಚಿಮಕ್ಕೆ"
    r"|ಉತ್ತರಕ್ಕೆ|ದಕ್ಷಿಣಕ್ಕೆ|ಚಕ್ಕುಬಂದಿ)"
)

EN_STOP_WORDS = {
    "aged", "years", "residing",
    "represented", "defendant",
    "respondent", "property",
    "owner", "legal", "heirs",
    "late", "deceased", "since",
    "dead", "and", "notice",
    "south", "north", "east", "west",
}

KN_STOP_TERMS = (
    "ವಿಳಾಸ", "ಆಸ್ತಿ", "ನಿವೇಶನ",
    "ಸಾಲಗಾರ", "ಜಾಮೀನುದಾರ",
    "ಮೃತರು", "ಮರಣಾನಂತರ",
    "ವಾರಸುದಾರ", "ಇವರು",
    "ಸುಮಾರು", "ವರ್ಷ",
    "ಪತ್ನಿ", "ಬಿನ್", "ಕೋಂ",
)


def normalize_text(text):

    text = unicodedata.normalize(
        "NFC", text or ""
    )

    return (
        text.replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )


def clean_name(name, language):

    name = re.sub(
        r"\s+", " ", name or ""
    ).strip(" ,:;()")

    if language == "en":

        name = re.sub(
            rf"^{EN_HONORIFIC}",
            "",
            name,
        )

        # A subsequent honorific indicates a
        # possible new person, not a name token.
        name = re.split(
            r"\s+(?i:Mr|Mrs|Ms|Sri|Shri|Smt|Dr)"
            r"(?:\.\s*|\s+)",
            name,
            maxsplit=1,
        )[0].rstrip(" .")

        tokens = []

        for token in name.split():

            if token.casefold().strip(".") in EN_STOP_WORDS:
                break

            tokens.append(token)

        name = " ".join(tokens)

    else:

        name = re.sub(
            rf"^{KN_HONORIFIC}",
            "",
            name,
        )

        name = re.split(
            r"\s+(?:ಬಿನ್|ಕೋಂ|ಪತ್ನಿ"
            r"|ಸುಮಾರು|ವಿಳಾಸ|ಇವರು)",
            name,
            maxsplit=1,
        )[0]

    return name.strip(" ,:;")


def is_valid_name(name, language):

    if not name:
        return False

    if not validate_person_name(
        name, language
    ):
        return False

    if language == "kn":

        if any(
            term in name
            for term in KN_STOP_TERMS
        ):
            return False

    return True


def extract_inheritance_parties(raw_text):

    text = normalize_text(raw_text)

    lines = text.splitlines()

    candidates = []

    def add(
        name,
        role,
        language,
        evidence,
        method,
        start_line,
        end_line=None,
        related_person=None,
        relationship=None,
    ):

        name = clean_name(
            name, language
        )

        if not is_valid_name(
            name, language
        ):
            return

        candidates.append({

            "name": name,

            "role": role,

            "language": language,

            "source_text": evidence,

            "extraction_method": method,

            "start_line": start_line,

            "end_line": (
                end_line or start_line
            ),

            "related_person": related_person,

            "relationship": relationship,

            "ownership_verified": False,

            "legal_entitlement_verified": False,

            "identity_merged": False,

            "requires_review": True,

            "verified": False,

            "approved_for_search": False,

            "eligible_for_alert": False,

        })

    # English explicit deceased person followed
    # by legal representation evidence.
    deceased_rep_pattern = re.compile(
        rf"{EN_HONORIFIC}"
        rf"(?P<name>{EN_NAME}?)"
        r"\s*,?\s*"
        r"(?i:since dead|deceased)"
        r"\s*,?\s*"
        r"(?i:represented by)"
        r"\s+(?i:his|her)\s+"
        r"(?i:LR['’]?s|legal representatives?)"
    )

    # Explicitly named legal heir.
    heir_pattern = re.compile(
        r"(?i:legal heirs?)\s*:\s*"
        rf"(?:{EN_HONORIFIC})?"
        rf"(?P<name>{EN_NAME})"
    )

    # Relationship references are not ownership.
    relative_pattern = re.compile(
        r"(?i:[SDW]\s*[/\.]\s*[oO]"
        r"|[SDW]lo|Dyo|0/0)"
        r"[\s.,]*"
        r"(?i:late)[\s.]+"
        rf"(?:{EN_HONORIFIC})?"
        rf"(?P<name>{EN_NAME}?)"
        r"(?=\s*[,;()]"
        r"|\s+(?i:aged|residing|is|and)"
        r"|$)"
    )

    # Explicit Kannada deceased relative.
    kn_relative_pattern = re.compile(
        r"(?:ಬಿನ್|ಕೋಂ)\s+"
        r"(?:ಲೇಟ್|ದಿವಂಗತ)\s+"
        rf"(?:{KN_HONORIFIC})?"
        rf"(?P<name>{KN_NAME}?)"
        r"(?=\s*[,;]"
        r"|\s+(?:ನಂ|ಸುಮಾರು|ವರ್ಷ)"
        r"|$)"
    )

    kn_heir_pattern = re.compile(
        r"(?:ಕಾನೂನುಬದ್ಧ ವಾರಸುದಾರರು?"
        r"|ಕಾನೂನು ವಾರಸುದಾರರು?)"
        r"\s*:\s*"
        rf"(?:{KN_HONORIFIC})?"
        rf"(?P<name>{KN_NAME}?)"
        r"(?=\s*[,;]|$)"
    )

    deceased_borrower_pattern = re.compile(
        r"\(ಮೃತ\s+ಸಾಲಗಾರರ\s+ಆಸ್ತಿ\)"
        r"\s*"
        rf"{KN_HONORIFIC}"
        rf"(?P<name>{KN_NAME}?)"
        r"\s+(?:ಲೇಟ್|ದಿವಂಗತ)"
    )

    for index, line in enumerate(lines):

        line_number = index + 1

        if (
            EN_BOUNDARY.search(line)
            or KN_BOUNDARY.search(line)
        ):
            continue

        # Join one continuation line only.
        window = line

        end_line = line_number

        if index + 1 < len(lines):

            next_line = lines[index + 1]

            if not re.match(
                r"^\s*\d+[.,)]",
                next_line,
            ):

                if not (
                    EN_BOUNDARY.search(next_line)
                    or KN_BOUNDARY.search(next_line)
                ):

                    window += " " + next_line
                    end_line += 1

        for match in deceased_rep_pattern.finditer(
            line
        ):

            add(
                match.group("name"),
                "DECEASED_PERSON",
                "en",
                line,
                "EXPLICIT_DECEASED_REPRESENTATION",
                line_number,
            )

        for match in relative_pattern.finditer(
            window
        ):

            # Prevent reprocessing a relationship
            # beginning only on the continuation line.
            if match.start() >= len(line):
                continue

            add(
                match.group("name"),
                "DECEASED_PERSON",
                "en",
                window,
                "DECEASED_RELATIVE_REFERENCE",
                line_number,
                end_line,
            )

        for match in heir_pattern.finditer(line):

            add(
                match.group("name"),
                "LEGAL_HEIR",
                "en",
                line,
                "EXPLICIT_LEGAL_HEIR_LABEL",
                line_number,
            )

        for match in kn_relative_pattern.finditer(
            line
        ):

            add(
                match.group("name"),
                "DECEASED_PERSON",
                "kn",
                line,
                "KANNADA_DECEASED_RELATIVE",
                line_number,
            )

        for match in kn_heir_pattern.finditer(line):

            add(
                match.group("name"),
                "LEGAL_HEIR",
                "kn",
                line,
                "KANNADA_EXPLICIT_HEIR_LABEL",
                line_number,
            )

        for match in deceased_borrower_pattern.finditer(
            line
        ):

            add(
                match.group("name"),
                "FINANCIAL_PARTY_UNSPECIFIED",
                "kn",
                line,
                "AMBIGUOUS_DECEASED_BORROWER_CONTEXT",
                line_number,
            )

            if candidates and (
                candidates[-1]["extraction_method"]
                == "AMBIGUOUS_DECEASED_BORROWER_CONTEXT"
                and candidates[-1]["start_line"]
                == line_number
            ):

                candidates[-1]["role_ambiguous"] = True

                candidates[-1]["role_warning"] = (
                    "Deceased borrower heading does "
                    "not establish this person's death."
                )

            # Extract the explicitly deceased spouse
            # mentioned in the same evidence.
            spouse = re.search(
                r"(?:ಲೇಟ್|ದಿವಂಗತ)\s+"
                rf"(?P<name>{KN_NAME}?)"
                r"\s+ಪತ್ನಿ",
                line,
            )

            if spouse:

                deceased_name = re.sub(
                    r"ನವರ$",
                    "",
                    spouse.group("name"),
                )

                add(
                    deceased_name,
                    "DECEASED_PERSON",
                    "kn",
                    line,
                    "EXPLICIT_DECEASED_SPOUSE_REFERENCE",
                    line_number,
                )

    # Preserve separate source occurrences.
    unique = {}

    for item in candidates:

        key = (
            item["name"].casefold(),
            item["role"],
            item["start_line"],
        )

        unique.setdefault(key, item)

    candidates = list(unique.values())

    return {

        "party_candidates": candidates,

        "candidate_count": len(candidates),

        "will_context_detected": bool(
            EN_WILL_PATTERN.search(text)
            or KN_WILL_PATTERN.search(text)
        ),

        "requires_review": True,

        "verified": False,

        "approved_for_search": False,

        "eligible_for_alert": False,

    }
