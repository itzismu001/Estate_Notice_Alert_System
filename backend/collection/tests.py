from collection.services.collection_runner import execute_collection_run
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from sources.models import Source
from collection.models import CollectionRun, CollectionRunDocument
from documents.models import SourceDocument
from collection.services.pdf_downloader import download_and_register_pdf


class PDFDownloaderTests(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.settings_override = override_settings(
            MEDIA_ROOT=self.temp_dir.name
        )
        self.settings_override.enable()

        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.temp_dir.cleanup)

        self.source = Source.objects.create(
            name="Test PDF Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
            region="Karnataka",
            language="English",
            is_active=True,
        )

        self.collection_run = CollectionRun.objects.create()

        self.pdf_url = "https://example.com/newspaper.pdf"

        self.response = MagicMock()
        self.response.__enter__.return_value = self.response
        self.response.headers = {"Content-Length": "20"}
        self.response.iter_content.return_value = [
            b"%PDF-",
            b"sample pdf content",
        ]

    @patch("collection.services.pdf_downloader.requests.get")
    def test_successful_pdf_download(self, mock_get):

        mock_get.return_value = self.response

        document, duplicate = download_and_register_pdf(
            source=self.source,
            collection_run=self.collection_run,
            pdf_url=self.pdf_url,
            title="Test Newspaper PDF",
        )

        self.assertFalse(duplicate)

        self.assertEqual(
            document.status,
            SourceDocument.Status.DOWNLOADED,
        )

        self.assertTrue(document.file_hash)

        self.assertTrue(
            (Path(self.settings_override.options["MEDIA_ROOT"])
             / document.file_path).exists()
        )

        self.assertTrue(
            CollectionRunDocument.objects.filter(
                collection_run=self.collection_run,
                document=document,
            ).exists()
        )

    @patch("collection.services.pdf_downloader.requests.get")
    def test_duplicate_pdf_is_not_saved_twice(self, mock_get):

        mock_get.return_value = self.response

        first_document, first_duplicate = download_and_register_pdf(
            source=self.source,
            collection_run=self.collection_run,
            pdf_url=self.pdf_url,
            title="Test Newspaper PDF",
        )

        second_document, second_duplicate = download_and_register_pdf(
            source=self.source,
            collection_run=self.collection_run,
            pdf_url=self.pdf_url,
            title="Test Newspaper PDF",
        )

        self.assertFalse(first_duplicate)
        self.assertTrue(second_duplicate)

        self.assertEqual(first_document.id, second_document.id)

        self.assertEqual(SourceDocument.objects.count(), 1)

    @patch("collection.services.pdf_downloader.requests.get")
    def test_invalid_file_is_rejected(self, mock_get):

        self.response.iter_content.return_value = [
            b"This is not a PDF"
        ]

        mock_get.return_value = self.response

        with self.assertRaises(ValueError):

            download_and_register_pdf(
                source=self.source,
                collection_run=self.collection_run,
                pdf_url=self.pdf_url,
                title="Invalid PDF",
            )

        self.assertEqual(SourceDocument.objects.count(), 0)

    @patch("collection.services.pdf_downloader.requests.get")
    def test_inactive_source_is_rejected(self, mock_get):

        self.source.is_active = False
        self.source.save()

        with self.assertRaises(ValueError):

            download_and_register_pdf(
                source=self.source,
                collection_run=self.collection_run,
                pdf_url=self.pdf_url,
                title="Inactive Source PDF",
            )

        mock_get.assert_not_called()
