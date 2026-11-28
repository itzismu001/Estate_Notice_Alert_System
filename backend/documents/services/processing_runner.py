from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from documents.models import SourceDocument, ProcessingJob
from documents.services.pipeline import process_pdf
from documents.services.database_saver import save_document_pages


def resolve_document_path(document):
    media_root = Path(settings.MEDIA_ROOT).resolve()

    if not document.file_path:
        raise ValueError("Document file path is missing")

    pdf_path = (media_root / document.file_path).resolve()

    if not pdf_path.is_relative_to(media_root):
        raise ValueError("Document path is outside media storage")

    if not pdf_path.is_file():
        raise FileNotFoundError("Registered PDF file not found")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Unsupported document file type")

    return pdf_path


def execute_document_processing(document_id, task_id=""):

    with transaction.atomic():

        document = (
            SourceDocument.objects
            .select_for_update()
            .get(pk=document_id)
        )

        if document.status in (
            SourceDocument.Status.PROCESSING,
            SourceDocument.Status.COMPLETED,
        ):
            return {
                "document_id": document.id,
                "status": document.status,
                "skipped": True,
            }

        if document.status not in (
            SourceDocument.Status.DOWNLOADED,
            SourceDocument.Status.FAILED,
        ):
            raise ValueError("Document is not ready for processing")

        job = ProcessingJob.objects.create(
            document=document,
            job_type=ProcessingJob.JobType.NOTICE_DETECTION,
            status=ProcessingJob.Status.RUNNING,
            celery_task_id=task_id or "",
            started_at=timezone.now(),
        )

        document.status = SourceDocument.Status.PROCESSING
        document.save(update_fields=["status", "updated_at"])

    try:
        pdf_path = resolve_document_path(document)

        result = process_pdf(
            pdf_path,
            multilingual=True,
            validate_secondary=True,
        )

        total_pages = result["total_pages"]
        completed_pages = result["completed_pages"]

        fully_completed = (
            total_pages > 0
            and completed_pages == total_pages
            and len(result["pages"]) == total_pages
        )

        with transaction.atomic():

            summary = save_document_pages(document, result)

            document.status = (
                SourceDocument.Status.COMPLETED
                if fully_completed
                else SourceDocument.Status.FAILED
            )

            document.save(
                update_fields=["status", "updated_at"]
            )

            job.status = (
                ProcessingJob.Status.COMPLETED
                if fully_completed
                else ProcessingJob.Status.FAILED
            )

            job.completed_at = timezone.now()

            job.error_message = (
                ""
                if fully_completed
                else (
                    f"Completed {completed_pages} of "
                    f"{total_pages} pages. "
                    "Incomplete pages require reprocessing."
                )
            )

            job.save()

        return {
            "document_id": document.id,
            "job_id": job.id,
            "status": document.status,
            "pipeline_version": result["pipeline_version"],
            "total_pages": total_pages,
            "completed_pages": completed_pages,
            "partial_failure_pages": result.get(
                "partial_failure_pages", 0
            ),
            "failed_pages": result.get("failed_pages", 0),
            "total_notices": result["total_notices"],
            "database_summary": summary,
            "skipped": False,
            "eligible_for_alert": False,
        }

    except Exception as error:

        with transaction.atomic():

            document.status = SourceDocument.Status.FAILED
            document.save(
                update_fields=["status", "updated_at"]
            )

            job.status = ProcessingJob.Status.FAILED
            job.error_message = str(error)
            job.completed_at = timezone.now()
            job.save()

        raise
