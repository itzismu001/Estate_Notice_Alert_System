
import cv2
import numpy as np
import pymupdf
import pytesseract
import re


def detect_notice_boxes(pdf_path, page_number):
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
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
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

        for column_number, heading in enumerate(headings, 1):

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

            horizontal_kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (max(40, int(CW * 0.55)), 1)
            )

            vertical_kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (1, max(25, int(CW * 0.15)))
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

                bx, by, bw, bh = cv2.boundingRect(contour)

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

            for candidate_number, (bx, by, bw, bh) in enumerate(boxes, 1):

                left = max(0, bx - 3)
                right = min(CW, bx + bw + 3)
                top = max(0, by - 12)
                bottom = min(CH, by + bh + 3)

                crop = column[top:bottom, left:right]

                if crop.size == 0:
                    continue

                crop_gray = cv2.cvtColor(
                    crop,
                    cv2.COLOR_BGR2GRAY
                )

                heading_part = crop_gray[
                    :min(150, crop_gray.shape[0]), :
                ]

                enlarged_heading = cv2.resize(
                    heading_part,
                    None,
                    fx=3,
                    fy=3,
                    interpolation=cv2.INTER_CUBIC
                )

                heading_text = pytesseract.image_to_string(
                    enlarged_heading,
                    config="--psm 6"
                )

                clean_heading = re.sub(
                    r"[^A-Z]",
                    "",
                    heading_text.upper()
                )

                body_part = crop_gray[
                    min(150, crop_gray.shape[0]):,
                    :
                ]

                body_text = ""

                if body_part.size > 0 and body_part.shape[0] >= 150:

                    enlarged_body = cv2.resize(
                        body_part,
                        None,
                        fx=2,
                        fy=2,
                        interpolation=cv2.INTER_CUBIC
                    )

                    body_text = pytesseract.image_to_string(
                        enlarged_body,
                        config="--oem 3 --psm 6"
                    ).strip()

                body_characters = len(
                    re.sub(
                        r"[^A-Za-z0-9]",
                        "",
                        body_text
                    )
                )

                is_complete_notice = (
                    "PUBLICNOTICE" in clean_heading[:100]
                    and crop_gray.shape[0] >= 300
                    and body_characters >= 80
                )

                if is_complete_notice:

                    # Convert image coordinates to PDF coordinates

                    results.append({
                        "page_number": page_number,
                        "column_number": column_number,
                        "bbox": {
                            "x0": (x1 + left) / 5,
                            "y0": (y + top) / 5,
                            "x1": (x1 + right) / 5,
                            "y1": (y + bottom) / 5
                        },
                        "text": body_text,
                        "status": "needs_review"
                    })

    return results
