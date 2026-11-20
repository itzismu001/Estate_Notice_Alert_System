import pymupdf


def detect_notice_boxes(pdf_path, page_number):
    results = []

    with pymupdf.open(pdf_path) as document:
        if page_number < 1 or page_number > len(document):
            raise ValueError("Invalid page number")

        page = document[page_number - 1]

        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            text = ""

            for line in block["lines"]:
                for span in line["spans"]:
                    text += span["text"] + " "

            text = text.strip()

            if not text:
                continue

            lower_text = text.lower()

            if (
                "public notice" in lower_text
                or "legal notice" in lower_text
                or "court notice" in lower_text
            ):
                x0, y0, x1, y1 = block["bbox"]

                results.append({
                    "page_number": page_number,
                    "bbox": {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                    },
                    "text": text,
                })

    return results
