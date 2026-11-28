import shutil
import tempfile

from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings

from sources.models import Source
from collection.models import CollectionRun

from collection.tasks import (
    execute_collection_run_task,
    fetch_and_register_indupaper_daily,
)

from collection.services.local_pdf_registrar import (
    register_local_pdf,
)

from documents.models import SourceDocument


class CollectionProcessingDispatchTests(TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.root = Path(self.temp_dir.name)

        settings_override = override_settings(
            MEDIA_ROOT=self.root / "media"
        )

        settings_override.enable()
        self.addCleanup(settings_override.disable)

        self.source = Source.objects.create(
            name="Hindustan Times Delhi",
            source_type=Source.SourceType.NEWSPAPER,
            region="Delhi",
            language="English",
            is_active=True,
        )

        self.fixture = Path(
            "test_files/sample_multiple_notices.pdf"
        ).resolve()

        self.assertTrue(self.fixture.is_file())

    def make_pdf(self):

        path = self.root / "sample.pdf"

        shutil.copy2(self.fixture, path)

        return path

    @patch(
        "documents.services.processing_dispatcher."
        "process_source_document_task.delay"
    )
    @patch(
        "collection.tasks.execute_collection_run"
    )
    def test_manual_collection_dispatch(
        self, mock_collection, mock_delay
    ):

        run = CollectionRun.objects.create()

        document, duplicate = register_local_pdf(
            source=self.source,
            collection_run=run,
            local_pdf_path=self.make_pdf(),
            title="Manual Collection Test",
        )

        self.assertFalse(duplicate)

        run.status = CollectionRun.Status.COMPLETED
        run.save()

        mock_collection.return_value = run

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            result = execute_collection_run_task.run(
                run.id, []
            )

        mock_delay.assert_called_once_with(document.id)

        self.assertEqual(
            result["status"], "COMPLETED"
        )

    @patch(
        "documents.services.processing_dispatcher."
        "process_source_document_task.delay"
    )
    @patch(
        "collection.services.indupaper_fetcher.run"
    )
    def test_scheduled_collection_dispatch(
        self, mock_fetch, mock_delay
    ):

        mock_fetch.return_value = self.make_pdf()

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            result = fetch_and_register_indupaper_daily.run()

        document = SourceDocument.objects.get(
            pk=result["document_id"]
        )

        self.assertEqual(
            result["status"], "COMPLETED"
        )

        self.assertEqual(
            document.status, "DOWNLOADED"
        )

        mock_delay.assert_called_once_with(document.id)

    @patch(
        "documents.services.processing_dispatcher."
        "process_source_document_task.delay"
    )
    @patch(
        "collection.services.indupaper_fetcher.run"
    )
    def test_completed_duplicate_not_dispatched(
        self, mock_fetch, mock_delay
    ):

        run = CollectionRun.objects.create()

        document, duplicate = register_local_pdf(
            source=self.source,
            collection_run=run,
            local_pdf_path=self.make_pdf(),
            title="Existing Completed PDF",
        )

        document.status = SourceDocument.Status.COMPLETED
        document.save()

        mock_fetch.return_value = self.make_pdf()

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            result = fetch_and_register_indupaper_daily.run()

        self.assertTrue(result["duplicate"])

        self.assertEqual(
            result["document_id"], document.id
        )

        mock_delay.assert_not_called()
