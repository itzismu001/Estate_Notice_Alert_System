import logging

from django.db import transaction

from documents.models import SourceDocument
from documents.tasks import process_source_document_task

from documents.services.processing_retry import (
    get_processing_retry_state,
)


logger = logging.getLogger(__name__)


def dispatch_document_processing(document_id):

    document = SourceDocument.objects.get(
        pk=document_id
    )

    if document.status != SourceDocument.Status.DOWNLOADED:
        return False

    retry_state = get_processing_retry_state(document)

    if not retry_state["allowed"]:
        logger.warning(
            "Processing dispatch blocked for document %s: %s",
            document_id,
            retry_state["reason"],
        )
        return False

    def submit_task():

        try:
            process_source_document_task.delay(
                document_id
            )

            logger.info(
                "Processing task submitted for document %s",
                document_id,
            )

        except Exception:
            logger.exception(
                "Could not submit processing task for document %s",
                document_id,
            )

    transaction.on_commit(submit_task)

    return True
