
import cv2
import numpy as np
import pymupdf
import pytesseract
import re

from notices.services.detector import detect_notice


# ==================================================
# STRATEGY 1: SCANNED PDF NOTICE DETECTION
# ==================================================

def detect_scanned_notice_boxes(pdf_path, page_number):

    results = []

    with pymupdf.open(pdf_path) as document:

        if page_number < 1 or page_number > len(document):
            raise ValueError("Invalid page number")

        page = document[page_number - 1]

        # -----------------------------------
        # STEP 1: Render page at 2x
        # -----------------------------------

        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(2, 2),
            alpha=False
        )

        image = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        ).reshape(
            pix.height,
            pix.width,
            3
        ).copy()

        image = cv2.cvtColor(
            image,
            cv2.COLOR_RGB2BGR
        )

        H, W = image.shape[:2]

        # -----------------------------------
        # STEP 2: Detect purple notice headings
        # -----------------------------------

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV
        )

        lower = np.array([120, 55, 40])
        upper = np.array([165, 255, 255])

        mask = cv2.inRange(
            hsv,
            lower,
            upper
        )

        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (5, 3)
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            kernel
        )

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        headings = []

        for contour in contours:

            x, y, w, h = cv2.boundingRect(contour)

            if w < W * 0.035 or h < H * 0.004:
                continue

            if h > H * 0.06 or w / h < 2.5:
                continue

            crop = image[y:y+h, x:x+w]

            gray = cv2.cvtColor(
                crop,
                cv2.COLOR_BGR2GRAY
            )

            enlarged = cv2.resize(
                gray,
                None,
                fx=3,
                fy=3,
                interpolation=cv2.INTER_CUBIC
            )

            _, binary = cv2.threshold(
                enlarged,
                0,
                255,
                cv2.THRESH_BINARY_INV
                + cv2.THRESH_OTSU
            )

            text = pytesseract.image_to_string(
                binary,
                config="--psm 7"
            ).strip()

            clean = re.sub(
                r"[^A-Z]",
                "",
                text.upper()
            )

            if "PUBLICNOTICE" in clean:

                headings.append({
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h
                })

        # -----------------------------------
        # STEP 3: Render page at 5x
        # -----------------------------------

        if not headings:
            return results

        pix = page.get_pixmap(
            matrix=pymupdf.Matrix(5, 5),
            alpha=False
        )

        image = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        ).reshape(
            pix.height,
            pix.width,
            3
        ).copy()

        image = cv2.cvtColor(
            image,
            cv2.COLOR_RGB2BGR
        )

        H, W = image.shape[:2]

        scale = 5 / 2

        headings = sorted(
            headings,
            key=lambda b: (b["y"], b["x"])
        )

        # -----------------------------------
        # STEP 4: Extract columns
        # -----------------------------------

        for column_number, heading in enumerate(
            headings, 1
        ):

            x = int(heading["x"] * scale)
            y = int(heading["y"] * scale)
            w = int(heading["width"] * scale)

            x1 = max(0, x - 8)
            x2 = min(W, x + w + 8)

            column = image[y:H, x1:x2]

            if column.size == 0:
                continue

            gray = cv2.cvtColor(
                column,
                cv2.COLOR_BGR2GRAY
            )

            _, binary = cv2.threshold(
                gray,
                160,
                255,
                cv2.THRESH_BINARY_INV
            )

            CW = column.shape[1]
            CH = column.shape[0]

            # -----------------------------------
            # STEP 5: Detect notice borders
            # -----------------------------------

            horizontal_kernel = (
                cv2.getStructuringElement(
                    cv2.MORPH_RECT,
                    (max(40, int(CW * 0.55)), 1)
                )
            )

            vertical_kernel = (
                cv2.getStructuringElement(
                    cv2.MORPH_RECT,
                    (1, max(25, int(CW * 0.15)))
                )
            )

            horizontal = cv2.morphologyEx(
                binary,
                cv2.MORPH_OPEN,
                horizontal_kernel
            )

            vertical = cv2.morphologyEx(
                binary,
                cv2.MORPH_OPEN,
                vertical_kernel
            )

            borders = cv2.bitwise_or(
                horizontal,
                vertical
            )

            borders = cv2.morphologyEx(
                borders,
                cv2.MORPH_CLOSE,
                np.ones((3, 3), np.uint8)
            )

            contours, _ = cv2.findContours(
                borders,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            boxes = []

            for contour in contours:

                bx, by, bw, bh = (
                    cv2.boundingRect(contour)
                )

                if bw < CW * 0.70:
                    continue

                if bh < CH * 0.04:
                    continue

                if bh > CH * 0.92:
                    continue

                boxes.append((bx, by, bw, bh))

            boxes.sort(
                key=lambda b: (b[1], b[0])
            )

            # -----------------------------------
            # STEP 6: Validate notice candidates
            # -----------------------------------

            for candidate_number, (
                bx, by, bw, bh
            ) in enumerate(boxes, 1):

                left = max(0, bx - 3)
                right = min(CW, bx + bw + 3)

                top = max(0, by - 12)
                bottom = min(CH, by + bh + 3)

                crop = column[
                    top:bottom,
                    left:right
                ]

                if crop.size == 0:
                    continue

                crop_gray = cv2.cvtColor(
                    crop,
                    cv2.COLOR_BGR2GRAY
                )

                # Extract the complete notice region.
                # Preserve heading and opening paragraphs.

                enlarged_crop = cv2.resize(
                    crop_gray,
                    None,
                    fx=1.2,
                    fy=1.2,
                    interpolation=cv2.INTER_CUBIC
                )

                full_text = pytesseract.image_to_string(
                    enlarged_crop,
                    lang="eng",
                    config="--oem 3 --psm 6"
                ).strip()

                if not full_text:
                    continue

                # Validate the complete extracted text.

                detection = detect_notice(full_text)

                if not detection["is_notice"]:
                    continue

                # Convert rendered pixel coordinates
                # into unrotated PDF coordinates.

                rect = pymupdf.Rect(
                    (x1 + left + pix.x) / 5,
                    (y + top + pix.y) / 5,
                    (x1 + right + pix.x) / 5,
                    (y + bottom + pix.y) / 5
                )

                rect = rect * page.derotation_matrix

                results.append({
                    "page_number": page_number,
                    "column_number": column_number,
                    "bbox": {
                        "x0": float(rect.x0),
                        "y0": float(rect.y0),
                        "x1": float(rect.x1),
                        "y1": float(rect.y1)
                    },
                    "text": full_text,
                    "status": "needs_review"
                })

    return results


# ==================================================
# STRATEGY 2: SPATIAL TEXT BLOCK GROUPING
# ==================================================

def group_text_blocks(
    blocks,
    max_vertical_gap=25
):

    groups = []

    for block in blocks:

        # Ignore non-text blocks.
        if block[6] != 0:
            continue

        x0, y0, x1, y1, text = block[:5]

        text = text.strip()

        if not text:
            continue

        current = {
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "text": text,
        }

        matched_group = None

        # A new notice heading starts a new group.

        is_heading = bool(
            re.match(
                r"^(PUBLIC\s+NOTICE|LEGAL\s+NOTICE)\b",
                text,
                re.IGNORECASE
            )
        )

        if not is_heading:

            for group in reversed(groups):

                vertical_gap = (
                    y0 - group["y1"]
                )

                horizontal_overlap = max(
                    0,
                    min(x1, group["x1"])
                    - max(x0, group["x0"])
                )

                minimum_width = min(
                    x1 - x0,
                    group["x1"] - group["x0"]
                )

                same_column = (
                    minimum_width > 0
                    and horizontal_overlap
                    / minimum_width >= 0.5
                    and abs(x0 - group["x0"]) <= 25
                )

                if (
                    same_column
                    and 0 <= vertical_gap
                    <= max_vertical_gap
                ):

                    matched_group = group
                    break

        # Merge matching blocks.

        if matched_group is not None:

            matched_group["x0"] = min(
                matched_group["x0"], x0
            )

            matched_group["y0"] = min(
                matched_group["y0"], y0
            )

            matched_group["x1"] = max(
                matched_group["x1"], x1
            )

            matched_group["y1"] = max(
                matched_group["y1"], y1
            )

            matched_group["text"] += (
                "\n" + text
            )

        else:

            groups.append(current)

    return groups


# ==================================================
# STRATEGY 3: SELECTABLE-TEXT NOTICE DETECTION
# ==================================================

def detect_text_notice_boxes(
    pdf_path,
    page_number
):

    results = []

    with pymupdf.open(pdf_path) as document:

        if page_number < 1 or page_number > len(document):
            raise ValueError("Invalid page number")

        page = document[page_number - 1]

        # Extract text blocks with PDF coordinates.

        blocks = page.get_text(
            "blocks",
            sort=True
        )

        # Combine nearby blocks belonging
        # to the same potential notice.

        groups = group_text_blocks(blocks)

        for group in groups:

            detection = detect_notice(
                group["text"]
            )

            if not detection["is_notice"]:
                continue

            results.append({
                "page_number": page_number,
                "column_number": None,
                "bbox": {
                    "x0": float(group["x0"]),
                    "y0": float(group["y0"]),
                    "x1": float(group["x1"]),
                    "y1": float(group["y1"]),
                },
                "text": group["text"],
                "status": "needs_review",
            })

    return results


# ==================================================
# MAIN HYBRID BOUNDING-BOX DETECTOR
# ==================================================

def detect_ocr_notice_boxes(pdf_path, page_number):

    from notices.services.ocr_bbox_detector import (
        extract_ocr_text_blocks
    )

    blocks = extract_ocr_text_blocks(
        pdf_path,
        page_number
    )

    groups = group_text_blocks(blocks)

    results = []

    for group in groups:

        detection = detect_notice(group["text"])

        if not detection["is_notice"]:
            continue

        results.append({
            "page_number": page_number,
            "column_number": None,
            "bbox": {
                "x0": float(group["x0"]),
                "y0": float(group["y0"]),
                "x1": float(group["x1"]),
                "y1": float(group["y1"]),
            },
            "text": group["text"],
            "status": "needs_review",
        })

    return results


def detect_notice_boxes(pdf_path, page_number):

    # Strategy 1: Selectable-text detection.

    text_boxes = detect_text_notice_boxes(
        pdf_path,
        page_number
    )

    if text_boxes:
        return text_boxes

    # Strategy 2: General OCR coordinate detection.

    ocr_boxes = detect_ocr_notice_boxes(
        pdf_path,
        page_number
    )

    if ocr_boxes:
        return ocr_boxes

    # Strategy 3: Original colour and border detector.

    return detect_scanned_notice_boxes(
        pdf_path,
        page_number
    )
