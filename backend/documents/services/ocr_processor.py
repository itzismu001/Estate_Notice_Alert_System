import pymupdf
import pytesseract
from PIL import Image
from pathlib import Path
import io


def process_ocr_pages(pdf_path, page_numbers):
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError("PDF file not found")

    results = []

    with pymupdf.open(pdf_path) as document:

        for page_number in page_numbers:

            if page_number < 1 or page_number > len(document):
                continue

            page = document[page_number - 1]

            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                alpha=False
            )

            image = Image.open(
                io.BytesIO(pix.tobytes("png"))
            )

            text = pytesseract.image_to_string(
                image,
                lang="eng",
                config="--oem 3 --psm 3"
            ).strip()

            results.append({
                "page_number": page_number,
                "method": "ocr",
                "text": text,
                "character_count": len(text),
                "status": "success" if text else "failed",
            })

    return results
