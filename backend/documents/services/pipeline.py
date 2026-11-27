
from documents.services.pdf_extractor import extract_pdf_text
from documents.services.ocr_processor import process_ocr_pages
from notices.services.notice_processor import process_notice
from notices.services.bbox_detector import detect_notice_boxes


def process_pdf(pdf_path):
    direct_result = extract_pdf_text(pdf_path)

    ocr_pages = process_ocr_pages(
        pdf_path,
        direct_result["ocr_required_pages"]
    )

    ocr_map = {
        item["page_number"]: item
        for item in ocr_pages
    }

    final_pages = []

    for page in direct_result["pages"]:
        page_number = page["page_number"]

        if page_number in ocr_map:
            ocr_result = ocr_map[page_number]
            text = ocr_result["text"]
            method = "ocr"
        else:
            text = page["text"]
            method = "direct"

        notice_result = process_notice(text)
        boxes = detect_notice_boxes(pdf_path, page_number)

        for box in boxes:
            box["notice_result"] = process_notice(box["text"])

        final_pages.append({
            "page_number": page_number,
            "method": method,
            "text": text,
            "notice_result": notice_result,
            "bounding_boxes": boxes,
        })

    return {
        "total_pages": direct_result["total_pages"],
        "pages": final_pages,
        "ocr_processed_pages": len(ocr_pages),
    }
