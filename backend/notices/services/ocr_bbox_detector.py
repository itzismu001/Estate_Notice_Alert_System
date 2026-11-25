
import pymupdf
import pytesseract

from PIL import Image
from pytesseract import Output


def extract_ocr_text_blocks(
    pdf_path,
    page_number,
    scale=3
):
    """
    Extract OCR text lines with bounding-box
    coordinates expressed in PDF points.
    """

    with pymupdf.open(pdf_path) as document:

        if page_number < 1 or page_number > len(document):
            raise ValueError("Invalid page number")

        page = document[page_number - 1]

        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(scale, scale),
            colorspace=pymupdf.csRGB,
            alpha=False
        )

        image = Image.frombytes(
            "RGB",
            (pix.width, pix.height),
            pix.samples
        )

        data = pytesseract.image_to_data(
            image,
            lang="eng",
            config="--psm 3",
            output_type=Output.DICT
        )

        lines = {}

        # Group OCR words into individual lines.

        for i in range(len(data["text"])):

            text = data["text"][i].strip()

            if not text:
                continue

            key = (
                data["block_num"][i],
                data["par_num"][i],
                data["line_num"][i]
            )

            x0 = data["left"][i]
            y0 = data["top"][i]

            x1 = x0 + data["width"][i]
            y1 = y0 + data["height"][i]

            word = {
                "text": text,
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1
            }

            lines.setdefault(key, []).append(word)

        blocks = []

        # Convert OCR lines into the existing
        # PyMuPDF text-block structure.

        for block_number, words in enumerate(
            lines.values()
        ):

            words.sort(key=lambda word: word["x0"])

            text = " ".join(
                word["text"] for word in words
            )

            x0 = min(word["x0"] for word in words)
            y0 = min(word["y0"] for word in words)
            x1 = max(word["x1"] for word in words)
            y1 = max(word["y1"] for word in words)

            # Convert pixel coordinates to PDF points.

            rect = pymupdf.Rect(
                (x0 + pix.x) / scale,
                (y0 + pix.y) / scale,
                (x1 + pix.x) / scale,
                (y1 + pix.y) / scale
            )

            # Match PyMuPDF's unrotated coordinates.
            rect = rect * page.derotation_matrix

            blocks.append((
                rect.x0,
                rect.y0,
                rect.x1,
                rect.y1,
                text,
                block_number,
                0
            ))

        # Sort from top to bottom, left to right.

        blocks.sort(
            key=lambda block: (block[1], block[0])
        )

        return blocks
