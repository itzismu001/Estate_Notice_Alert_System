from django.db import models


class CollectionRun(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        PARTIAL = "PARTIAL", "Partially Completed"

    started_at = models.DateTimeField(auto_now_add=True)

    finished_at = models.DateTimeField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    total_documents = models.PositiveIntegerField(default=0)
    successful_documents = models.PositiveIntegerField(default=0)
    failed_documents = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "collection_runs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Collection Run {self.id} - {self.status}"


class CollectionRunDocument(models.Model):

    collection_run = models.ForeignKey(
        CollectionRun,
        on_delete=models.CASCADE,
        related_name="run_documents"
    )

    document = models.ForeignKey(
        "documents.SourceDocument",
        on_delete=models.PROTECT,
        related_name="collection_records"
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "collection_run_documents"

        constraints = [
            models.UniqueConstraint(
                fields=["collection_run", "document"],
                name="unique_collection_run_document"
            )
        ]

    def __str__(self):
        return f"Run {self.collection_run_id} - Document {self.document_id}"
