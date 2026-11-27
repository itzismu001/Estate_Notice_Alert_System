
import math
import pymupdf

from documents.services.pdf_extractor import extract_pdf_text
from documents.services.ocr_processor import process_ocr_pages
from notices.services.notice_processor import process_notice
from notices.services.bbox_detector import detect_notice_boxes


# ==================================================
# BOUNDING-BOX NORMALIZATION
# ==================================================

def normalize_bbox(bbox, page_width, page_height):

    if page_width <= 0 or page_height <= 0:
        raise ValueError("Invalid page dimensions")

    x0 = float(bbox["x0"])
    y0 = float(bbox["y0"])
    x1 = float(bbox["x1"])
    y1 = float(bbox["y1"])

    coordinates = [x0, y0, x1, y1]

    if not all(math.isfinite(v) for v in coordinates):
        raise ValueError("Invalid bounding-box coordinates")

    if x1 <= x0 or y1 <= y0:
        raise ValueError("Invalid bounding-box area")

    # Clip minor coordinate overflow.

    x0 = max(0.0, min(x0, page_width))
    x1 = max(0.0, min(x1, page_width))

    y0 = max(0.0, min(y0, page_height))
    y1 = max(0.0, min(y1, page_height))

    if x1 <= x0 or y1 <= y0:
        raise ValueError("Bounding box outside page")

    return {
        "x0": round(x0 / page_width, 6),
        "y0": round(y0 / page_height, 6),
        "x1": round(x1 / page_width, 6),
        "y1": round(y1 / page_height, 6),
    }


# ==================================================
# PDF PAGE METADATA
# ==================================================

def extract_page_metadata(pdf_path):

    metadata = {}

    with pymupdf.open(pdf_path) as document:

        for index, page in enumerate(document, 1):

            # Use unrotated page dimensions to match
            # the coordinate system of our detectors.

            page_rect = (
                page.rect * page.derotation_matrix
            )

            metadata[index] = {
                "page_width": float(page_rect.width),
                "page_height": float(page_rect.height),
                "page_rotation": page.rotation,
                "dimension_unit": "PDF_POINTS",
            }

    return metadata


# ==================================================
# MAIN PDF PROCESSING PIPELINE
# ==================================================

def process_pdf(
    pdf_path,
    multilingual=False,
    selected_pages=None,
    validate_secondary=True,
    force_region_ocr=False,
):

    if multilingual:

        from documents.services.multilingual_pipeline import (
            process_multilingual_pdf,
        )

        return process_multilingual_pdf(
            pdf_path,
            selected_pages=selected_pages,
            validate_secondary=validate_secondary,
            force_region_ocr=force_region_ocr,
        )

    if selected_pages is not None or force_region_ocr:
        raise ValueError(
            "These options require multilingual=True"
        )


    # STEP 1: Extract selectable PDF text.

    direct_result = extract_pdf_text(pdf_path)

    # STEP 2: Extract page metadata.

    page_metadata = extract_page_metadata(pdf_path)

    # STEP 3: Process pages requiring OCR.

    ocr_pages = process_ocr_pages(
        pdf_path,
        direct_result["ocr_required_pages"]
    )

    ocr_map = {
        item["page_number"]: item
        for item in ocr_pages
    }

    ocr_required = set(
        direct_result["ocr_required_pages"]
    )

    final_pages = []

    # STEP 4: Process individual pages.

    for page in direct_result["pages"]:

        page_number = page["page_number"]
        metadata = page_metadata[page_number]

        method = "direct"
        text = page.get("text", "")

        processing_status = "COMPLETED"
        error_message = ""

        try:

            # Select the appropriate extracted text.

            if page_number in ocr_required:

                method = "ocr"

                if page_number not in ocr_map:
                    raise RuntimeError(
                        "Required OCR result is missing"
                    )

                ocr_result = ocr_map[page_number]

                text = ocr_result.get("text", "")

                if str(
                    ocr_result.get("status", "")
                ).lower() in ("failed", "error"):

                    raise RuntimeError(
                        ocr_result.get("error_message")
                        or "OCR processing failed"
                    )

            # Page-level notice classification.

            notice_result = process_notice(text)

            # Detect individual notice regions.

            boxes = detect_notice_boxes(
                pdf_path,
                page_number
            )

            # Process each detected notice.

            for box in boxes:

                box["notice_result"] = process_notice(
                    box["text"]
                )

                # Preserve original PDF coordinates.

                box["coordinate_unit"] = "PDF_POINTS"
                box["coordinate_format"] = "XYXY"

                # Generate normalized coordinates
                # for database and frontend usage.

                box["normalized_bbox"] = normalize_bbox(
                    box["bbox"],
                    metadata["page_width"],
                    metadata["page_height"]
                )

        except Exception as error:

            processing_status = "FAILED"
            error_message = str(error)

            notice_result = None
            boxes = []

        final_pages.append({

            "page_number": page_number,

            "page_width": metadata["page_width"],

            "page_height": metadata["page_height"],

            "page_rotation": metadata["page_rotation"],

            "dimension_unit": metadata["dimension_unit"],

            "method": method,

            "text": text,

            "processing_status": processing_status,

            "error_message": error_message,

            "notice_result": notice_result,

            "bounding_boxes": boxes,

        })

    # STEP 5: Generate processing summary.

    completed_pages = sum(
        page["processing_status"] == "COMPLETED"
        for page in final_pages
    )

    failed_pages = sum(
        page["processing_status"] == "FAILED"
        for page in final_pages
    )

    total_notices = sum(
        1
        for page in final_pages
        for box in page["bounding_boxes"]
        if box.get(
            "notice_result", {}
        ).get(
            "detection", {}
        ).get("is_notice")
    )

    return {

        "total_pages": direct_result["total_pages"],

        "pages": final_pages,

        "ocr_processed_pages": len(ocr_pages),

        "completed_pages": completed_pages,

        "failed_pages": failed_pages,

        "total_notices": total_notices,

    }

