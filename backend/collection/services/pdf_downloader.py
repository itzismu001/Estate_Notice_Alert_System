
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from documents.models import SourceDocument
from collection.models import CollectionRunDocument


MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024  # 100 MB


def download_and_register_pdf(
    *,
    source,
    collection_run,
    pdf_url,
    title,
    publication_date=None,
    timeout=30,
):
    """
    Download a newspaper PDF, validate it, prevent duplicates,
    save it and register it in the database.

    Returns:
        (SourceDocument, duplicate)
        duplicate is True if the PDF already exists.
    """

    # 1. Validate source
    if not source.is_active:
        raise ValueError("This newspaper source is inactive.")

    # 2. Validate URL
    parsed_url = urlparse(pdf_url)

    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError("A valid HTTP or HTTPS PDF URL is required.")

    if not title:
        raise ValueError("Document title is required.")

    # 3. Decide storage date
    storage_date = publication_date or timezone.localdate()

    relative_directory = (
        Path("newspapers")
        / str(storage_date.year)
        / f"{storage_date.month:02d}"
    )

    storage_directory = Path(settings.MEDIA_ROOT) / relative_directory
    storage_directory.mkdir(parents=True, exist_ok=True)

    temporary_path = None
    final_path = None

    try:
        # 4. Download PDF into a temporary file
        with requests.get(
            pdf_url,
            stream=True,
            timeout=timeout,
            headers={"User-Agent": "EstateNoticeAlertSystem/1.0"},
        ) as response:

            response.raise_for_status()

            content_length = response.headers.get("Content-Length")

            if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                raise ValueError("PDF exceeds the 100 MB download limit.")

            file_hash = hashlib.sha256()
            downloaded_size = 0

            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=storage_directory,
                prefix=".download-",
                suffix=".part",
                delete=False,
            ) as temporary_file:

                temporary_path = Path(temporary_file.name)

                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue

                    downloaded_size += len(chunk)

                    if downloaded_size > MAX_DOWNLOAD_BYTES:
                        raise ValueError(
                            "PDF exceeds the 100 MB download limit."
                        )

                    file_hash.update(chunk)
                    temporary_file.write(chunk)

        # 5. Verify that the downloaded file is actually a PDF
        with temporary_path.open("rb") as pdf_file:
            file_signature = pdf_file.read(5)

        if file_signature != b"%PDF-":
            raise ValueError("Downloaded file is not a valid PDF.")

        # 6. Calculate SHA-256 hash
        file_hash_value = file_hash.hexdigest()

        # 7. Check for an existing document with the same hash
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

        # 8. Create a permanent filename using the hash
        filename = f"{file_hash_value}.pdf"

        relative_file_path = relative_directory / filename
        final_path = Path(settings.MEDIA_ROOT) / relative_file_path

        # 9. Move temporary download to permanent storage
        os.replace(temporary_path, final_path)
        temporary_path = None

        try:
            # 10. Register document and collection relationship
            with transaction.atomic():

                document = SourceDocument.objects.create(
                    source=source,
                    title=title,
                    source_url=pdf_url,
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
            # Remove the saved file if database registration fails
            final_path.unlink(missing_ok=True)
            raise

    finally:
        # Clean up incomplete temporary downloads
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
