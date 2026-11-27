
import cv2
import numpy as np
import pymupdf
import pytesseract

from notices.services.detector import detect_notice


# ==================================================
# PHYSICAL ADVERTISEMENT BORDER DETECTION
# ==================================================

def detect_advertisement_boxes(image):

    height, width = image.shape[:2]

    if image.ndim == 3:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

    else:

        gray = image.copy()

    # Convert to binary image.

    binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV
        + cv2.THRESH_OTSU
    )[1]

    # Detect horizontal lines.

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(20, width // 35), 1)
    )

    horizontal_lines = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        horizontal_kernel
    )

    # Detect vertical lines.

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, max(20, height // 65))
    )

    vertical_lines = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        vertical_kernel
    )

    # Combine horizontal and vertical borders.

    combined = cv2.bitwise_or(
        horizontal_lines,
        vertical_lines
    )

    combined = cv2.morphologyEx(
        combined,
        cv2.MORPH_CLOSE,
        np.ones((3, 3), dtype=np.uint8)
    )

    contours, _ = cv2.findContours(
        combined,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    for contour in contours:

        x, y, w, h = cv2.boundingRect(contour)

        # Ignore very small regions.

        if w < width * 0.065:
            continue

        if h < height * 0.065:
            continue

        # Ignore nearly full-page regions.

        if w > width * 0.96:
            continue

        if h > height * 0.96:
            continue

        rectangle_area = w * h

        if rectangle_area <= 0:
            continue

        rectangularity = (
            cv2.contourArea(contour)
            / rectangle_area
        )

        if rectangularity < 0.75:
            continue

        candidates.append((x, y, w, h))

    return remove_nested_boxes(candidates)


# ==================================================
# REMOVE NESTED AND DUPLICATE REGIONS
# ==================================================

def remove_nested_boxes(candidates):

    candidates = sorted(
        candidates,
        key=lambda box: box[2] * box[3],
        reverse=True
    )

    final_boxes = []

    for x, y, w, h in candidates:

        duplicate = False

        for X, Y, W, H in final_boxes:

            intersection_width = max(
                0,
                min(x + w, X + W)
                - max(x, X)
            )

            intersection_height = max(
                0,
                min(y + h, Y + H)
                - max(y, Y)
            )

            intersection_area = (
                intersection_width
                * intersection_height
            )

            coverage = (
                intersection_area / (w * h)
            )

            if coverage >= 0.93:

                duplicate = True

                break

        if not duplicate:

            final_boxes.append((x, y, w, h))

    return sorted(
        final_boxes,
        key=lambda box: (box[1], box[0])
    )


# ==================================================
# PDF PAGE RENDERING
# ==================================================

def render_page(page, scale=3):

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(scale, scale),
        colorspace=pymupdf.csRGB,
        alpha=False
    )

    image = np.frombuffer(
        pixmap.samples,
        dtype=np.uint8
    ).reshape(
        pixmap.height,
        pixmap.width,
        3
    )

    image = cv2.cvtColor(
        image,
        cv2.COLOR_RGB2BGR
    )

    return image, pixmap


# ==================================================
# STANDARDIZE IMAGE RESOLUTION
# ==================================================

def resize_for_detection(image, target_height=2048):

    height, width = image.shape[:2]

    scale = target_height / height

    resized = cv2.resize(
        image,
        (
            round(width * scale),
            target_height
        ),
        interpolation=(
            cv2.INTER_AREA
            if scale < 1
            else cv2.INTER_LINEAR
        )
    )

    return resized


# ==================================================
# INDIVIDUAL REGION OCR
# ==================================================

def extract_region_text(image, language="eng"):

    if image.size == 0:
        return ""

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    height, width = gray.shape

    scale = min(
        2.0,
        4500 / max(height, width)
    )

    enlarged = cv2.resize(
        gray,
        None,
        fx=scale,
        fy=scale,
        interpolation=(
            cv2.INTER_CUBIC
            if scale > 1
            else cv2.INTER_AREA
        )
    )

    text = pytesseract.image_to_string(
        enlarged,
        lang=language,
        config="--oem 3 --psm 6",
        timeout=90
    )

    return text.strip()


# ==================================================
# PIXEL TO PDF COORDINATE CONVERSION
# ==================================================

def pixels_to_pdf_bbox(
    page,
    pixmap,
    x0,
    y0,
    x1,
    y1,
    render_scale
):

    rect = pymupdf.Rect(
        (x0 + pixmap.x) / render_scale,
        (y0 + pixmap.y) / render_scale,
        (x1 + pixmap.x) / render_scale,
        (y1 + pixmap.y) / render_scale
    )

    # Match existing detector coordinate convention.

    rect = rect * page.derotation_matrix

    return {
        "x0": float(rect.x0),
        "y0": float(rect.y0),
        "x1": float(rect.x1),
        "y1": float(rect.y1)
    }


# ==================================================
# MAIN BORDER-FIRST NOTICE DETECTOR
# ==================================================

def detect_border_notice_boxes(
    pdf_path,
    page_number,
    language="eng"
):

    results = []

    render_scale = 3

    with pymupdf.open(pdf_path) as document:

        if page_number < 1 or page_number > len(document):

            raise ValueError("Invalid page number")

        page = document[page_number - 1]

        original_image, pixmap = render_page(
            page,
            scale=render_scale
        )

        working_image = resize_for_detection(
            original_image
        )

        boxes = detect_advertisement_boxes(
            working_image
        )

        original_height, original_width = (
            original_image.shape[:2]
        )

        working_height, working_width = (
            working_image.shape[:2]
        )

        x_scale = original_width / working_width

        y_scale = original_height / working_height

        for region_number, (x, y, w, h) in enumerate(
            boxes, 1
        ):

            # Map coordinates to the original image.

            x0 = max(
                0,
                int(x * x_scale)
            )

            y0 = max(
                0,
                int(y * y_scale)
            )

            x1 = min(
                original_width,
                int(np.ceil((x + w) * x_scale))
            )

            y1 = min(
                original_height,
                int(np.ceil((y + h) * y_scale))
            )

            crop = original_image[
                y0:y1,
                x0:x1
            ]

            if crop.size == 0:
                continue

            # Perform OCR within the individual region.

            text = extract_region_text(
                crop,
                language=language
            )

            if not text:
                continue

            # Use existing English property classifier.

            detection = detect_notice(text)

            if not detection.get("is_notice"):
                continue

            bbox = pixels_to_pdf_bbox(
                page,
                pixmap,
                x0,
                y0,
                x1,
                y1,
                render_scale
            )

            results.append({

                "page_number": page_number,

                "column_number": None,

                "region_number": region_number,

                "bbox": bbox,

                "text": text,

                "status": "needs_review",

                "detection_method": "border_first",

                "ocr_language": language,

            })

    return results
