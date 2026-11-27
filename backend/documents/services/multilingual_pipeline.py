"""Multilingual newspaper PDF processing pipeline."""

from pathlib import Path
from time import perf_counter
from collections import Counter

import pymupdf

from documents.services.pipeline import (
    normalize_bbox,
    extract_page_metadata,
)

from notices.services.bbox_detector import (
    group_text_blocks,
)

from notices.services.multilingual_processor import (
    process_multilingual_notice,
)

from notices.services.multilingual_bbox_detector import (
    detect_multilingual_notice_boxes,
)

from notices.services.ocr_router import (
    check_ocr_languages,
)

from notices.services.multilingual_ocr_fallback import (
    detect_multilingual_ocr_fallback,
)


def bbox_iou(first, second):

    width = max(
        0,
        min(first["x1"], second["x1"])
        - max(first["x0"], second["x0"]),
    )

    height = max(
        0,
        min(first["y1"], second["y1"])
        - max(first["y0"], second["y0"]),
    )

    intersection = width * height

    first_area = (
        (first["x1"] - first["x0"])
        * (first["y1"] - first["y0"])
    )

    second_area = (
        (second["x1"] - second["x0"])
        * (second["y1"] - second["y0"])
    )

    union = first_area + second_area - intersection

    return intersection / union if union > 0 else 0.0


def detect_direct_candidates(page, page_number):

    blocks = page.get_text(
        "blocks",
        sort=True,
    )

    groups = group_text_blocks(blocks)

    candidates = []

    for group in groups:

        text = group["text"].strip()

        if not text:
            continue

        result = process_multilingual_notice(
            text
        )

        if not result["retain_candidate"]:
            continue

        candidates.append({
            "page_number": page_number,
            "column_number": None,
            "region_number": None,

            "bbox": {
                key: float(group[key])
                for key in ("x0", "y0", "x1", "y1")
            },

            "text": text,
            "language": result["language"],
            "decision": result["decision"],
            "detection_method": "multilingual_direct",
            "ocr_language": None,
            "notice_result": result,
            "status": "needs_review",
            "requires_review": True,
            "eligible_for_alert": False,
        })

    return candidates


def merge_candidates(direct_candidates, ocr_candidates):

    merged = list(ocr_candidates)

    for candidate in direct_candidates:

        duplicate = False

        for existing in merged:

            overlap = bbox_iou(
                candidate["bbox"],
                existing["bbox"],
            )

            first_text = " ".join(
                candidate["text"].casefold().split()
            )

            second_text = " ".join(
                existing["text"].casefold().split()
            )

            if (
                overlap >= 0.90
                and first_text == second_text
            ):

                duplicate = True
                break

        if not duplicate:

            merged.append(candidate)

    return merged


