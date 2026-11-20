from notices.services.detector import detect_notice
from notices.services.field_extractor import extract_notice_fields


def process_notice(text):

    detection = detect_notice(text)

    result = {
        "detection": detection,
        "fields": None,
        "raw_text": text,
    }

    if detection["is_notice"]:
        result["fields"] = extract_notice_fields(text)

    return result
