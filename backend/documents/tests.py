
from django.test import TestCase
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from sources.models import Source
from documents.models import (
    SourceDocument,
    DocumentPage,
    ProcessingJob,
)


class SourceDocumentTests(TestCase):

    def setUp(self):
        self.source = Source.objects.create(
            name="Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
        )

    def test_document_default_status(self):
        document = SourceDocument.objects.create(
            source=self.source,
            title="Test Newspaper PDF",
        )

        self.assertEqual(
            document.status,
            SourceDocument.Status.PENDING,
        )

    def test_document_default_type_is_pdf(self):
        document = SourceDocument.objects.create(
            source=self.source,
            title="Test PDF",
        )

        self.assertEqual(document.document_type, "PDF")

    def test_source_deletion_is_protected(self):
        SourceDocument.objects.create(
            source=self.source,
            title="Test PDF",
        )

        with self.assertRaises(ProtectedError):
            self.source.delete()


class DocumentPageTests(TestCase):

    def setUp(self):
        self.source = Source.objects.create(
            name="Page Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
        )

        self.document = SourceDocument.objects.create(
            source=self.source,
            title="Page Test PDF",
        )

    def test_page_default_values(self):
        page = DocumentPage.objects.create(
            document=self.document,
            page_number=1,
        )

        self.assertEqual(
            page.page_type,
            DocumentPage.PageType.UNKNOWN,
        )

        self.assertEqual(
            page.processing_status,
            DocumentPage.ProcessingStatus.PENDING,
        )

    def test_duplicate_page_number_is_prevented(self):
        DocumentPage.objects.create(
            document=self.document,
            page_number=1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DocumentPage.objects.create(
                    document=self.document,
                    page_number=1,
                )


class ProcessingJobTests(TestCase):

    def setUp(self):
        self.source = Source.objects.create(
            name="Processing Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
        )

        self.document = SourceDocument.objects.create(
            source=self.source,
            title="Processing Test PDF",
        )

    def test_processing_job_default_values(self):
        job = ProcessingJob.objects.create(
            document=self.document,
            job_type=ProcessingJob.JobType.OCR,
        )

        self.assertEqual(
            job.status,
            ProcessingJob.Status.PENDING,
        )

        self.assertEqual(job.retry_count, 0)
        self.assertEqual(job.max_retries, 3)

    def test_processing_job_can_be_linked_to_page(self):
        page = DocumentPage.objects.create(
            document=self.document,
            page_number=1,
        )

        job = ProcessingJob.objects.create(
            document=self.document,
            page=page,
            job_type=ProcessingJob.JobType.TEXT_EXTRACTION,
        )

        self.assertEqual(job.page, page)
        self.assertEqual(job.document, self.document)
