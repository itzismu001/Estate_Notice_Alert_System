"""OCR fallback for scanned notices without physical borders."""

from time import perf_counter

import pymupdf

from notices.services.ocr_bbox_detector import (
    extract_ocr_text_blocks,
)

from notices.services.bbox_detector import (
    group_text_blocks,
)

from notices.services.multilingual_processor import (
    process_multilingual_notice,
)

from notices.services.border_bbox_detector import (
    render_page,
)

from notices.services.ocr_router import (
    prepare_ocr_image,
    run_ocr,
    select_secondary_language,
)


def detect_multilingual_ocr_fallback(
    pdf_path,
    page_number,
    validate_secondary=True,
):

    start = perf_counter()

    primary_start = perf_counter()

    blocks = extract_ocr_text_blocks(
        str(pdf_path),
        page_number,
        scale=3,
        language="kan+eng",
    )

    primary_seconds = round(
        perf_counter() - primary_start,
        4,
    )

    groups = group_text_blocks(blocks)

    notices = []

    rejected_regions = []

    failed_regions = []

    with pymupdf.open(str(pdf_path)) as document:

        page = document[page_number - 1]

        image = None

        pixmap = None

        for region_number, group in enumerate(
            groups, 1
        ):

            region_start = perf_counter()

            bbox = None

            try:

                text = group["text"].strip()

                if not text:
                    continue

                bbox = {
                    key: float(group[key])
                    for key in (
                        "x0", "y0", "x1", "y1"
                    )
                }

                result = process_multilingual_notice(
                    text,
                    primary_ocr_language="kan+eng",
                )

                secondary = None

                secondary_error = None

                if (
                    validate_secondary
                    and result["retain_candidate"]
                ):

                    language = (
                        select_secondary_language(text)
                    )

                    if language:

                        try:

                            if image is None:

                                image, pixmap = (
                                    render_page(
                                        page,
                                        scale=3,
                                    )
                                )

                            rect = pymupdf.Rect(
                                bbox["x0"],
                                bbox["y0"],
                                bbox["x1"],
                                bbox["y1"],
                            )

                            rect = (
                                rect
                                * page.rotation_matrix
                                * pymupdf.Matrix(3, 3)
                            )

                            x0 = max(
                                0,
                                int(rect.x0)
                                - pixmap.x - 12,
                            )

                            y0 = max(
                                0,
                                int(rect.y0)
                                - pixmap.y - 12,
                            )

                            x1 = min(
                                image.shape[1],
                                int(rect.x1 + 1)
                                - pixmap.x + 12,
                            )

                            y1 = min(
                                image.shape[0],
                                int(rect.y1 + 1)
                                - pixmap.y + 12,
                            )

                            crop = image[
                                y0:y1, x0:x1
                            ]

                            secondary = run_ocr(
                                prepare_ocr_image(crop),
                                language=language,
                            )

                            validated = (
                                process_multilingual_notice(
                                    text,
                                    secondary_text=(
                                        secondary["text"]
                                    ),
                                    primary_ocr_language=(
                                        "kan+eng"
                                    ),
                                    secondary_ocr_language=(
                                        language
                                    ),
                                )
                            )

                            if validated["retain_candidate"]:

                                result = validated

                            else:

                                secondary_error = (
                                    "Secondary classification "
                                    "did not retain candidate"
                                )

                        except Exception as error:

                            secondary_error = str(error)

                result["ocr_metadata"] = {

                    "primary": {
                        "language": "kan+eng",
                        "text": text,
                        "method": "page_ocr_text_blocks",
                    },

                    "secondary": secondary,

                    "secondary_error": secondary_error,

                    "secondary_validation_requested": (
                        validate_secondary
                    ),

                    "secondary_validation_completed": (
                        secondary is not None
                        and secondary_error is None
                    ),

                    "ocr_passes": (
                        2 if secondary is not None else 1
                    ),

                    "page_primary_ocr_seconds": (
                        primary_seconds
                    ),

                    "total_processing_seconds": round(
                        perf_counter() - region_start,
                        4,
                    ),
                }

                region = {

                    "page_number": page_number,

                    "column_number": None,

                    "region_number": region_number,

                    "bbox": bbox,

                    "coordinate_unit": "PDF_POINTS",

                    "coordinate_format": "XYXY",

                    "text": result["raw_text"],

                    "language": result["language"],

                    "decision": result["decision"],

                    "detection_method": (
                        "multilingual_ocr_fallback"
                    ),

                    "ocr_language": "kan+eng",

                    "notice_result": result,

                    "requires_review": True,

                    "eligible_for_alert": False,

                    "processing_seconds": round(
                        perf_counter() - region_start,
                        4,
                    ),
                }

                if result["retain_candidate"]:

                    region["status"] = "needs_review"

                    notices.append(region)

                else:

                    region["status"] = "rejected"

                    rejected_regions.append(region)

            except Exception as error:

                failed_regions.append({

                    "page_number": page_number,

                    "region_number": region_number,

                    "bbox": bbox,

                    "status": "failed",

                    "error": str(error),

                })

    return {

        "page_number": page_number,

        "total_regions": len(groups),

        "accepted_count": sum(
            item["decision"] == "ACCEPT"
            for item in notices
        ),

        "review_count": sum(
            item["decision"] == "REVIEW"
            for item in notices
        ),

        "rejected_count": len(rejected_regions),

        "failed_count": len(failed_regions),

        "total_retained": len(notices),

        "status": (
            "partial_failure"
            if failed_regions
            else "completed"
        ),

        "notices": notices,

        "rejected_regions": rejected_regions,

        "failed_regions": failed_regions,

        "ocr_text": "\n".join(
            block[4] for block in blocks
        ),

        "processing_seconds": round(
            perf_counter() - start,
            4,
        ),
    }
