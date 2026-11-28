import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from sources.models import Source
from collection.models import CollectionRun
from collection.services.local_pdf_registrar import register_local_pdf

from documents.models import SourceDocument, ProcessingJob
from documents.services.processing_runner import (
    execute_document_processing,
)
from documents.services.processing_dispatcher import (
    dispatch_document_processing,
)

from notices.models import NoticePage, NoticeExtractionEvidence


class ProcessingIntegrationTests(TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)

        self.settings_override = override_settings(
            MEDIA_ROOT=self.root / "media"
        )

        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.source = Source.objects.create(
            name="Integration Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
            region="Karnataka",
            language="English",
            is_active=True,
        )

        self.collection_run = CollectionRun.objects.create()

    def register_fixture(self):

        fixture = Path(
            "test_files/sample_multiple_notices.pdf"
        ).resolve()

        self.assertTrue(fixture.is_file())

        pdf_path = self.root / "sample.pdf"
        shutil.copy2(fixture, pdf_path)

        document, duplicate = register_local_pdf(
            source=self.source,
            collection_run=self.collection_run,
            local_pdf_path=pdf_path,
            title="Integration Test PDF",
        )

        self.assertFalse(duplicate)

        return document

    def test_complete_processing(self):

        document = self.register_fixture()

        result = execute_document_processing(
            document.id,
            task_id="test-task",
        )

        document.refresh_from_db()

        self.assertEqual(document.status, "COMPLETED")
        self.assertEqual(document.pages.count(), 1)
        self.assertEqual(result["total_notices"], 2)
        self.assertFalse(result["eligible_for_alert"])

        self.assertEqual(
            NoticePage.objects.filter(
                document_page__document=document
            ).count(),
            2,
        )

        self.assertEqual(
            NoticeExtractionEvidence.objects.filter(
                notice_page__document_page__document=document
            ).count(),
            2,
        )

        job = ProcessingJob.objects.get(document=document)

        self.assertEqual(job.status, "COMPLETED")
        self.assertEqual(job.celery_task_id, "test-task")

    def test_duplicate_processing_is_skipped(self):

        document = self.register_fixture()

        execute_document_processing(document.id)

        result = execute_document_processing(document.id)

        self.assertTrue(result["skipped"])

        self.assertEqual(
            ProcessingJob.objects.filter(
                document=document
            ).count(),
            1,
        )

    def test_missing_pdf_marks_processing_failed(self):

        document = self.register_fixture()

        pdf_path = (
            self.root / "media" / document.file_path
        )

        pdf_path.unlink()

        with self.assertRaises(FileNotFoundError):
            execute_document_processing(document.id)

        document.refresh_from_db()

        self.assertEqual(document.status, "FAILED")

        job = ProcessingJob.objects.get(document=document)

        self.assertEqual(job.status, "FAILED")
        self.assertTrue(job.error_message)

    def test_running_document_is_skipped(self):

        document = self.register_fixture()

        document.status = SourceDocument.Status.PROCESSING
        document.save()

        result = execute_document_processing(document.id)

        self.assertTrue(result["skipped"])

        self.assertFalse(
            ProcessingJob.objects.filter(
                document=document
            ).exists()
        )

    @patch(
        "documents.services.processing_dispatcher."
        "process_source_document_task.delay"
    )
    def test_dispatch_after_commit(self, mock_delay):

        document = self.register_fixture()

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            result = dispatch_document_processing(
                document.id
            )

        self.assertTrue(result)

        mock_delay.assert_called_once_with(document.id)

    @patch(
        "documents.services.processing_dispatcher."
        "process_source_document_task.delay"
    )
    def test_completed_document_is_not_dispatched(
        self, mock_delay
    ):

        document = self.register_fixture()

        document.status = SourceDocument.Status.COMPLETED
        document.save()

        result = dispatch_document_processing(
            document.id
        )

        self.assertFalse(result)
        mock_delay.assert_not_called()

    @patch(
        "documents.services.processing_dispatcher."
        "process_source_document_task.delay",
        side_effect=ConnectionError("Redis unavailable"),
    )
    def test_queue_failure_preserves_document(
        self, mock_delay
    ):

        document = self.register_fixture()

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            dispatch_document_processing(document.id)

        document.refresh_from_db()

        self.assertEqual(document.status, "DOWNLOADED")

        mock_delay.assert_called_once_with(document.id)
