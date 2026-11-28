from celery import shared_task

from documents.services.processing_runner import (
    execute_document_processing,
)


@shared_task(
    bind=True,
    name="documents.process_source_document",
)
def process_source_document_task(self, document_id):

    return execute_document_processing(
        document_id=document_id,
        task_id=self.request.id or "",
    )
