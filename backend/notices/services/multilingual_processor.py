
import re

from copy import deepcopy

from notices.services.detector import detect_notice

from notices.services.field_extractor import (
    extract_notice_fields
)

from notices.services.kannada_detector import (
    detect_kannada_notice
)

from notices.services.kannada_field_extractor import (
    extract_kannada_fields
)

from notices.services.ocr_validator import (
    validate_extracted_fields
)

from notices.services.classification_policy import (
    apply_classification_policy
)

from notices.services.location_ocr_validator import (
    validate_property_locations
)

from notices.services.unified_party_extractor import (
    extract_unified_parties,
)


# ==================================================
# LANGUAGE IDENTIFICATION
# ==================================================

def identify_language(text):

    text = text or ""

    kannada_count = len(
        re.findall(
            r"[\u0C85-\u0CB9]",
            text
        )
    )

    english_count = len(
        re.findall(
            r"[A-Za-z]",
            text
        )
    )

    total = kannada_count + english_count

    if total == 0:

        return {
            "language": "unknown",
            "kannada_characters": 0,
            "english_characters": 0,
            "kannada_ratio": 0.0
        }

    kannada_ratio = kannada_count / total

    if kannada_count == 0:

        language = "en"

    elif english_count == 0:

        language = "kn"

    elif kannada_ratio >= 0.85:

        language = "kn"

    else:

        language = "mixed"

    return {

        "language": language,

        "kannada_characters": kannada_count,

        "english_characters": english_count,

        "kannada_ratio": round(
            kannada_ratio,
            4
        )
    }


# ==================================================
# ENGLISH PROCESSING
# ==================================================

def process_english_text(text):

    detection = deepcopy(
        detect_notice(text)
    )

    accepted = detection.get(
        "is_notice",
        False
    )

    detection["decision"] = (
        "ACCEPT" if accepted else "REJECT"
    )

    detection["language"] = "en"

    detection["requires_review"] = accepted

    fields = (

        extract_notice_fields(text)

        if accepted else None
    )

    return detection, fields


# ==================================================
# KANNADA PROCESSING
# ==================================================

def process_kannada_text(text):

    detection = detect_kannada_notice(
        text
    )

    decision = detection.get("decision")

    fields = (

        extract_kannada_fields(text)

        if decision in ("ACCEPT", "REVIEW")

        else None
    )

    return detection, fields


# ==================================================
# EXTRACT FIELDS FOR RECOVERED CANDIDATES
# ==================================================

def extract_recovered_fields(
    text,
    language_info
):

    language = language_info["language"]

    if language == "en":

        fields = extract_notice_fields(
            text
        )

    elif language in ("kn", "mixed"):

        if language_info["kannada_ratio"] >= 0.5:

            fields = extract_kannada_fields(
                text
            )

        else:

            fields = extract_notice_fields(
                text
            )

    else:

        return None

    if fields is not None:

        fields["requires_review"] = True

        reasons = fields.get(
            "review_reasons"
        ) or []

        fields["review_reasons"] = list(
            dict.fromkeys(

                reasons

                + [
                    "Fields extracted from a "
                    "recovered legal candidate"
                ]
            )
        )

    return fields


# ==================================================
# BASE LANGUAGE ROUTING
# ==================================================

def route_text(text):

    language_info = identify_language(text)

    language = language_info["language"]

    if language == "unknown":

        detection = {

            "is_notice": False,

            "notice_type": None,

            "decision": "REJECT",

            "confidence": "LOW",

            "score": 0,

            "reason": "No supported script detected",

            "requires_review": False
        }

        fields = None

    elif language == "en":

        detection, fields = (
            process_english_text(text)
        )

    elif language == "kn":

        detection, fields = (
            process_kannada_text(text)
        )

    else:

        kn_detection, kn_fields = (
            process_kannada_text(text)
        )

        en_detection, en_fields = (
            process_english_text(text)
        )

        kn_decision = kn_detection["decision"]

        en_decision = en_detection["decision"]

        if kn_decision == "ACCEPT":

            detection = kn_detection

            fields = kn_fields

        elif kn_decision == "REVIEW":

            detection = kn_detection

            fields = kn_fields

        elif en_decision == "ACCEPT":

            detection = deepcopy(
                en_detection
            )

            detection["decision"] = "REVIEW"

            detection["is_notice"] = False

            detection["confidence"] = "LOW"

            detection["reason"] = (
                "English and Kannada "
                "classifiers disagree"
            )

            detection["requires_review"] = True

            fields = en_fields

        else:

            detection = kn_detection

            fields = None

        detection["language"] = "mixed"

    # ----------------------------------------------
    # Preserve original classifier output.
    # ----------------------------------------------

    base_detection = deepcopy(
        detection
    )

    # ----------------------------------------------
    # Apply common legal classification policy.
    # ----------------------------------------------

    detection = apply_classification_policy(

        text,

        detection
    )

    detection["language"] = language

    # Recover fields for candidates previously
    # rejected by the ordinary classifiers.

    if (

        detection["retain_candidate"]

        and fields is None
    ):

        fields = extract_recovered_fields(

            text,

            language_info
        )

    return {

        "language_info": language_info,

        "base_detection": base_detection,

        "detection": detection,

        "fields": fields
    }


# ==================================================
# BUILD CONSOLIDATED REVIEW FIELDS
# ==================================================