def process_multilingual_pdf(
    pdf_path,
    selected_pages=None,
    validate_secondary=True,
    force_region_ocr=False,
):

    start = perf_counter()

    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Expected a PDF file")

    metadata = extract_page_metadata(pdf_path)

    final_pages = []

    decisions = Counter()

    ocr_processed_pages = 0

    with pymupdf.open(str(pdf_path)) as document:

        total_pages = len(document)

        if selected_pages is None:

            page_numbers = list(
                range(1, total_pages + 1)
            )

        else:

            page_numbers = sorted(
                set(selected_pages)
            )

        if not page_numbers:
            raise ValueError("No pages selected")

        if any(
            number < 1 or number > total_pages
            for number in page_numbers
        ):
            raise ValueError("Invalid selected page")

        for page_number in page_numbers:

            page_start = perf_counter()

            page = document[page_number - 1]

            page_metadata = metadata[page_number]

            direct_text = ""
            ocr_text = ""

            method = "direct"

            candidates = []

            failed_regions = []

            region_report = None

            fallback_report = None

            processing_status = "COMPLETED"

            error_message = ""

            try:

                direct_text = page.get_text().strip()

                direct_candidates = (
                    detect_direct_candidates(
                        page,
                        page_number,
                    )
                )

                candidates = direct_candidates

                requires_ocr = (
                    len(direct_text) < 80
                    or len(direct_text.split()) < 10
                    or force_region_ocr
                    or bool(page.get_images())
                )

                if requires_ocr:

                    language_status = (
                        check_ocr_languages()
                    )

                    if not language_status[
                        "multilingual_ready"
                    ]:
                        raise RuntimeError(
                            "Required OCR languages missing: "
                            + ", ".join(
                                language_status["missing"]
                            )
                        )

                    method = (
                        "mixed"
                        if direct_text
                        else "ocr"
                    )

                    ocr_processed_pages += 1

                    region_report = (
                        detect_multilingual_notice_boxes(
                            str(pdf_path),
                            page_number,
                            validate_secondary=(
                                validate_secondary
                            ),
                        )
                    )

                    failed_regions.extend(
                        region_report["failed_regions"]
                    )

                    ocr_candidates = (
                        region_report["notices"]
                    )

                    candidates = merge_candidates(
                        direct_candidates,
                        ocr_candidates,
                    )

                    all_regions = (
                        region_report["notices"]
                        + region_report["rejected_regions"]
                    )

                    ocr_text = "\n\n".join(
                        region.get("text", "")
                        for region in sorted(
                            all_regions,
                            key=lambda item:
                            item["region_number"],
                        )
                    )

                    if not candidates:

                        try:

                            fallback_report = (
                                detect_multilingual_ocr_fallback(
                                    str(pdf_path),
                                    page_number,
                                    validate_secondary=(
                                        validate_secondary
                                    ),
                                )
                            )

                            candidates = merge_candidates(
                                candidates,
                                fallback_report["notices"],
                            )

                            failed_regions.extend(
                                fallback_report["failed_regions"]
                            )

                            fallback_text = (
                                fallback_report.get(
                                    "ocr_text", ""
                                )
                            )

                            if fallback_text:

                                ocr_text = fallback_text

                        except Exception as error:

                            failed_regions.append({
                                "page_number": page_number,
                                "region_number": None,
                                "status": "failed",
                                "detection_method": (
                                    "multilingual_ocr_fallback"
                                ),
                                "error": str(error),
                            })

                valid_candidates = []

                for candidate in candidates:

                    try:

                        candidate["coordinate_unit"] = (
                            "PDF_POINTS"
                        )

                        candidate["coordinate_format"] = (
                            "XYXY"
                        )

                        candidate["normalized_bbox"] = (
                            normalize_bbox(
                                candidate["bbox"],
                                page_metadata["page_width"],
                                page_metadata["page_height"],
                            )
                        )

                        candidate["requires_review"] = True

                        candidate["eligible_for_alert"] = False

                        valid_candidates.append(
                            candidate
                        )

                    except Exception as error:

                        failed_regions.append({
                            "page_number": page_number,
                            "region_number": candidate.get(
                                "region_number"
                            ),
                            "bbox": candidate.get("bbox"),
                            "status": "failed",
                            "error": str(error),
                        })

                candidates = valid_candidates

                if failed_regions:

                    processing_status = (
                        "PARTIAL_FAILURE"
                    )

                    error_message = (
                        f"{len(failed_regions)} "
                        "region(s) failed"
                    )

            except Exception as error:

                processing_status = "FAILED"

                error_message = str(error)

                candidates = []

            for candidate in candidates:

                decisions[
                    candidate["decision"]
                ] += 1

            final_pages.append({
                "page_number": page_number,
                **page_metadata,

                "method": method,

                "text": (
                    direct_text
                    if method == "direct"
                    else ocr_text
                    if method == "ocr"
                    else direct_text + "\n\n" + ocr_text
                ),

                "direct_text": direct_text,

                "ocr_text": ocr_text,

                "ocr_text_scope": (
                    "PAGE_OCR_TEXT_BLOCKS"
                    if fallback_report is not None
                    and fallback_report.get("ocr_text")
                    else "DETECTED_REGIONS"
                    if region_report is not None
                    else None
                ),

                "processing_status": processing_status,

                "error_message": error_message,

                "notice_result": None,

                "bounding_boxes": candidates,

                "failed_regions": failed_regions,

                "region_report": region_report,

                "fallback_report": fallback_report,

                "processing_seconds": round(
                    perf_counter() - page_start,
                    4,
                ),
            })

            print(
                f"Page {page_number}/{total_pages}: "
                f"{processing_status} | "
                f"{len(candidates)} notices | "
                f"{perf_counter() - page_start:.2f}s",
                flush=True,
            )

    return {

        "pipeline_version": "multilingual_v2",

        "pdf_path": str(pdf_path),

        "total_pages": total_pages,

        "processed_pages": len(final_pages),

        "selected_pages": page_numbers,

        "pages": final_pages,

        "ocr_processed_pages": ocr_processed_pages,

        "completed_pages": sum(
            page["processing_status"] == "COMPLETED"
            for page in final_pages
        ),

        "partial_failure_pages": sum(
            page["processing_status"] == "PARTIAL_FAILURE"
            for page in final_pages
        ),

        "failed_pages": sum(
            page["processing_status"] == "FAILED"
            for page in final_pages
        ),

        "total_notices": sum(
            len(page["bounding_boxes"])
            for page in final_pages
        ),

        "decision_counts": dict(decisions),

        "requires_review": True,

        "eligible_for_alert": False,

        "processing_seconds": round(
            perf_counter() - start,
            4,
        ),
    }
