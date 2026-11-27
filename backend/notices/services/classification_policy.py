
from copy import deepcopy

from notices.services.secured_property_detector import (
    detect_secured_property_notice
)

from notices.services.court_notice_detector import (
    detect_property_court_notice
)


# ==================================================
# COMMON NOTICE CLASSIFICATION POLICY
# ==================================================

def apply_classification_policy(
    raw_text,
    base_detection,
    secondary_text=None
):

    detection = deepcopy(
        base_detection or {}
    )

    original_decision = detection.get(
        "decision",
        "ACCEPT"
        if detection.get("is_notice")
        else "REJECT"
    )

    # Evaluate primary and secondary OCR separately.

    sources = [
        ("primary", raw_text or "")
    ]

    if secondary_text:

        sources.append(
            ("secondary", secondary_text)
        )

    secured_evidence = []

    court_evidence = []

    for source, text in sources:

        secured = detect_secured_property_notice(
            text
        )

        court = detect_property_court_notice(
            text
        )

        if secured["is_secured_property_notice"]:

            secured_evidence.append({

                "source": source,

                "result": secured
            })

        if court["is_property_court_notice"]:

            court_evidence.append({

                "source": source,

                "result": court
            })

    categories = []

    for item in secured_evidence + court_evidence:

        category = item["result"][
            "notice_category"
        ]

        if category:

            categories.append(category)

    categories = list(
        dict.fromkeys(categories)
    )

    # ----------------------------------------------
    # Special legal notices require manual review.
    # ----------------------------------------------

    if secured_evidence or court_evidence:

        final_decision = "REVIEW"

        detection["confidence"] = "LOW"

        if secured_evidence and court_evidence:

            reason = (
                "Both secured-property and court "
                "evidence detected"
            )

        elif secured_evidence:

            reason = (
                "Secured-property notice requires "
                "manual scope and category verification"
            )

        else:

            reason = (
                "Property-related court proceeding "
                "requires manual verification"
            )

        detection["reason"] = reason

    else:

        final_decision = original_decision

    retain_candidate = (
        final_decision in ("ACCEPT", "REVIEW")
    )

    detection["decision"] = final_decision

    detection["is_notice"] = (
        final_decision == "ACCEPT"
    )

    detection["requires_review"] = (
        retain_candidate
    )

    detection["retain_candidate"] = (
        retain_candidate
    )

    detection["verified"] = False

    detection["eligible_for_alert"] = False

    # Preserve a common property notice type.

    if retain_candidate:

        detection["notice_type"] = (
            detection.get("notice_type")
            or "ESTATE_PROPERTY_NOTICE"
        )

    # Preserve category separately for compatibility.

    if len(categories) == 1:

        notice_category = categories[0]

    elif len(categories) > 1:

        notice_category = "MULTIPLE_LEGAL_CATEGORIES"

    elif retain_candidate:

        notice_category = (
            "GENERAL_PROPERTY_NOTICE"
        )

    else:

        notice_category = None

    detection["notice_category"] = (
        notice_category
    )

    # ----------------------------------------------
    # Preserve classification evidence.
    # ----------------------------------------------

    detection["classification_policy"] = {

        "original_decision": original_decision,

        "final_decision": final_decision,

        "decision_changed": (
            original_decision != final_decision
        ),

        "candidate_categories": categories,

        "secured_property_evidence": (
            secured_evidence
        ),

        "property_court_evidence": (
            court_evidence
        ),

        "recovered_candidate": (

            original_decision == "REJECT"

            and retain_candidate
        ),

        "requires_scope_verification": bool(
            secured_evidence
        )
    }

    return detection
