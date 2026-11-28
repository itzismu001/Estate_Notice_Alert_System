from django.db import transaction
from django.utils import timezone

from documents.models import ProcessingJob, SourceDocument


class ProcessingRecoveryError(Exception):
    """Raised when a document cannot be safely recovered."""


@transaction.atomic
def recover_interrupted_processing(
    document_id,
    *,
    dry_run=True,
    confirm_worker_stopped=False,
):
    """
    Recover an explicitly selected interrupted processing job.

    This service does not submit a new Celery task.
    """

    if not dry_run and not confirm_worker_stopped:
        raise ProcessingRecoveryError(
            "Confirm that the original worker has stopped "
            "before recovering the document."
        )

    try:
        document = (
            SourceDocument.objects
            .select_for_update()
            .get(pk=document_id)
        )
    except SourceDocument.DoesNotExist as error:
        raise ProcessingRecoveryError(
            f"Document {document_id} does not exist."
        ) from error

    if document.status != SourceDocument.Status.PROCESSING:
        raise ProcessingRecoveryError(
            f"Document {document_id} is {document.status}, "
            "not PROCESSING."
        )

    running_jobs = list(
        ProcessingJob.objects
        .select_for_update()
        .filter(
            document=document,
            status=ProcessingJob.Status.RUNNING,
        )
        .order_by("id")
    )

    if not running_jobs:
        raise ProcessingRecoveryError(
            "No running processing job was found."
        )

    if len(running_jobs) != 1:
        raise ProcessingRecoveryError(
            "Multiple running jobs found. "
            "Manual investigation is required."
        )

    job = running_jobs[0]

    if job.job_type != ProcessingJob.JobType.NOTICE_DETECTION:
        raise ProcessingRecoveryError(
            "Unsupported processing job type."
        )

    retry_allowed = job.retry_count < job.max_retries

    target_status = (
        SourceDocument.Status.DOWNLOADED
        if retry_allowed
        else SourceDocument.Status.FAILED
    )

    result = {
        "document_id": document.id,
        "document_title": document.title,
        "job_id": job.id,
        "celery_task_id": job.celery_task_id,
        "previous_document_status": document.status,
        "new_document_status": target_status,
        "previous_job_status": job.status,
        "new_job_status": ProcessingJob.Status.FAILED,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "retry_allowed": retry_allowed,
        "dry_run": dry_run,
        "recovered": False,
        "task_submitted": False,
    }

    if dry_run:
        return result

    job.status = ProcessingJob.Status.FAILED
    job.completed_at = timezone.now()

    job.error_message = (
        "Processing interrupted. Original worker confirmed "
        "stopped by administrator. Recovered manually."
    )

    if not retry_allowed:
        job.error_message += " Maximum retry limit reached."

    job.save(
        update_fields=[
            "status",
            "completed_at",
            "error_message",
            "updated_at",
        ]
    )

    document.status = target_status

    document.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    result["recovered"] = True

    return result
