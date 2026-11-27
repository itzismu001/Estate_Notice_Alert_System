
import math
import re

from django.db import transaction

from notices.services.evidence_persistence import (
    save_extraction_evidence,
)

from documents.models import SourceDocument, DocumentPage
from notices.models import Notice, NoticeEntity, NoticePage


# ==================================================
# ENTITY MAPPING
# ==================================================

ENTITY_MAPPING = {

    "survey_numbers": (
        NoticeEntity.EntityType.SURVEY_NUMBER,
        ""
    ),

    "subdivision_numbers": (
        NoticeEntity.EntityType.SUBDIVISION_NUMBER,
        ""
    ),

    "plot_numbers": (
        NoticeEntity.EntityType.PLOT_NUMBER,
        ""
    ),

    "tp_numbers": (
        NoticeEntity.EntityType.TP_NUMBER,
        ""
    ),

    "property_numbers": (
        NoticeEntity.EntityType.PROPERTY_NUMBER,
        ""
    ),

    "site_numbers": (
        NoticeEntity.EntityType.PROPERTY_NUMBER,
        "Site No. "
    ),

    "khata_numbers": (
        NoticeEntity.EntityType.PROPERTY_NUMBER,
        "Khata No. "
    ),

    "pid_numbers": (
        NoticeEntity.EntityType.PROPERTY_NUMBER,
        "PID No. "
    ),

    "municipal_numbers": (
        NoticeEntity.EntityType.PROPERTY_NUMBER,
        "Municipal No. "
    ),

    "flat_numbers": (
        NoticeEntity.EntityType.PROPERTY_NUMBER,
        "Flat No. "
    ),

    "hissa_numbers": (
        NoticeEntity.EntityType.OTHER,
        "Hissa No. "
    ),

    "khasra_numbers": (
        NoticeEntity.EntityType.OTHER,
        "Khasra No. "
    ),

    "document_numbers": (
        NoticeEntity.EntityType.OTHER,
        "Document No. "
    ),
}


LOCATION_FIELDS = [
    "village",
    "hobli",
    "taluk",
    "district",
]


# ==================================================
# BOUNDING-BOX VALIDATION
# ==================================================

def validate_normalized_bbox(bbox):

    if not isinstance(bbox, dict):
        raise ValueError("Missing normalized bounding box")

    values = {
        key: float(bbox[key])
        for key in ("x0", "y0", "x1", "y1")
    }

    if not all(
        math.isfinite(value)
        for value in values.values()
    ):
        raise ValueError("Invalid bounding-box values")

    if not (
        0 <= values["x0"] < values["x1"] <= 1
        and
        0 <= values["y0"] < values["y1"] <= 1
    ):
        raise ValueError(
            "Invalid normalized bounding box"
        )

    return values


# ==================================================
# DUPLICATE DETECTION
# ==================================================

def calculate_iou(box_a, box_b):

    try:

        box_a = validate_normalized_bbox(box_a)
        box_b = validate_normalized_bbox(box_b)

    except (ValueError, TypeError, KeyError):
        return 0.0

    intersection_width = max(
        0,
        min(box_a["x1"], box_b["x1"])
        - max(box_a["x0"], box_b["x0"])
    )

    intersection_height = max(
        0,
        min(box_a["y1"], box_b["y1"])
        - max(box_a["y0"], box_b["y0"])
    )

    intersection = (
        intersection_width * intersection_height
    )

    area_a = (
        (box_a["x1"] - box_a["x0"])
        * (box_a["y1"] - box_a["y0"])
    )

    area_b = (
        (box_b["x1"] - box_b["x0"])
        * (box_b["y1"] - box_b["y0"])
    )

    union = area_a + area_b - intersection

    return intersection / union if union > 0 else 0


def normalize_notice_text(text):

    return re.sub(
        r"\s+",
        " ",
        text or ""
    ).strip().casefold()


