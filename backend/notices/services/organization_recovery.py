"""
Conservative recovery of OCR-corrupted organization names.

Recovered names are suggestions for manual review,
not verified legal identities.
"""

import re
import unicodedata

from notices.services.organization_ocr_validator import (
    organization_safety_flags,
)


APTUS_SUGGESTED_NAME = (
    "Aptus Value Housing Finance India Limited"
)


APTUS_PREFIX = (
    r"(?:ಆಪ್ಟಸ್|ಅಪ್ಟಸ್|ಆಪ್ಟುಸ್|"
    r"ಅಪ್ಟುಸ್|ಅಪ್ಪಸ್|ಅಪಸ್)"
)


APTUS_FULL_PATTERN = re.compile(

    rf"(?<![\u0C80-\u0CFF])"

    rf"{APTUS_PREFIX}\s+"

    r"ವ್ಯಾಲ್ಯೂ\s+"

    r"(?:ಹೌಸಿಂಗ್|ಕೌಸಿಂಗ್|ಹಾಸಿಂಗ್|PLOT)\s+"

    r"ಫೈನಾನ್ಸ್\s+"

    r"ಇಂಡಿಯಾ\s+"

    r"ಲಿಮಿಟೆಡ್",

    re.IGNORECASE,

)


SECURED_CATEGORIES = {

    "SECURED_PROPERTY_DEMAND",

    "SECURED_PROPERTY_POSSESSION",

    "SECURED_PROPERTY_AUCTION",

    "SECURED_PROPERTY_OTHER",

}


LEGAL_CONTEXT = re.compile(

    r"ಸ್ವಾಧೀನ|ಸರ್ಪೇಸಿ|ಸರ್ಫೇಸಿ|"

    r"ಭದ್ರತಾ ಹಿತಾಸಕ್ತಿ|ಅಡಮಾನ|"

    r"possession notice|sarfaesi|"

    r"secured asset|"

    r"13\s*\(\s*[24]\s*\)",

    re.IGNORECASE,

)


def normalize_organization_text(text):

    text = unicodedata.normalize(
        "NFC",
        text or "",
    )

    text = re.sub(
        r"[\u200b\u200c\u200d\ufeff]",
        "",
        text,
    )

    return text


def recover_organization_candidates(
    raw_text,
    notice_category="",
):

    result = {

        "applicable": (
            notice_category in SECURED_CATEGORIES
        ),

        "organization_candidates": [],

        "organization_count": 0,

        **organization_safety_flags(),

    }

    if not result["applicable"]:

        return result

    normalized = normalize_organization_text(
        raw_text
    )

    if not LEGAL_CONTEXT.search(normalized):

        return result

    evidence = []
    variants = []

    for line_number, original_line in enumerate(
        (raw_text or "").splitlines(),
        start=1,
    ):

        normalized_line = (
            normalize_organization_text(
                original_line
            )
        )

        for match in APTUS_FULL_PATTERN.finditer(
            normalized_line
        ):

            raw_name = match.group(0)

            if raw_name not in variants:

                variants.append(raw_name)

            evidence.append({

                "line_number": line_number,

                "source_text": original_line,

                "normalized_matched_name": raw_name,

                "extraction_method": (
                    "APTUS_KANNADA_OCR_RECOVERY"
                ),

            })

    if not evidence:

        return result

    candidate = {

        "name": variants[0],

        "suggested_name": APTUS_SUGGESTED_NAME,

        "name_variants": variants,

        "role": "SECURED_CREDITOR_CANDIDATE",

        "entity_kind": "ORGANIZATION",

        "language": "kn",

        "source_text": evidence[0]["source_text"],

        "evidence": evidence,

        "extraction_method": (
            "APTUS_KANNADA_OCR_RECOVERY"
        ),

        "ocr_correction_applied": True,

        "name_uncertain": True,

        "confidence": "LOW",

        **organization_safety_flags(),

    }

    result["organization_candidates"].append(
        candidate
    )

    result["organization_count"] = 1

    return result
