import hashlib
import os
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from documents.models import SourceDocument
from collection.models import CollectionRunDocument

from .pdf_downloader import MAX_DOWNLOAD_BYTES


def register_local_pdf(
    *,
    source,
    collection_run,
    local_pdf_path,
    title,
    publication_date=None,
    source_url="",
):
    """
    Register an already-downloaded PDF in Django media storage.

    Returns:
        (SourceDocument, duplicate)
    """

    if not source.is_active:
        raise ValueError("This newspaper source is inactive.")

    if not title:
        raise ValueError("Document title is required.")

    local_pdf_path = Path(local_pdf_path)

    if not local_pdf_path.is_file():
        raise FileNotFoundError(
            f"PDF file not found: {local_pdf_path}"
        )

    file_size = local_pdf_path.stat().st_size

    if file_size > MAX_DOWNLOAD_BYTES:
        raise ValueError("PDF exceeds the 100 MB limit.")

    if file_size == 0:
        raise ValueError("PDF file is empty.")

    file_hash = hashlib.sha256()

    with local_pdf_path.open("rb") as pdf_file:
        signature = pdf_file.read(5)

        if signature != b"%PDF-":
            raise ValueError("File is not a valid PDF.")

        pdf_file.seek(0)

        for chunk in iter(
            lambda: pdf_file.read(8192),
            b"",
        ):
            file_hash.update(chunk)

    file_hash_value = file_hash.hexdigest()

    storage_date = publication_date or timezone.localdate()

    relative_directory = (
        Path("newspapers")
        / str(storage_date.year)
        / f"{storage_date.month:02d}"
    )

    storage_directory = Path(settings.MEDIA_ROOT) / relative_directory
    storage_directory.mkdir(parents=True, exist_ok=True)

    relative_file_path = relative_directory / f"{file_hash_value}.pdf"
    final_path = Path(settings.MEDIA_ROOT) / relative_file_path

    with transaction.atomic():

        existing_document = SourceDocument.objects.filter(
            file_hash=file_hash_value
        ).first()

        if existing_document:
            CollectionRunDocument.objects.get_or_create(
                collection_run=collection_run,
                document=existing_document,
            )

            return existing_document, True

        file_created = False

        try:
            if not final_path.exists():
                os.replace(local_pdf_path, final_path)
                file_created = True

            document = SourceDocument.objects.create(
                source=source,
                title=title,
                source_url=source_url,
                publication_date=publication_date,
                file_path=relative_file_path.as_posix(),
                file_hash=file_hash_value,
                document_type="PDF",
                status=SourceDocument.Status.DOWNLOADED,
                downloaded_at=timezone.now(),
            )

            CollectionRunDocument.objects.create(
                collection_run=collection_run,
                document=document,
            )

            return document, False

        except Exception:
            if file_created:
                final_path.unlink(missing_ok=True)

            raise
