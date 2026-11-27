
import numpy as np
import pymupdf

from time import perf_counter

from notices.services.border_bbox_detector import (
    render_page,
    resize_for_detection,
    detect_advertisement_boxes,
    pixels_to_pdf_bbox
)

from notices.services.ocr_router import (
    check_ocr_languages,
    process_notice_image
)


# ==================================================
# MAP DETECTION COORDINATES TO ORIGINAL IMAGE
# ==================================================

def map_region_coordinates(
    box,
    original_shape,
    working_shape
):

    x, y, w, h = box

    original_height, original_width = (
        original_shape[:2]
    )

    working_height, working_width = (
        working_shape[:2]
    )

    x_scale = original_width / working_width

    y_scale = original_height / working_height

    x0 = max(
        0,
        int(np.floor(x * x_scale))
    )

    y0 = max(
        0,
        int(np.floor(y * y_scale))
    )

    x1 = min(
        original_width,
        int(np.ceil((x + w) * x_scale))
    )

    y1 = min(
        original_height,
        int(np.ceil((y + h) * y_scale))
    )

    return x0, y0, x1, y1


# ==================================================
# MULTILINGUAL BORDER-FIRST PDF DETECTOR
# ==================================================

def detect_multilingual_notice_boxes(
    pdf_path,
    page_number,
    validate_secondary=True
):

    start = perf_counter()

    language_status = check_ocr_languages()

    if not language_status["multilingual_ready"]:

        raise RuntimeError(
            "Missing OCR languages: "
            + ", ".join(language_status["missing"])
        )

    notices = []

    rejected_regions = []

    failed_regions = []

    render_scale = 3

    with pymupdf.open(pdf_path) as document:

        if page_number < 1 or page_number > len(document):

            raise ValueError(
                "Invalid page number"
            )

        page = document[page_number - 1]

        # ------------------------------------------
        # Render original PDF page.
        # ------------------------------------------

        original_image, pixmap = render_page(
            page,
            scale=render_scale
        )

        working_image = resize_for_detection(
            original_image
        )

        # ------------------------------------------
        # Detect individual advertisement regions.
        # ------------------------------------------

        advertisement_boxes = (
            detect_advertisement_boxes(
                working_image
            )
        )

        # ------------------------------------------
        # Process each advertisement independently.
        # ------------------------------------------

        for region_number, box in enumerate(
            advertisement_boxes,
            1
        ):

            region_start = perf_counter()

            bbox = None

            try:

                x0, y0, x1, y1 = (
                    map_region_coordinates(
                        box,
                        original_image.shape,
                        working_image.shape
                    )
                )

                bbox = pixels_to_pdf_bbox(

                    page,

                    pixmap,

                    x0,

                    y0,

                    x1,

                    y1,

                    render_scale
                )

                crop = original_image[
                    y0:y1,
                    x0:x1
                ]

                if crop.size == 0:

                    raise ValueError(
                        "Empty advertisement crop"
                    )

                # ----------------------------------
                # Automatic multilingual OCR.
                # ----------------------------------

                result = process_notice_image(

                    crop,

                    validate_secondary=(
                        validate_secondary
                    )
                )

                elapsed = round(

                    perf_counter() - region_start,

                    4
                )

                region_result = {

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
                        "multilingual_border_first"
                    ),

                    "ocr_language": (
                        result["primary_ocr_language"]
                    ),

                    "notice_result": result,

                    "requires_review": (
                        result["requires_review"]
                    ),

                    "eligible_for_alert": False,

                    "processing_seconds": elapsed
                }

                # ----------------------------------
                # Preserve ACCEPT and REVIEW.
                # ----------------------------------

                if result["retain_candidate"]:

                    region_result["status"] = (
                        "needs_review"
                    )

                    notices.append(region_result)

                else:

                    region_result["status"] = (
                        "rejected"
                    )

                    rejected_regions.append(
                        region_result
                    )

            except Exception as error:

                # Continue processing remaining
                # advertisement regions.

                failed_regions.append({

                    "page_number": page_number,

                    "region_number": region_number,

                    "bbox": bbox,

                    "status": "failed",

                    "error": str(error),

                    "processing_seconds": round(

                        perf_counter() - region_start,

                        4
                    )
                })

    accepted_count = sum(

        item["decision"] == "ACCEPT"

        for item in notices
    )

    review_count = sum(

        item["decision"] == "REVIEW"

        for item in notices
    )

    return {

        "page_number": page_number,

        "total_regions": len(
            advertisement_boxes
        ),

        "accepted_count": accepted_count,

        "review_count": review_count,

        "rejected_count": len(
            rejected_regions
        ),

        "failed_count": len(
            failed_regions
        ),

        "total_retained": len(notices),

        "status": (

            "partial_failure"

            if failed_regions

            else "completed"
        ),

        "notices": notices,

        "rejected_regions": rejected_regions,

        "failed_regions": failed_regions,

        "processing_seconds": round(

            perf_counter() - start,

            4
        )
    }
