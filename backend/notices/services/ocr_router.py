
import cv2
import pytesseract

from time import perf_counter

from notices.services.multilingual_processor import (
    identify_language,
    process_multilingual_notice
)


# ==================================================
# OCR LANGUAGE AVAILABILITY
# ==================================================

def check_ocr_languages():

    installed_languages = set(
        pytesseract.get_languages(config="")
    )

    required_languages = {
        "eng",
        "kan"
    }

    missing_languages = (
        required_languages
        - installed_languages
    )

    return {

        "available": sorted(
            installed_languages
        ),

        "missing": sorted(
            missing_languages
        ),

        "multilingual_ready": (
            not missing_languages
        )
    }


# ==================================================
# IMAGE PREPROCESSING
# ==================================================

def prepare_ocr_image(image):

    if image is None or image.size == 0:

        raise ValueError(
            "Invalid or empty OCR image"
        )

    if image.ndim == 3:

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

    else:

        gray = image.copy()

    height, width = gray.shape

    scale = min(

        3.0,

        4500 / max(height, width)
    )

    target_width = max(
        1,
        round(width * scale)
    )

    target_height = max(
        1,
        round(height * scale)
    )

    prepared = cv2.resize(

        gray,

        (target_width, target_height),

        interpolation=(

            cv2.INTER_CUBIC

            if scale > 1

            else cv2.INTER_AREA
        )
    )

    return prepared


# ==================================================
# SINGLE OCR EXECUTION
# ==================================================

def run_ocr(image, language):

    start = perf_counter()

    text = pytesseract.image_to_string(

        image,

        lang=language,

        config="--oem 3 --psm 6",

        timeout=90
    ).strip()

    return {

        "language": language,

        "text": text,

        "processing_seconds": round(

            perf_counter() - start,

            4
        ),

        "language_info": identify_language(
            text
        )
    }


# ==================================================
# SECONDARY OCR LANGUAGE SELECTION
# ==================================================

def select_secondary_language(text):

    info = identify_language(text)

    language = info["language"]

    if language == "en":

        return "eng"

    if language == "kn":

        return "kan"

    if language == "mixed":

        if info["kannada_ratio"] >= 0.5:

            return "kan"

        return "eng"

    return None


# ==================================================
# MULTILINGUAL IMAGE PROCESSING
# ==================================================

def process_notice_image(
    image,
    validate_secondary=True
):

    start = perf_counter()

    language_status = check_ocr_languages()

    if not language_status["multilingual_ready"]:

        raise RuntimeError(

            "Missing OCR languages: "

            + ", ".join(
                language_status["missing"]
            )
        )

    prepared_image = prepare_ocr_image(
        image
    )

    # ----------------------------------------------
    # Primary bilingual OCR.
    # ----------------------------------------------

    primary_ocr = run_ocr(

        prepared_image,

        language="kan+eng"
    )

    preliminary = process_multilingual_notice(

        primary_ocr["text"],

        primary_ocr_language="kan+eng"
    )

    secondary_ocr = None

    secondary_error = None

    result = preliminary

    # ----------------------------------------------
    # Secondary OCR for relevant candidates.
    # ----------------------------------------------

    if (

        validate_secondary

        and preliminary["retain_candidate"]
    ):

        secondary_language = (
            select_secondary_language(
                primary_ocr["text"]
            )
        )

        if secondary_language:

            try:

                secondary_ocr = run_ocr(

                    prepared_image,

                    language=secondary_language
                )

            except RuntimeError as error:

                secondary_error = str(error)

            if secondary_ocr is not None:

                result = process_multilingual_notice(

                    primary_ocr["text"],

                    secondary_text=(
                        secondary_ocr["text"]
                    ),

                    primary_ocr_language="kan+eng",

                    secondary_ocr_language=(
                        secondary_language
                    )
                )

    # ----------------------------------------------
    # Preserve OCR provenance.
    # ----------------------------------------------

    result["ocr_metadata"] = {

        "primary": primary_ocr,

        "secondary": secondary_ocr,

        "secondary_error": secondary_error,

        "secondary_validation_requested": (
            validate_secondary
        ),

        "secondary_validation_completed": (

            secondary_ocr is not None
        ),

        "ocr_passes": (

            2 if secondary_ocr is not None

            else 1
        ),

        "total_processing_seconds": round(

            perf_counter() - start,

            4
        )
    }

    return result
