from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from sources.models import Source

from documents.models import (
    SourceDocument,
    ProcessingJob,
    DocumentPage,
)

from documents.services.processing_retry import (
    get_processing_retry_state,
)

from documents.services.processing_runner import (
    execute_document_processing,
)

from documents.services.processing_dispatcher import (
    dispatch_document_processing,
)


class ProcessingRetryTests(TestCase):

    def setUp(self):
        self.source = Source.objects.create(
            name="Retry Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
            region="Karnataka",
            language="English",
            is_active=True,
        )

        self.document = SourceDocument.objects.create(
            source=self.source,
            title="Retry Test Document",
            status=SourceDocument.Status.DOWNLOADED,
            file_path="newspapers/retry-test.pdf",
        )

    def create_job(
        self,
        retry_count=0,
        max_retries=3,
        status=ProcessingJob.Status.FAILED,
        job_type=ProcessingJob.JobType.NOTICE_DETECTION,
        page=None,
    ):
        return ProcessingJob.objects.create(
            document=self.document,
            page=page,
            job_type=job_type,
            status=status,
            retry_count=retry_count,
            max_retries=max_retries,
            started_at=timezone.now(),
        )

    def test_initial_attempt_starts_at_zero(self):
        state = get_processing_retry_state(
            self.document
        )

        self.assertTrue(state["allowed"])
        self.assertEqual(state["retry_count"], 0)
        self.assertEqual(state["max_retries"], 3)
        self.assertIsNone(state["previous_job_id"])
        self.assertEqual(
            state["reason"],
            "initial_attempt",
        )

    def test_first_retry_increments_to_one(self):
        previous = self.create_job(retry_count=0)

        state = get_processing_retry_state(
            self.document
        )

        self.assertTrue(state["allowed"])
        self.assertEqual(state["retry_count"], 1)
        self.assertEqual(
            state["previous_job_id"],
            previous.id,
        )

    def test_second_retry_increments_to_two(self):
        self.create_job(retry_count=0)
        self.create_job(retry_count=1)

        state = get_processing_retry_state(
            self.document
        )

        self.assertTrue(state["allowed"])
        self.assertEqual(state["retry_count"], 2)

    def test_third_retry_is_allowed(self):
        for count in range(3):
            self.create_job(retry_count=count)

        state = get_processing_retry_state(
            self.document
        )

        self.assertTrue(state["allowed"])
        self.assertEqual(state["retry_count"], 3)

    def test_fourth_retry_is_blocked(self):
        for count in range(4):
            self.create_job(retry_count=count)

        state = get_processing_retry_state(
            self.document
        )

        self.assertFalse(state["allowed"])
        self.assertEqual(state["retry_count"], 4)
        self.assertEqual(
            state["reason"],
            "maximum_retries_reached",
        )

    def test_custom_maximum_retry_limit(self):
        self.create_job(
            retry_count=0,
            max_retries=1,
        )

        state = get_processing_retry_state(
            self.document
        )

        self.assertTrue(state["allowed"])
        self.assertEqual(state["max_retries"], 1)

        self.create_job(
            retry_count=1,
            max_retries=1,
        )

        state = get_processing_retry_state(
            self.document
        )

        self.assertFalse(state["allowed"])

    def test_legacy_zero_count_failures(self):
        for _ in range(3):
            self.create_job(retry_count=0)

        state = get_processing_retry_state(
            self.document
        )

        self.assertTrue(state["allowed"])
        self.assertEqual(state["retry_count"], 3)

        self.create_job(retry_count=0)

        state = get_processing_retry_state(
            self.document
        )

        self.assertFalse(state["allowed"])

    def test_running_job_blocks_new_attempt(self):
        self.create_job(
            status=ProcessingJob.Status.RUNNING
        )

        state = get_processing_retry_state(
            self.document
        )

        self.assertFalse(state["allowed"])
        self.assertEqual(
            state["reason"],
            "active_processing_job",
        )

    def test_pending_job_blocks_new_attempt(self):
        self.create_job(
            status=ProcessingJob.Status.PENDING
        )

        state = get_processing_retry_state(
            self.document
        )

        self.assertFalse(state["allowed"])
        self.assertEqual(
            state["reason"],
            "active_processing_job",
        )

    def test_completed_job_blocks_retry(self):
        self.create_job(
            status=ProcessingJob.Status.COMPLETED
        )

        state = get_processing_retry_state(
            self.document
        )

        self.assertFalse(state["allowed"])
        self.assertEqual(
            state["reason"],
            "previous_job_not_failed",
        )

    def test_page_level_jobs_do_not_affect_retry(self):
        page = DocumentPage.objects.create(
            document=self.document,
            page_number=1,
        )

        self.create_job(
            retry_count=3,
            job_type=ProcessingJob.JobType.OCR,
            page=page,
        )

        self.create_job(
            retry_count=3,
            job_type=ProcessingJob.JobType.NOTICE_DETECTION,
            page=page,
        )

        state = get_processing_retry_state(
            self.document
        )

        self.assertTrue(state["allowed"])
        self.assertEqual(state["retry_count"], 0)

    def test_dispatcher_blocks_exhausted_retries(self):
        self.create_job(
            retry_count=3,
            max_retries=3,
        )

        with patch(
            "documents.services.processing_dispatcher."
            "process_source_document_task.delay"
        ) as mock_delay:

            with self.captureOnCommitCallbacks(
                execute=True
            ):
                result = dispatch_document_processing(
                    self.document.id
                )

            self.assertFalse(result)
            mock_delay.assert_not_called()

    def test_runner_cannot_bypass_retry_limit(self):
        self.create_job(
            retry_count=3,
            max_retries=3,
        )

        self.document.status = (
            SourceDocument.Status.FAILED
        )
        self.document.save()

        with patch(
            "documents.services.processing_runner."
            "process_pdf"
        ) as mock_pipeline:

            result = execute_document_processing(
                document_id=self.document.id,
                task_id="blocked-retry",
            )

            mock_pipeline.assert_not_called()

        self.document.refresh_from_db()

        self.assertTrue(result["skipped"])
        self.assertEqual(
            result["reason"],
            "maximum_retries_reached",
        )
        self.assertEqual(
            self.document.status,
            SourceDocument.Status.FAILED,
        )
        self.assertEqual(
            self.document.processing_jobs.count(),
            1,
        )

    def test_runner_persists_retry_and_preserves_history(self):
        original_job = self.create_job(
            retry_count=0,
            max_retries=3,
        )

        original_job_id = original_job.id

        with patch(
            "documents.services.processing_runner."
            "resolve_document_path",
            side_effect=FileNotFoundError(
                "Simulated processing failure"
            ),
        ):
            with self.assertRaises(FileNotFoundError):
                execute_document_processing(
                    document_id=self.document.id,
                    task_id="first-retry-test",
                )

        self.document.refresh_from_db()
        original_job.refresh_from_db()

        jobs = self.document.processing_jobs.order_by(
            "id"
        )

        self.assertEqual(jobs.count(), 2)

        latest_job = jobs.last()

        self.assertEqual(original_job.id, original_job_id)
        self.assertEqual(original_job.retry_count, 0)
        self.assertEqual(
            original_job.status,
            ProcessingJob.Status.FAILED,
        )

        self.assertEqual(latest_job.retry_count, 1)
        self.assertEqual(latest_job.max_retries, 3)
        self.assertEqual(
            latest_job.celery_task_id,
            "first-retry-test",
        )
        self.assertEqual(
            latest_job.status,
            ProcessingJob.Status.FAILED,
        )
        self.assertEqual(
            self.document.status,
            SourceDocument.Status.FAILED,
        )
        self.assertIsNotNone(latest_job.completed_at)

        state = get_processing_retry_state(
            self.document
        )

        self.assertTrue(state["allowed"])
        self.assertEqual(state["retry_count"], 2)
