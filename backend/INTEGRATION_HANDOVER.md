# Estate Notice Alert System

## Backend Integration Handover

### Branch

integration/estate-notice-pipeline

### Integrated Modules

- Automated newspaper collection
- PDF downloading and validation
- SHA-256 duplicate detection
- Cross-filesystem PDF registration
- Redis and Celery background processing
- Automatic document processing dispatch
- Multilingual V2 notice detection
- English and Kannada field extraction
- PostgreSQL persistence
- Extraction evidence storage
- Processing job tracking
- Manual review protection

### Processing Workflow

Newspaper collection
-> PDF registration
-> Processing dispatcher
-> Redis
-> Celery worker
-> Multilingual processing
-> Notice detection
-> Field extraction
-> Database persistence
-> Manual review

### Verified Test Results

- Full regression tests: 660/660
- Portable regression tests: 286/286
- Django tests: 56/56
- Processing integration tests: 7/7
- Collection dispatch tests: 3/3
- Combined tests: 716/716

Portable tests are included in the full regression suite.
Integration and dispatch tests are included in Django tests.

### Background Processing Verification

- Document status: COMPLETED
- Pages processed: 1
- Notices detected: 2
- Evidence records: 2
- Failed pages: 0
- Automatic alerts: Disabled

### Registered Celery Tasks

- collection.execute_collection_run
- collection.fetch_and_register_indupaper_daily
- documents.process_source_document

### Development Services

sudo service postgresql start
sudo service redis-server start

### Start Worker

python -m celery -A config worker --loglevel=info --concurrency=1

### Run Tests

python manage.py check
python manage.py test
python test_files/regression_tests/run_regression_tests.py

Full regression tests require historical local fixtures.

### Remaining Work

- Jahnvi's OCR and image cropping integration
- OCR confidence and preprocessing improvements
- Structured NoticeEntity mapping
- Live scheduled newspaper collection verification
- Automatic queue failure recovery
- Worker crash recovery
- Concurrent registration hardening
- Frontend integration
- Saved search and notification verification
- Production deployment

### Safety

All extracted notice candidates require manual review.
Extraction evidence is not legal verification.
Collection trigger tests use mocked newspaper downloads.
Production scheduling remains unverified.
Synthetic integration records have been cleaned up.
