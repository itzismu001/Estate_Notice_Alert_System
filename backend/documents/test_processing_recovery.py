from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from sources.models import Source
from documents.models import SourceDocument, ProcessingJob

from documents.services.processing_recovery import (
    ProcessingRecoveryError,
    recover_interrupted_processing,
)


class ProcessingRecoveryTests(TestCase):

    def setUp(self):
        self.source = Source.objects.create(
            name="Recovery Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
            region="Karnataka",
            language="English",
            is_active=True,
        )

        self.document = SourceDocument.objects.create(
            source=self.source,
            title="Recovery Test Document",
            status=SourceDocument.Status.PROCESSING,
            file_path="newspapers/test.pdf",
        )

        self.job = ProcessingJob.objects.create(
            document=self.document,
            job_type=ProcessingJob.JobType.NOTICE_DETECTION,
            status=ProcessingJob.Status.RUNNING,
            celery_task_id="recovery-test-task",
            retry_count=0,
            max_retries=3,
            started_at=timezone.now(),
        )

    def refresh_records(self):
        self.document.refresh_from_db()
        self.job.refresh_from_db()

    def test_dry_run_does_not_modify_database(self):
        result = recover_interrupted_processing(
            self.document.id,
            dry_run=True,
        )

        self.refresh_records()

        self.assertTrue(result["dry_run"])
        self.assertFalse(result["recovered"])
        self.assertFalse(result["task_submitted"])

        self.assertEqual(
            self.document.status,
            SourceDocument.Status.PROCESSING,
        )

        self.assertEqual(
            self.job.status,
            ProcessingJob.Status.RUNNING,
        )

        self.assertIsNone(self.job.completed_at)

    def test_actual_recovery_resets_document(self):
        result = recover_interrupted_processing(
            self.document.id,
            dry_run=False,
            confirm_worker_stopped=True,
        )

        self.refresh_records()

        self.assertTrue(result["recovered"])
        self.assertFalse(result["task_submitted"])

        self.assertEqual(
            self.document.status,
            SourceDocument.Status.DOWNLOADED,
        )

        self.assertEqual(
            self.job.status,
            ProcessingJob.Status.FAILED,
        )

        self.assertIsNotNone(self.job.completed_at)

        self.assertIn(
            "Processing interrupted",
            self.job.error_message,
        )

    def test_recovery_preserves_job_history(self):
        original_job_id = self.job.id
        original_task_id = self.job.celery_task_id
        original_started_at = self.job.started_at
        original_file_path = self.document.file_path

        recover_interrupted_processing(
            self.document.id,
            dry_run=False,
            confirm_worker_stopped=True,
        )

        self.refresh_records()

        self.assertEqual(self.job.id, original_job_id)

        self.assertEqual(
            self.job.celery_task_id,
            original_task_id,
        )

        self.assertEqual(
            self.job.started_at,
            original_started_at,
        )

        self.assertEqual(
            self.document.file_path,
            original_file_path,
        )

        self.assertEqual(
            ProcessingJob.objects.filter(
                document=self.document
            ).count(),
            1,
        )

    def test_recovery_requires_confirmation(self):
        with self.assertRaises(ProcessingRecoveryError):
            recover_interrupted_processing(
                self.document.id,
                dry_run=False,
                confirm_worker_stopped=False,
            )

        self.refresh_records()

        self.assertEqual(
            self.document.status,
            SourceDocument.Status.PROCESSING,
        )

        self.assertEqual(
            self.job.status,
            ProcessingJob.Status.RUNNING,
        )

    def test_completed_document_cannot_be_recovered(self):
        self.document.status = (
            SourceDocument.Status.COMPLETED
        )
        self.document.save()

        with self.assertRaises(ProcessingRecoveryError):
            recover_interrupted_processing(
                self.document.id,
                dry_run=True,
            )

    def test_downloaded_document_cannot_be_recovered(self):
        self.document.status = (
            SourceDocument.Status.DOWNLOADED
        )
        self.document.save()

        with self.assertRaises(ProcessingRecoveryError):
            recover_interrupted_processing(
                self.document.id,
                dry_run=True,
            )

    def test_missing_document_is_rejected(self):
        with self.assertRaises(ProcessingRecoveryError):
            recover_interrupted_processing(
                999999,
                dry_run=True,
            )

    def test_document_without_running_job_is_rejected(self):
        self.job.status = ProcessingJob.Status.FAILED
        self.job.save()

        with self.assertRaises(ProcessingRecoveryError):
            recover_interrupted_processing(
                self.document.id,
                dry_run=True,
            )

    def test_multiple_running_jobs_are_rejected(self):
        ProcessingJob.objects.create(
            document=self.document,
            job_type=ProcessingJob.JobType.NOTICE_DETECTION,
            status=ProcessingJob.Status.RUNNING,
            celery_task_id="second-running-task",
            started_at=timezone.now(),
        )

        with self.assertRaises(ProcessingRecoveryError):
            recover_interrupted_processing(
                self.document.id,
                dry_run=True,
            )

    def test_retry_limit_marks_document_failed(self):
        self.job.retry_count = self.job.max_retries
        self.job.save()

        result = recover_interrupted_processing(
            self.document.id,
            dry_run=False,
            confirm_worker_stopped=True,
        )

        self.refresh_records()

        self.assertFalse(result["retry_allowed"])

        self.assertEqual(
            self.document.status,
            SourceDocument.Status.FAILED,
        )

        self.assertEqual(
            self.job.status,
            ProcessingJob.Status.FAILED,
        )

        self.assertIn(
            "Maximum retry limit reached",
            self.job.error_message,
        )

    def test_repeated_recovery_is_rejected(self):
        recover_interrupted_processing(
            self.document.id,
            dry_run=False,
            confirm_worker_stopped=True,
        )

        with self.assertRaises(ProcessingRecoveryError):
            recover_interrupted_processing(
                self.document.id,
                dry_run=False,
                confirm_worker_stopped=True,
            )

    def test_management_command_dry_run(self):
        output = StringIO()

        call_command(
            "recover_processing",
            "--document-id",
            str(self.document.id),
            "--dry-run",
            stdout=output,
        )

        self.assertIn(
            "DRY RUN",
            output.getvalue(),
        )

        self.refresh_records()

        self.assertEqual(
            self.document.status,
            SourceDocument.Status.PROCESSING,
        )

        self.assertEqual(
            self.job.status,
            ProcessingJob.Status.RUNNING,
        )