def find_existing_notice_page(
    page,
    bbox,
    text,
    threshold=0.90
):

    existing_pages = NoticePage.objects.filter(
        document_page=page,
        coordinate_unit=(
            NoticePage.CoordinateUnit.NORMALIZED
        ),
        coordinate_format=(
            NoticePage.CoordinateFormat.XYXY
        )
    ).select_related("notice")

    normalized_text = normalize_notice_text(text)

    best_match = None
    best_score = 0.0

    for existing in existing_pages:

        overlap = calculate_iou(
            existing.bounding_box,
            bbox
        )

        same_text = (
            normalize_notice_text(
                existing.extracted_text
            ) == normalized_text
        )

        exact_bbox = existing.bounding_box == bbox

        if exact_bbox:
            return existing

        if same_text and overlap >= threshold:

            if overlap > best_score:

                best_score = overlap
                best_match = existing

    return best_match


# ==================================================
# REVIEW PROTECTION
# ==================================================

def is_reviewed_notice(notice):

    return (
        notice.status != Notice.Status.NEEDS_REVIEW
        or notice.reviewed_by_id is not None
        or notice.reviewed_at is not None
        or notice.review_history.exists()
    )


# ==================================================
# STRUCTURED ENTITY STORAGE
# ==================================================

def save_notice_entities(notice, fields):

    fields = fields or {}

    entities = []
    seen = set()

    def add_entity(
        entity_type,
        value,
        source_text=""
    ):

        if value is None:
            return

        value = str(value).strip()

        if not value:
            return

        key = (
            entity_type,
            value.casefold()
        )

        if key in seen:
            return

        seen.add(key)

        entities.append(
            NoticeEntity(
                notice=notice,
                entity_type=entity_type,
                value=value,

                # Field-level confidence is not
                # currently measured.
                confidence=Notice.Confidence.LOW,

                source_text=str(source_text or "")
            )
        )

    # Store all extracted property identifiers.

    for field_name, mapping in ENTITY_MAPPING.items():

        entity_type, prefix = mapping

        values = fields.get(field_name) or []

        # Backward compatibility with older
        # scalar-only extraction results.

        if not values:

            scalar_key = field_name[:-1]

            scalar_value = fields.get(scalar_key)

            if scalar_value is not None:
                values = [scalar_value]

        if isinstance(values, str):
            values = [values]

        for value in values:

            if value is None:
                continue

            add_entity(
                entity_type,
                prefix + str(value),
                value
            )

    # Store locations with descriptive labels.

    for field_name in LOCATION_FIELDS:

        value = fields.get(field_name)

        if value:

            add_entity(
                NoticeEntity.EntityType.LOCATION,
                f"{field_name.title()}: {value}",
                value
            )

    # Store party names without assuming ownership.

    for party in fields.get("party_names") or []:

        if party:

            add_entity(
                NoticeEntity.EntityType.OTHER,
                f"Party: {party}",
                party
            )

    # Advocate information.

    add_entity(
        NoticeEntity.EntityType.ADVOCATE,
        fields.get("advocate_name"),
        fields.get("advocate_name")
    )

    # Property address, when available.

    add_entity(
        NoticeEntity.EntityType.PROPERTY_ADDRESS,
        fields.get("property_address"),
        fields.get("property_address")
    )

    # Notice date is separate from publication date.

    add_entity(
        NoticeEntity.EntityType.NOTICE_DATE,
        fields.get("notice_date"),
        fields.get("notice_date")
    )

    publication_date = fields.get(
        "publication_date"
    )

    if publication_date:

        add_entity(
            NoticeEntity.EntityType.OTHER,
            f"Publication date: {publication_date}",
            publication_date
        )

    # Preserve deadline duration and unit.

    deadline = fields.get("response_deadline")
    unit = fields.get("response_deadline_unit")

    if deadline is not None:

        value = str(deadline)

        if unit:
            value += f" {unit}"

        add_entity(
            NoticeEntity.EntityType.OBJECTION_DEADLINE,
            value,
            ""
        )

    NoticeEntity.objects.bulk_create(entities)

    return len(entities)


# ==================================================
# MAIN DATABASE SAVER
# ==================================================

