from datetime import date
from celery import shared_task

from documents.services.processing_dispatcher import dispatch_document_processing

from collection.models import CollectionRun
from collection.services.collection_runner import execute_collection_run
from sources.models import Source
from django.utils import timezone


@shared_task(bind=True, name="collection.execute_collection_run")
def execute_collection_run_task(self, collection_run_id, pdf_list):
    """
    Execute a newspaper collection run in the background.

    Celery receives JSON-compatible data.
    Database objects are retrieved inside the task.
    """

    collection_run = CollectionRun.objects.get(
        id=collection_run_id
    )

    prepared_pdf_list = []

    for pdf in pdf_list:
        source = Source.objects.get(
            id=pdf["source_id"]
        )

        prepared_pdf_list.append({
            "source": source,
            "pdf_url": pdf["pdf_url"],
            "title": pdf["title"],
            "publication_date": (
    date.fromisoformat(pdf["publication_date"])
    if pdf.get("publication_date")
    else None
),
        })

    result = execute_collection_run(
        collection_run,
        prepared_pdf_list
    )

    for record in result.run_documents.all():
        dispatch_document_processing(record.document_id)

    return {
        "collection_run_id": result.id,
        "status": result.status,
        "total_documents": result.total_documents,
        "successful_documents": result.successful_documents,
        "failed_documents": result.failed_documents,
    }

@shared_task(name="collection.fetch_and_register_indupaper_daily")
def fetch_and_register_indupaper_daily():

    from collection.services.indupaper_fetcher import run
    from collection.services.indupaper_fetcher import URL
    from collection.services.local_pdf_registrar import register_local_pdf

    today = timezone.localdate()

    collection_run = CollectionRun.objects.create(
        status=CollectionRun.Status.RUNNING
    )

    local_pdf_path = None

    try:
        # Find the active Hindustan Times source
        source = Source.objects.get(
            name="Hindustan Times Delhi",
            is_active=True,
        )

        # Fetch today's newspaper PDF
        local_pdf_path = run(
            newspaper="Hindustan Times Delhi",
            edition_date=today,
            today=today,
        )

        # Register the downloaded PDF in Django
        document, duplicate = register_local_pdf(
            source=source,
            collection_run=collection_run,
            local_pdf_path=local_pdf_path,
            title=f"Hindustan Times Delhi - {today}",
            publication_date=today,
            source_url=URL,
        )

        dispatch_document_processing(document.id)

        # Mark collection as successful
        collection_run.status = CollectionRun.Status.COMPLETED
        collection_run.total_documents = 1
        collection_run.successful_documents = 1
        collection_run.failed_documents = 0
        collection_run.finished_at = timezone.now()
        collection_run.error_message = ""

        collection_run.save()

        return {
            "collection_run_id": collection_run.id,
            "status": collection_run.status,
            "document_id": document.id,
            "duplicate": duplicate,
            "total_documents": 1,
            "successful_documents": 1,
            "failed_documents": 0,
        }

    except Exception as error:

        collection_run.status = CollectionRun.Status.FAILED
        collection_run.total_documents = 1
        collection_run.successful_documents = 0
        collection_run.failed_documents = 1
        collection_run.finished_at = timezone.now()
        collection_run.error_message = str(error)

        collection_run.save()

        raise

    finally:
        # Remove the staging PDF if it still exists.
        # The registrar moves it when a new document is registered.
        if local_pdf_path is not None:
            local_pdf_path.unlink(missing_ok=True)
