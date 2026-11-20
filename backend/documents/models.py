
from django.db import models
from sources.models import Source


class SourceDocument(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DOWNLOADED = "DOWNLOADED", "Downloaded"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    source = models.ForeignKey(
        Source,
        on_delete=models.PROTECT,
        related_name="documents"
    )

    title = models.CharField(max_length=500)

    source_url = models.URLField(
        max_length=1000,
        blank=True
    )

    publication_date = models.DateField(
        blank=True,
        null=True
    )

    file_path = models.CharField(
        max_length=1000,
        blank=True
    )

    file_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True
    )

    document_type = models.CharField(
        max_length=50,
        default="PDF"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    downloaded_at = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "source_documents"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class DocumentPage(models.Model):

    class PageType(models.TextChoices):
        TEXT = "TEXT", "Selectable Text"
        SCANNED = "SCANNED", "Scanned Image"
        MIXED = "MIXED", "Mixed Content"
        UNKNOWN = "UNKNOWN", "Unknown"

    class ProcessingStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    document = models.ForeignKey(
        SourceDocument,
        on_delete=models.CASCADE,
        related_name="pages"
    )

    page_number = models.PositiveIntegerField()

    page_type = models.CharField(
        max_length=20,
        choices=PageType.choices,
        default=PageType.UNKNOWN
    )

    extracted_text = models.TextField(blank=True)
    ocr_text = models.TextField(blank=True)

    page_image_path = models.CharField(
        max_length=1000,
        blank=True
    )

    page_width = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    page_height = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "document_pages"
        ordering = ["document", "page_number"]

        constraints = [
            models.UniqueConstraint(
                fields=["document", "page_number"],
                name="unique_document_page"
            )
        ]

    def __str__(self):
        return f"Document {self.document_id} - Page {self.page_number}"


class ProcessingJob(models.Model):

    class JobType(models.TextChoices):
        TEXT_EXTRACTION = "TEXT_EXTRACTION", "Text Extraction"
        OCR = "OCR", "OCR Processing"
        NOTICE_DETECTION = "NOTICE_DETECTION", "Notice Detection"
        DETAIL_EXTRACTION = "DETAIL_EXTRACTION", "Notice Detail Extraction"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    document = models.ForeignKey(
        SourceDocument,
        on_delete=models.CASCADE,
        related_name="processing_jobs"
    )

    page = models.ForeignKey(
        DocumentPage,
        on_delete=models.CASCADE,
        related_name="processing_jobs",
        blank=True,
        null=True
    )

    job_type = models.CharField(
        max_length=30,
        choices=JobType.choices
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)

    celery_task_id = models.CharField(
        max_length=255,
        blank=True
    )

    started_at = models.DateTimeField(
        blank=True,
        null=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "processing_jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.job_type} - Document {self.document_id}"