@transaction.atomic
def save_document_pages(
    source_document,
    pipeline_result
):

    # Lock the source document to serialize
    # concurrent calls to this saver.

    source_document = (
        SourceDocument.objects
        .select_for_update()
        .get(pk=source_document.pk)
    )

    summary = {
        "pages_created": 0,
        "pages_updated": 0,
        "failed_pages": 0,
        "notices_created": 0,
        "notices_skipped_existing": 0,
        "reviewed_notices_skipped": 0,
        "entities_created": 0,
        "evidence_created": 0,
        "evidence_skipped_existing": 0,
    }

    for page_data in pipeline_result["pages"]:

        page_number = page_data["page_number"]

        method = page_data.get("method", "")

        text = page_data.get("text", "")

        processing_status = page_data.get(
            "processing_status",
            "COMPLETED"
        )

        error_message = page_data.get(
            "error_message",
            ""
        )

        page_type_mapping = {
            "direct": DocumentPage.PageType.TEXT,
            "ocr": DocumentPage.PageType.SCANNED,
            "mixed": DocumentPage.PageType.MIXED,
        }

        page_type = page_type_mapping.get(
            method,
            DocumentPage.PageType.UNKNOWN
        )

        failed = processing_status != "COMPLETED"

        defaults = {
            "processing_status": (
                DocumentPage.ProcessingStatus.FAILED
                if failed
                else
                DocumentPage.ProcessingStatus.COMPLETED
            ),
            "error_message": error_message,
        }

        # Preserve existing successful text if a
        # subsequent processing attempt fails.

        if not failed:

            defaults.update({
                "page_type": page_type,

                "extracted_text": page_data.get(
                    "direct_text",
                    text if method == "direct" else ""
                ),

                "ocr_text": page_data.get(
                    "ocr_text",
                    text if method == "ocr" else ""
                ),

                "page_width": (
                    round(page_data["page_width"])
                    if page_data.get("page_width")
                    else None
                ),

                "page_height": (
                    round(page_data["page_height"])
                    if page_data.get("page_height")
                    else None
                ),
            })

        page, created = (
            DocumentPage.objects.update_or_create(
                document=source_document,
                page_number=page_number,
                defaults=defaults
            )
        )

        if created:
            summary["pages_created"] += 1
        else:
            summary["pages_updated"] += 1

        if failed:

            summary["failed_pages"] += 1

            continue

        # Process individual notice regions.

        for box in page_data.get(
            "bounding_boxes", []
        ):

            notice_result = box.get(
                "notice_result"
            ) or {}

            detection = notice_result.get(
                "detection"
            ) or {}

            multilingual = (
                "retain_candidate" in notice_result
            )

            if multilingual:
                if not notice_result["retain_candidate"]:
                    continue
            elif not detection.get("is_notice"):
                continue

            bbox = validate_normalized_bbox(
                box.get("normalized_bbox")
            )

            notice_text = box.get("text", "").strip()

            if not notice_text:
                continue

            existing_page = find_existing_notice_page(
                page,
                bbox,
                notice_text
            )

            # Do not overwrite an existing notice
            # or its manually corrected entities.

            if existing_page:

                if is_reviewed_notice(
                    existing_page.notice
                ):

                    summary[
                        "reviewed_notices_skipped"
                    ] += 1

                else:

                    summary[
                        "notices_skipped_existing"
                    ] += 1

                continue

            # Create a new notice.

            confidence = detection.get(
                "confidence",
                Notice.Confidence.LOW
            )

            if confidence not in Notice.Confidence.values:

                confidence = Notice.Confidence.LOW

            notice = Notice.objects.create(

                title=notice_text.splitlines()[0][:500],

                notice_text=notice_text,

                notice_type=(
                    detection.get("notice_category")
                    or detection.get("notice_type")
                    or ""
                ),

                confidence=confidence,

                status=Notice.Status.NEEDS_REVIEW
            )

            notice_page = NoticePage.objects.create(

                notice=notice,

                document_page=page,

                bounding_box=bbox,

                coordinate_format=(
                    NoticePage.CoordinateFormat.XYXY
                ),

                coordinate_unit=(
                    NoticePage.CoordinateUnit.NORMALIZED
                ),

                extracted_text=notice_text,

                page_sequence=1
            )

            summary["notices_created"] += 1

            if multilingual:

                evidence, evidence_created = (
                    save_extraction_evidence(
                        notice_page,
                        box,
                        pipeline_version=pipeline_result.get(
                            "pipeline_version",
                            "multilingual_v1"
                        ),
                    )
                )

                if evidence_created:

                    summary["evidence_created"] += 1

                else:

                    summary["evidence_skipped_existing"] += 1

                entity_count = 0

            else:

                entity_count = save_notice_entities(
                    notice,
                    notice_result.get("fields")
                )

            summary[
                "entities_created"
            ] += entity_count

    return summary