from django.test import TestCase
class CollectionRunnerTests(TestCase):

    def setUp(self):
        self.source = Source.objects.create(
            name="Runner Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
            region="Karnataka",
            language="English",
            is_active=True,
        )

        self.collection_run = CollectionRun.objects.create()

        self.pdf_list = [
            {
                "source": self.source,
                "pdf_url": "https://example.com/paper1.pdf",
                "title": "Newspaper 1",
            },
            {
                "source": self.source,
                "pdf_url": "https://example.com/paper2.pdf",
                "title": "Newspaper 2",
            },
        ]

    @patch("collection.services.collection_runner.download_and_register_pdf")
    def test_all_downloads_successful(self, mock_download):

        mock_download.return_value = (MagicMock(), False)

        result = execute_collection_run(
            self.collection_run,
            self.pdf_list,
        )

        self.assertEqual(result.status, CollectionRun.Status.COMPLETED)
        self.assertEqual(result.total_documents, 2)
        self.assertEqual(result.successful_documents, 2)
        self.assertEqual(result.failed_documents, 0)
        self.assertIsNotNone(result.finished_at)

    @patch("collection.services.collection_runner.download_and_register_pdf")
    def test_partial_download_failure(self, mock_download):

        mock_download.side_effect = [
            (MagicMock(), False),
            ValueError("Download failed"),
        ]

        result = execute_collection_run(
            self.collection_run,
            self.pdf_list,
        )

        self.assertEqual(result.status, CollectionRun.Status.PARTIAL)
        self.assertEqual(result.total_documents, 2)
        self.assertEqual(result.successful_documents, 1)
        self.assertEqual(result.failed_documents, 1)
        self.assertIn("Download failed", result.error_message)

    @patch("collection.services.collection_runner.download_and_register_pdf")
    def test_all_downloads_failed(self, mock_download):

        mock_download.side_effect = ValueError("Download failed")

        result = execute_collection_run(
            self.collection_run,
            self.pdf_list,
        )

        self.assertEqual(result.status, CollectionRun.Status.FAILED)
        self.assertEqual(result.total_documents, 2)
        self.assertEqual(result.successful_documents, 0)
        self.assertEqual(result.failed_documents, 2)
        self.assertIsNotNone(result.finished_at)
# Create your tests here.
class CollectionRunAPITests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username="collection_admin",
            email="admin@example.com",
            password="testpassword123",
        )

        self.normal_user = User.objects.create_user(
            username="normal_user",
            password="testpassword123",
        )

        self.source = Source.objects.create(
            name="API Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
            region="Karnataka",
            language="English",
            is_active=True,
        )

        self.url = "/api/v1/collection-runs/"

        self.payload = {
            "pdf_list": [
                {
                    "source_id": self.source.id,
                    "pdf_url": "https://example.com/newspaper.pdf",
                    "title": "Test Newspaper",
                    "publication_date": "2026-11-27",
                }
            ]
        }

    @patch("collection.views.execute_collection_run_task.delay")
    def test_admin_can_create_collection_run(self, mock_delay):

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 202)

        self.assertEqual(
            response.data["status"],
            CollectionRun.Status.PENDING,
        )

        self.assertEqual(CollectionRun.objects.count(), 1)

        mock_delay.assert_called_once_with(
            response.data["id"],
            [
                {
                    "source_id": self.source.id,
                    "pdf_url": "https://example.com/newspaper.pdf",
                    "title": "Test Newspaper",
                    "publication_date": "2026-11-27",
                }
            ],
        )

    def test_inactive_or_invalid_source_is_rejected(self):

        self.client.force_authenticate(user=self.admin)

        invalid_payload = {
            "pdf_list": [
                {
                    "source_id": 99999,
                    "pdf_url": "https://example.com/newspaper.pdf",
                    "title": "Invalid Source Newspaper",
                }
            ]
        }

        response = self.client.post(
            self.url,
            invalid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(CollectionRun.objects.count(), 0)

    def test_normal_user_cannot_create_collection_run(self):

        self.client.force_authenticate(user=self.normal_user)

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(CollectionRun.objects.count(), 0)

    @patch(
        "collection.views.execute_collection_run_task.delay",
        side_effect=Exception("Redis unavailable"),
    )
    def test_celery_queue_failure_marks_run_failed(self, mock_delay):

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 503)

        collection_run = CollectionRun.objects.get()

        self.assertEqual(
            collection_run.status,
            CollectionRun.Status.FAILED,
        )

        self.assertIn(
            "Redis unavailable",
            collection_run.error_message,
        )
