from documents.models import ProcessingJob


def get_processing_retry_state(document):
    """
    Determine the next processing attempt using persisted
    document-level notice detection job history.

    The caller must lock the document when using this
    result to create a new processing attempt.
    """

    previous_jobs = ProcessingJob.objects.filter(
        document=document,
        job_type=ProcessingJob.JobType.NOTICE_DETECTION,
        page__isnull=True,
    )

    previous_job = previous_jobs.order_by("-id").first()

    if previous_job is None:
        return {
            "allowed": True,
            "retry_count": 0,
            "max_retries": 3,
            "previous_job_id": None,
            "reason": "initial_attempt",
        }

    if previous_jobs.filter(
        status__in=[
            ProcessingJob.Status.RUNNING,
            ProcessingJob.Status.PENDING,
        ]
    ).exists():
        return {
            "allowed": False,
            "retry_count": previous_job.retry_count,
            "max_retries": previous_job.max_retries,
            "previous_job_id": previous_job.id,
            "reason": "active_processing_job",
        }

    if previous_job.status != ProcessingJob.Status.FAILED:
        return {
            "allowed": False,
            "retry_count": previous_job.retry_count,
            "max_retries": previous_job.max_retries,
            "previous_job_id": previous_job.id,
            "reason": "previous_job_not_failed",
        }

    failed_jobs = previous_jobs.filter(
        status=ProcessingJob.Status.FAILED
    )

    highest_retry = failed_jobs.order_by(
        "-retry_count"
    ).values_list(
        "retry_count",
        flat=True,
    ).first()

    next_retry_count = max(
        highest_retry + 1,
        failed_jobs.count(),
    )

    max_retries = previous_job.max_retries

    return {
        "allowed": next_retry_count <= max_retries,
        "retry_count": next_retry_count,
        "max_retries": max_retries,
        "previous_job_id": previous_job.id,
        "reason": (
            "retry_available"
            if next_retry_count <= max_retries
            else "maximum_retries_reached"
        ),
    }
