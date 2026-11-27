"""Unified property measurement extraction and OCR comparison."""

from collections import Counter
from copy import deepcopy

from notices.services.agricultural_area_extractor import (
    extract_agricultural_areas,
)

from notices.services.incomplete_measurement_detector import (
    detect_incomplete_measurements,
)

from notices.services.standard_area_extractor import (
    extract_standard_areas,
)

from notices.services.standard_area_recovery import (
    recover_standard_areas,
)

from notices.services.kannada_area_refinement import (
    refine_kannada_areas,
)

from notices.services.directional_dimension_extractor import (
    extract_directional_dimensions,
)

from notices.services.kannada_dimension_recovery import (
    recover_kannada_dimensions,
)

from notices.services.extended_dimension_recovery import (
    recover_extended_dimensions,
)

from notices.services.dimension_context_classifier import (
    classify_dimension_candidates,
)

from notices.services.measurement_ocr_validator import (
    validate_measurements,
    measurement_safety,
)


def extract_source_measurements(raw_text):

    raw_text = raw_text or ""

    modules = {
        "agricultural": extract_agricultural_areas(raw_text),
        "standard": extract_standard_areas(raw_text),
        "standard_recovery": recover_standard_areas(raw_text),
        "kannada_refinement": refine_kannada_areas(raw_text),
        "incomplete": detect_incomplete_measurements(raw_text),
        "directional": extract_directional_dimensions(raw_text),
        "kannada_dimension": recover_kannada_dimensions(raw_text),
        "extended_dimension": recover_extended_dimensions(raw_text),
    }

    candidates = []
    dimensions = []
    module_counts = Counter()

    for name, result in modules.items():

        items = (
            result.get("measurement_candidates", [])
            + result.get("dimension_candidates", [])
            + result.get("ambiguous_candidates", [])
            + result.get("incomplete_candidates", [])
        )

        module_counts[name] = len(items)

        for original in items:

            item = deepcopy(original)
            item["extraction_module"] = name

            if name in {
                "directional",
                "kannada_dimension",
                "extended_dimension",
            }:
                dimensions.append(item)

            else:
                candidates.append(item)

    context = classify_dimension_candidates(
        raw_text,
        dimensions,
    )

    candidates.extend(context["classified_candidates"])

    for item in candidates:

        item.update(measurement_safety())

    candidates.sort(
        key=lambda item: item["start_offset"]
    )

    type_counts = Counter(
        item.get("measurement_type")
        for item in candidates
    )

    return {
        "raw_text": raw_text,
        "measurement_candidates": candidates,
        "candidate_count": len(candidates),
        "module_counts": dict(module_counts),
        "type_counts": dict(type_counts),
        "dimension_context": context,
        "module_results": modules,
        "selected_measurement": None,
        "property_association_pending": True,
        "area_role_classification_pending": True,
        **measurement_safety(),
    }


def extract_unified_measurements(
    primary_text,
    secondary_text=None,
):

    primary = extract_source_measurements(primary_text)

    secondary = None

    if secondary_text and secondary_text.strip():

        secondary = extract_source_measurements(
            secondary_text
        )

    validation = validate_measurements(
        primary["measurement_candidates"],
        (
            secondary["measurement_candidates"]
            if secondary is not None else None
        ),
    )

    secondary_count = (
        secondary["candidate_count"]
        if secondary is not None else 0
    )

    return {
        "primary": primary,
        "secondary": secondary,
        "secondary_available": secondary is not None,
        "primary_candidate_count": primary["candidate_count"],
        "secondary_candidate_count": secondary_count,
        "total_candidate_occurrences": (
            primary["candidate_count"] + secondary_count
        ),
        "measurement_validation": validation,
        "selected_measurement": None,
        "property_association_pending": True,
        "area_role_classification_pending": True,
        **measurement_safety(),
    }
