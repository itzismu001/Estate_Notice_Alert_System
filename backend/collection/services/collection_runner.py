from django.db import transaction
from django.utils import timezone

from collection.models import CollectionRun
from collection.services.pdf_downloader import download_and_register_pdf


def execute_collection_run(collection_run, pdf_list):
    """
    Process a list of newspaper PDFs for one collection run.

    Each PDF entry must contain:
        source, pdf_url, title
        publication_date (optional)
    """

    collection_run.status = CollectionRun.Status.RUNNING
    collection_run.error_message = ""
    collection_run.save(
        update_fields=["status", "error_message"]
    )

    successful = 0
    failed = 0
    errors = []

    for pdf in pdf_list:
        try:
            download_and_register_pdf(
                source=pdf["source"],
                collection_run=collection_run,
                pdf_url=pdf["pdf_url"],
                title=pdf["title"],
                publication_date=pdf.get("publication_date"),
            )

            successful += 1

        except Exception as error:
            failed += 1
            errors.append(
                f'{pdf.get("title", "Unknown PDF")}: {error}'
            )

    # Determine final collection status
    if failed == 0:
        final_status = CollectionRun.Status.COMPLETED

    elif successful == 0:
        final_status = CollectionRun.Status.FAILED

    else:
        final_status = CollectionRun.Status.PARTIAL

    # Save final collection statistics
    with transaction.atomic():
        collection_run.status = final_status
        collection_run.total_documents = len(pdf_list)
        collection_run.successful_documents = successful
        collection_run.failed_documents = failed
        collection_run.finished_at = timezone.now()
        collection_run.error_message = "\n".join(errors)

        collection_run.save()

    return collection_run