def build_review_fields(
    fields,
    validation
):

    if fields is None:
        return None

    safe_fields = deepcopy(fields)

    safe_fields["requires_review"] = True
    safe_fields["verified"] = False

    # Preserve evidence separately.
    # Block fields with invalid subject evidence,
    # including when secondary OCR is unavailable.

    blocked_fields = {

        item["field"]

        for item in safe_fields.get(
            "invalid_subject_identifiers", []
        )

        if item.get("field")
    }

    if validation is not None:

        blocked_fields.update(

            validation.get(
                "conflicting_fields", []
            )

            + validation.get(
                "single_source_fields", []
            )

            + validation.get(
                "multiple_candidate_fields", []
            )

            + validation.get(
                "invalid_fields", []
            )
        )

        # Populate assessment number only when
        # both sources agree on one candidate.

        assessment = validation.get(
            "validations", {}
        ).get("assessment_numbers", {})

        if assessment.get(
            "status"
        ) == "CONSISTENT_UNVERIFIED":

            selected = assessment.get(
                "selected_value"
            )

            safe_fields["assessment_number"] = (
                selected
            )

            safe_fields["assessment_numbers"] = (
                [selected] if selected else []
            )

    # Assessment evidence alone is insufficient.

    else:

        safe_fields["assessment_number"] = None
        safe_fields["assessment_numbers"] = []

    for field in blocked_fields:

        if field.endswith("_numbers"):

            if field in safe_fields:

                safe_fields[field] = []

            scalar_field = field[:-1]

            if scalar_field in safe_fields:

                safe_fields[scalar_field] = None

        elif field == "property_area":

            safe_fields["property_area"] = None

            safe_fields["property_area_unit"] = None

        elif field == "response_deadline":

            safe_fields["response_deadline"] = None

            safe_fields["response_deadline_unit"] = None

    safe_fields["blocked_identifier_fields"] = (
        sorted(blocked_fields)
    )

    existing_reasons = (
        safe_fields.get("review_reasons") or []
    )

    validation_reasons = (

        validation.get("review_reasons", [])

        if validation is not None

        else []
    )

    safe_fields["review_reasons"] = list(

        dict.fromkeys(

            existing_reasons
            + validation_reasons
        )
    )

    return safe_fields


# ==================================================
# MAIN MULTILINGUAL PROCESSOR
# ==================================================

def process_multilingual_notice(

    primary_text,

    secondary_text=None,

    primary_ocr_language=None,

    secondary_ocr_language=None
):

    primary_text = primary_text or ""

    primary = route_text(
        primary_text
    )

    secondary = None

    validation = None

    detection = deepcopy(
        primary["detection"]
    )

    primary_fields = primary["fields"]

    if secondary_text is not None:

        secondary = route_text(
            secondary_text
        )

        primary_decision = primary[
            "detection"
        ]["decision"]

        secondary_decision = secondary[
            "detection"
        ]["decision"]

        # Preserve classification disagreements.

        if primary_decision != secondary_decision:

            detection["decision"] = "REVIEW"

            detection["is_notice"] = False

            detection["confidence"] = "LOW"

            detection["reason"] = (
                "OCR outputs produced different "
                "classification decisions"
            )

            detection["requires_review"] = True

            if primary_fields is None:

                primary_fields = secondary["fields"]

        # Compare extracted values from both OCR runs.

        if (

            primary["fields"] is not None

            and secondary["fields"] is not None
        ):

            validation = validate_extracted_fields(

                primary["fields"],

                secondary["fields"],

                source_a=(
                    primary_ocr_language
                    or "primary"
                ),

                source_b=(
                    secondary_ocr_language
                    or "secondary"
                )
            )

    # ----------------------------------------------
    # Final policy considers both OCR sources.
    # ----------------------------------------------

    detection = apply_classification_policy(

        primary_text,

        detection,

        secondary_text=secondary_text
    )

    decision = detection["decision"]

    retain_candidate = (
        decision in ("ACCEPT", "REVIEW")
    )

    if retain_candidate and primary_fields is None:

        primary_fields = extract_recovered_fields(

            primary_text,

            primary["language_info"]
        )

    fields = build_review_fields(

        primary_fields,

        validation
    )

    # ----------------------------------------------
    # Validate subject property locations.
    # ----------------------------------------------

    location_validation = None

    party_validation = None

    if retain_candidate:

        location_validation = validate_property_locations(

            primary_text,

            secondary_text
        )

        party_validation = extract_unified_parties(

            primary_text,

            secondary_text,

            notice_category=detection.get(
                "notice_category"
            ) or "",

        )

    else:

        fields = None


    from notices.services.unified_measurement_extractor import (
        extract_unified_measurements,
    )

    from notices.services.deadline_extractor import (
        validate_deadlines,
    )

    measurement_validation = None
    deadline_validation = None

    if party_validation is not None:
        measurement_validation = extract_unified_measurements(
            primary_text,
            secondary_text,
        )

        deadline_validation = validate_deadlines(
            primary_text,
            secondary_text,
        )

    return {

        "detection": detection,

        "fields": fields,

        "raw_text": primary_text,

        "language": primary[
            "language_info"
        ]["language"],

        "language_info": primary[
            "language_info"
        ],

        "decision": decision,

        "notice_category": detection.get(
            "notice_category"
        ),

        "retain_candidate": retain_candidate,

        "requires_review": retain_candidate,

        "verified": False,

        "eligible_for_alert": False,

        "primary_ocr_language": (
            primary_ocr_language
        ),

        "secondary_ocr_language": (
            secondary_ocr_language
        ),

        "secondary_raw_text": secondary_text,

        "primary_result": primary,

        "secondary_result": secondary,

        "ocr_validation": validation,

        "location_validation": location_validation,

        "measurement_validation": measurement_validation,
        "deadline_validation": deadline_validation,
        "party_validation": party_validation
    }
