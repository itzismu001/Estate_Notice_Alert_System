
import re
import unicodedata


# ==================================================
# CONFIGURATION
# ==================================================

NUMERAL_TRANSLATION = str.maketrans(
    "೦೧೨೩೪೫೬೭೮೯",
    "0123456789"
)

IDENTIFIER_FIELDS = (
    "survey_numbers",
    "site_numbers",
    "khata_numbers",
    "pid_numbers",
    "document_numbers",
    "property_numbers",
    "plot_numbers",
    "hissa_numbers",
    "subdivision_numbers",
    "municipal_numbers",
    "flat_numbers",
    "tp_numbers",
    "khasra_numbers",
    "registration_numbers",
    "assessment_numbers"
)


# ==================================================
# VALUE NORMALIZATION
# ==================================================

def normalize_value(value):

    if value is None:
        return None

    value = unicodedata.normalize(
        "NFC",
        str(value)
    )

    value = value.translate(
        NUMERAL_TRANSLATION
    )

    value = value.replace("\u200c", "")
    value = value.replace("\u200d", "")

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    return value or None


def normalize_values(values):

    if values is None:
        return []

    if isinstance(values, (str, int, float)):
        values = [values]

    normalized = []

    for value in values:

        value = normalize_value(value)

        if value is not None:
            normalized.append(value)

    return sorted(set(normalized))


# ==================================================
# IDENTIFIER CANDIDATE RETRIEVAL
# ==================================================

def get_identifier_candidates(fields, field):

    fields = fields or {}

    candidates = fields.get(field) or []

    if not candidates:

        evidence = fields.get(
            "identifier_candidates"
        ) or {}

        candidates = evidence.get(
            field,
            []
        )

    return normalize_values(candidates)


# ==================================================
# BASIC IDENTIFIER FORMAT VALIDATION
# ==================================================

def identifier_format_error(value):

    if not value:
        return "EMPTY_IDENTIFIER"

    if value.endswith(("/", "-")):
        return "INCOMPLETE_IDENTIFIER"

    if value.startswith(("/", "-")):
        return "INVALID_IDENTIFIER_PREFIX"

    if re.search(r"[/\-]{2,}", value):
        return "REPEATED_IDENTIFIER_SEPARATOR"

    if not re.search(r"\d", value):
        return "IDENTIFIER_WITHOUT_NUMBER"

    return None


# ==================================================
# RETRIEVE INVALID IDENTIFIER EVIDENCE
# ==================================================

def get_invalid_evidence(fields, field):

    fields = fields or {}

    records = fields.get(
        "invalid_subject_identifiers"
    ) or []

    return [

        record

        for record in records

        if record.get("field") == field
    ]


# ==================================================
# GENERIC OCR VALUE COMPARISON
# ==================================================

def compare_ocr_values(values_a, values_b):

    source_a = normalize_values(values_a)

    source_b = normalize_values(values_b)

    candidates = sorted(
        set(source_a) | set(source_b)
    )

    selected_value = None

    if not candidates:

        status = "NOT_FOUND"

    elif not source_a or not source_b:

        status = "SINGLE_SOURCE"

    elif source_a != source_b:

        status = "CONFLICT"

    elif len(candidates) == 1:

        status = "CONSISTENT_UNVERIFIED"

        selected_value = candidates[0]

    else:

        status = "MULTIPLE_CANDIDATES"

    return {

        "status": status,

        "selected_value": selected_value,

        "source_a_candidates": source_a,

        "source_b_candidates": source_b,

        "all_candidates": candidates,

        "requires_review": bool(candidates),

        "verified": False
    }


# ==================================================
# IDENTIFIER-SPECIFIC VALIDATION
# ==================================================

def compare_identifier_values(
    values_a,
    values_b,
    invalid_a=None,
    invalid_b=None
):

    result = compare_ocr_values(
        values_a,
        values_b
    )

    invalid_a = list(invalid_a or [])
    invalid_b = list(invalid_b or [])

    for values, invalid_records in [

        (
            result["source_a_candidates"],
            invalid_a
        ),

        (
            result["source_b_candidates"],
            invalid_b
        )
    ]:

        for value in values:

            error = identifier_format_error(
                value
            )

            if error:

                invalid_records.append({

                    "value": value,

                    "reason": error,

                    "verified": False
                })

    result["source_a_invalid_evidence"] = (
        invalid_a
    )

    result["source_b_invalid_evidence"] = (
        invalid_b
    )

    if invalid_a or invalid_b:

        result["status"] = (
            "INVALID_IDENTIFIER"
        )

        result["selected_value"] = None

        result["requires_review"] = True

        invalid_values = [

            record.get("value")

            for record in invalid_a + invalid_b
        ]

        result["invalid_candidates"] = (
            normalize_values(invalid_values)
        )

    else:

        result["invalid_candidates"] = []

    return result


# ==================================================
# MEASUREMENT AND UNIT COMPARISON
# ==================================================

def measurement_candidates(
    fields,
    value_key,
    unit_key
):

    value = normalize_value(
        fields.get(value_key)
    )

    unit = normalize_value(
        fields.get(unit_key)
    )

    if value is None:
        return []

    if unit is None:
        return [f"{value} UNKNOWN_UNIT"]

    return [f"{value} {unit}"]


