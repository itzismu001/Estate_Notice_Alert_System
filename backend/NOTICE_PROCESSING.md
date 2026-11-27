# Estate Notice Alert System
## Notice Processing Module - Technical Handover

### 1. Overview

The notice processing module extracts property-related
legal notice candidates from newspaper PDF documents.

It supports English, Kannada and mixed-language notices.

### 2. Processing capabilities

- Direct PDF text extraction
- Border-first notice detection
- Unbordered scanned notice OCR fallback
- Multilingual OCR
- Property notice classification
- Normalized bounding-box coordinates
- Structured field extraction
- Secondary OCR comparison
- Extraction conflict detection
- PostgreSQL persistence
- Duplicate notice prevention
- Structured extraction evidence preservation

### 3. Main entry point

documents/services/pipeline.py

Function:

process_pdf()

Example:

    from documents.services.pipeline import process_pdf

    result = process_pdf(
        "newspaper.pdf",
        multilingual=True,
        validate_secondary=True,
        force_region_ocr=True,
    )

The legacy processing mode remains available through
multilingual=False.

### 4. Core dependencies

Python dependencies are listed in requirements.txt.

Ubuntu / WSL OCR dependencies:

    sudo apt update
    sudo apt install -y tesseract-ocr \
        tesseract-ocr-eng tesseract-ocr-kan

Verify OCR languages:

    tesseract --list-langs

Install Python dependencies:

    python -m pip install -r requirements.txt

### 5. Database integration

Main persistence function:

documents.services.database_saver.save_document_pages

Example:

    from documents.services.database_saver import (
        save_document_pages,
    )

    summary = save_document_pages(document, result)

The document argument must be an existing
SourceDocument model instance.

Stored records include:

- DocumentPage
- Notice
- NoticePage
- NoticeExtractionEvidence

Migration:

    python manage.py migrate

Coordinate migration changes with the backend team
before merging into the main branch.

### 6. Structured extraction

The multilingual processor extracts candidate evidence for:

- Survey and property identifiers
- Plot, site, khata and PID numbers
- Locations and addresses
- Property parties and advocates
- Financial organizations
- Legal representatives and relationships
- Agricultural and standard area measurements
- Directional property dimensions
- Objection deadlines

OCR disagreements are preserved as conflicts.

Extracted candidates are not verified ownership records.

### 7. Safety and review

All retained multilingual notice candidates require
manual review.

ACCEPT means accepted as a notice candidate,
not legally verified.

Multilingual evidence is stored separately from
searchable NoticeEntity records.

Unreviewed candidates are not eligible for alerts.

### 8. Testing

Run commands from the backend directory.

Portable regression tests:

    python test_files/regression_tests/run_regression_tests.py

Full local regression tests:

    python test_files/regression_tests/run_regression_tests.py --full

The full suite requires historical local JSON reports.

These reports are intentionally excluded from Git
because they may contain real personal and property data.

The scanned synthetic PDF fixture is generated locally.

### 9. Recorded validation results

Validation date: 27 November 2026

Pipeline version: multilingual_v2

Newspaper: Kannada Prabha, 26 November 2026

- Total pages: 16
- Completed pages: 16
- Failed pages: 0
- Partial failures: 0
- Retained notice candidates: 33
- ACCEPT candidates: 14
- REVIEW candidates: 19
- Processing time: 354.0364 seconds
- Average processing time: 22.13 seconds per page
- Local regression tests: 660 passed
- Compatibility tests: 5 passed
- Django system issues: 0

Database integration validation:

- Document pages created: 16
- Notices created: 33
- Evidence records created: 33
- Duplicate notices created: 0
- Evidence payload integrity: PASS
- Manual review safety: PASS
- Transaction rollback: PASS

### 10. Known limitations

- Full notice detection recall has not been established.
- OCR output requires manual verification.
- Unbordered fallback activates when no candidates
  are retained by the preceding detection methods.
- Mixed bordered and unbordered notice coverage
  requires additional validation.
- Processing is sequential.
- Production-scale performance is not yet benchmarked.
- Searchable entity approval and alert integration
  require downstream team coordination.
- Full regression suite requires local historical reports.

### 11. Integration boundary

The module delivers classified notice candidates,
normalized bounding boxes and structured evidence.

Source collection, review interfaces, saved searches
and WhatsApp alert delivery are downstream workflows.
