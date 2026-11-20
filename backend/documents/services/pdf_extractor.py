import pymupdf
from pathlib import Path


def extract_pdf_text(pdf_path, min_characters=80, min_words=10):
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError("PDF file not found")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("File must be a PDF")

    results = []
    ocr_required_pages = []

    with pymupdf.open(pdf_path) as document:

        for page_number, page in enumerate(document, start=1):

            text = page.get_text("text").strip()

            character_count = len(text)
            word_count = len(text.split())

            needs_ocr = (
                character_count < min_characters
                or word_count < min_words
            )

            page_result = {
                "page_number": page_number,
                "method": "direct",
                "text": text,
                "character_count": character_count,
                "word_count": word_count,
                "status": "ocr_required" if needs_ocr else "success",
            }

            results.append(page_result)

            if needs_ocr:
                ocr_required_pages.append(page_number)

    return {
        "total_pages": len(results),
        "pages": results,
        "ocr_required_pages": ocr_required_pages,
    }