# ==================================================
# BOUNDARY IDENTIFIER VALIDATION
# ==================================================

def validate_boundary_identifiers(
    fields_a,
    fields_b
):

    boundary_a = (
        fields_a.get("boundary_identifiers")
        or {}
    )

    boundary_b = (
        fields_b.get("boundary_identifiers")
        or {}
    )

    invalid_a = (
        fields_a.get(
            "invalid_boundary_identifiers"
        ) or []
    )

    invalid_b = (
        fields_b.get(
            "invalid_boundary_identifiers"
        ) or []
    )

    field_names = (

        set(boundary_a)

        | set(boundary_b)

        | {
            item["field"]

            for item in invalid_a + invalid_b

            if item.get("field")
        }
    )

    validations = {}

    for field in sorted(field_names):

        validations[field] = (
            compare_identifier_values(

                boundary_a.get(field, []),

                boundary_b.get(field, []),

                invalid_a=[

                    item for item in invalid_a

                    if item.get("field") == field
                ],

                invalid_b=[

                    item for item in invalid_b

                    if item.get("field") == field
                ]
            )
        )

    return validations


# ==================================================
# COMPLETE OCR FIELD VALIDATION
# ==================================================

def validate_extracted_fields(
    fields_a,
    fields_b,
    source_a="kan",
    source_b="kan+eng"
):

    fields_a = fields_a or {}
    fields_b = fields_b or {}

    validations = {}

    # ----------------------------------------------
    # Subject property identifiers
    # ----------------------------------------------

    for field in IDENTIFIER_FIELDS:

        validations[field] = (
            compare_identifier_values(

                get_identifier_candidates(
                    fields_a,
                    field
                ),

                get_identifier_candidates(
                    fields_b,
                    field
                ),

                invalid_a=get_invalid_evidence(
                    fields_a,
                    field
                ),

                invalid_b=get_invalid_evidence(
                    fields_b,
                    field
                )
            )
        )

    # ----------------------------------------------
    # Property area
    # ----------------------------------------------

    validations["property_area"] = (
        compare_ocr_values(

            measurement_candidates(

                fields_a,

                "property_area",

                "property_area_unit"
            ),

            measurement_candidates(

                fields_b,

                "property_area",

                "property_area_unit"
            )
        )
    )

    # ----------------------------------------------
    # Response deadline
    # ----------------------------------------------

    validations["response_deadline"] = (
        compare_ocr_values(

            measurement_candidates(

                fields_a,

                "response_deadline",

                "response_deadline_unit"
            ),

            measurement_candidates(

                fields_b,

                "response_deadline",

                "response_deadline_unit"
            )
        )
    )

    # ----------------------------------------------
    # Boundary values remain separate from subject
    # property identifiers.
    # ----------------------------------------------

    boundary_validations = (
        validate_boundary_identifiers(

            fields_a,

            fields_b
        )
    )

    conflicts = []
    single_source_fields = []
    multiple_candidate_fields = []
    consistent_fields = []
    invalid_fields = []

    for field, result in validations.items():

        status = result["status"]

        if status == "CONFLICT":

            conflicts.append(field)

        elif status == "SINGLE_SOURCE":

            single_source_fields.append(field)

        elif status == "MULTIPLE_CANDIDATES":

            multiple_candidate_fields.append(
                field
            )

        elif status == "CONSISTENT_UNVERIFIED":

            consistent_fields.append(field)

        elif status == "INVALID_IDENTIFIER":

            invalid_fields.append(field)

    boundary_review_fields = [

        field

        for field, result in
        boundary_validations.items()

        if result["status"] in (

            "CONFLICT",

            "SINGLE_SOURCE",

            "MULTIPLE_CANDIDATES",

            "INVALID_IDENTIFIER"
        )
    ]

    # ----------------------------------------------
    # Review reasons
    # ----------------------------------------------

    review_reasons = []

    for field in conflicts:

        review_reasons.append(
            f"OCR conflict in {field}"
        )

    for field in single_source_fields:

        review_reasons.append(
            f"Single-source extraction in {field}"
        )

    for field in multiple_candidate_fields:

        review_reasons.append(
            f"Multiple candidates in {field}"
        )

    for field in invalid_fields:

        review_reasons.append(
            f"Invalid identifier evidence in {field}"
        )

    for field in boundary_review_fields:

        review_reasons.append(
            f"Boundary identifier review: {field}"
        )

    if consistent_fields:

        review_reasons.append(
            "OCR agreement requires human verification"
        )

    return {

        "source_a": source_a,

        "source_b": source_b,

        "validations": validations,

        "boundary_validations": (
            boundary_validations
        ),

        "conflicting_fields": conflicts,

        "single_source_fields": (
            single_source_fields
        ),

        "multiple_candidate_fields": (
            multiple_candidate_fields
        ),

        "consistent_fields": consistent_fields,

        "invalid_fields": invalid_fields,

        "boundary_review_fields": (
            boundary_review_fields
        ),

        "has_conflicts": bool(conflicts),

        "has_invalid_identifiers": bool(
            invalid_fields
        ),

        "requires_review": True,

        "verified": False,

        "review_reasons": review_reasons
    }
