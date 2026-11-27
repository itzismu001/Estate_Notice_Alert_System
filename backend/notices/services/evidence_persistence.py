"""Persistence of unverified notice extraction evidence."""

import hashlib
import json

from notices.models import NoticeExtractionEvidence


REQUIRED_VALIDATIONS = (
    "ocr_validation",
    "location_validation",
    "party_validation",
    "measurement_validation",
    "deadline_validation",
)


def calculate_payload_hash(payload):

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def validate_evidence_payload(result):

    if not isinstance(result, dict):
        raise ValueError("Invalid extraction result")

    if result.get("retain_candidate") is not True:
        raise ValueError("Candidate was not retained")

    if result.get("decision") not in (
        "ACCEPT",
        "REVIEW",
    ):
        raise ValueError("Invalid candidate decision")

    if result.get("verified") is not False:
        raise ValueError("Unexpected verification status")

    if result.get("eligible_for_alert") is not False:
        raise ValueError("Unsafe alert eligibility")

    if result.get("requires_review") is not True:
        raise ValueError("Manual review is required")

    for key in REQUIRED_VALIDATIONS:

        if key not in result:
            raise ValueError(
                f"Missing validation: {key}"
            )

    if not result.get("raw_text", "").strip():
        raise ValueError("Missing original notice text")

    return True


def save_extraction_evidence(
    notice_page,
    box,
    pipeline_version="multilingual_v1",
):

    result = box["notice_result"]

    validate_evidence_payload(result)

    payload = {
        "schema_version": "1.0",

        "pipeline_version": pipeline_version,

        "page_number": box["page_number"],

        "region_number": box.get(
            "region_number"
        ),

        "detection_method": box.get(
            "detection_method"
        ),

        "bbox": box["bbox"],

        "normalized_bbox": box["normalized_bbox"],

        "coordinate_unit": box.get(
            "coordinate_unit",
            "PDF_POINTS"
        ),

        "coordinate_format": box.get(
            "coordinate_format",
            "XYXY"
        ),

        "notice_result": result,

        "requires_review": True,

        "verified": False,

        "approved_for_search": False,

        "eligible_for_alert": False,
    }

    payload_hash = calculate_payload_hash(
        payload
    )

    evidence, created = (
        NoticeExtractionEvidence.objects
        .get_or_create(
            notice_page=notice_page,
            payload_hash=payload_hash,
            defaults={
                "schema_version": "1.0",

                "pipeline_version": pipeline_version,

                "language": result.get(
                    "language", ""
                ),

                "decision": result["decision"],

                "notice_category": result.get(
                    "notice_category", ""
                ),

                "payload": payload,
            }
        )
    )

    return evidence, created
