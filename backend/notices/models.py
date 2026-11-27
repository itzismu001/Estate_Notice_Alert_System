
from django.db import models
from django.contrib.auth.models import User


class Notice(models.Model):

    class Status(models.TextChoices):
        NEEDS_REVIEW = "NEEDS_REVIEW", "Needs Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class Confidence(models.TextChoices):
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    title = models.CharField(max_length=500, blank=True)
    notice_type = models.CharField(max_length=100, blank=True)
    notice_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)

    confidence = models.CharField(
        max_length=10,
        choices=Confidence.choices,
        default=Confidence.LOW
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEEDS_REVIEW
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_notices"
    )

    reviewed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notices"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Notice {self.id}"


class NoticeEntity(models.Model):

    class EntityType(models.TextChoices):
        PROPERTY_NUMBER = "PROPERTY_NUMBER", "Property Number"
        SURVEY_NUMBER = "SURVEY_NUMBER", "Survey Number"
        SUBDIVISION_NUMBER = "SUBDIVISION_NUMBER", "Subdivision Number"
        TP_NUMBER = "TP_NUMBER", "TP Number"
        PLOT_NUMBER = "PLOT_NUMBER", "Plot Number"
        PROPERTY_ADDRESS = "PROPERTY_ADDRESS", "Property Address"
        LOCATION = "LOCATION", "Location"
        OWNER = "OWNER", "Owner"
        LEGAL_HEIR = "LEGAL_HEIR", "Legal Heir"
        ADVOCATE = "ADVOCATE", "Advocate"
        NOTICE_DATE = "NOTICE_DATE", "Notice Date"
        OBJECTION_DEADLINE = "OBJECTION_DEADLINE", "Objection Deadline"
        OTHER = "OTHER", "Other"

    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name="entities"
    )

    entity_type = models.CharField(
        max_length=30,
        choices=EntityType.choices
    )

    value = models.TextField()

    confidence = models.CharField(
        max_length=10,
        choices=Notice.Confidence.choices,
        default=Notice.Confidence.LOW
    )

    source_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notice_entities"
        ordering = ["entity_type", "id"]

    def __str__(self):
        return f"{self.entity_type}: {self.value}"


class ReviewHistory(models.Model):

    class Action(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CORRECTED = "CORRECTED", "Corrected"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"

    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name="review_history"
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="notice_review_actions"
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices
    )

    previous_status = models.CharField(
        max_length=20,
        choices=Notice.Status.choices,
        blank=True
    )

    new_status = models.CharField(
        max_length=20,
        choices=Notice.Status.choices,
        blank=True
    )

    comments = models.TextField(blank=True)

    changes = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - Notice {self.notice_id}"


class NoticePage(models.Model):

    class CoordinateFormat(models.TextChoices):
        XYWH = "XYWH", "X, Y, Width, Height"
        XYXY = "XYXY", "X1, Y1, X2, Y2"
        UNKNOWN = "UNKNOWN", "Unknown"

    class CoordinateUnit(models.TextChoices):
        PIXELS = "PIXELS", "Pixels"
        NORMALIZED = "NORMALIZED", "Normalized"
        UNKNOWN = "UNKNOWN", "Unknown"

    notice = models.ForeignKey(
        Notice,
        on_delete=models.CASCADE,
        related_name="notice_pages"
    )

    document_page = models.ForeignKey(
        "documents.DocumentPage",
        on_delete=models.PROTECT,
        related_name="notice_links"
    )

    page_sequence = models.PositiveIntegerField(
        default=1,
        help_text="Order of this page within a multi-page notice."
    )

    crop_image_path = models.CharField(
        max_length=1000,
        blank=True
    )

    bounding_box = models.JSONField(
        default=dict,
        blank=True,
        help_text="Bounding box coordinates returned by the cropping module."
    )

    coordinate_format = models.CharField(
        max_length=10,
        choices=CoordinateFormat.choices,
        default=CoordinateFormat.UNKNOWN
    )

    coordinate_unit = models.CharField(
        max_length=15,
        choices=CoordinateUnit.choices,
        default=CoordinateUnit.UNKNOWN
    )

    extracted_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notice_pages"
        ordering = ["notice", "page_sequence", "id"]

    def __str__(self):
        return f"Notice {self.notice_id} - Document Page {self.document_page_id}"


class NoticeExtractionEvidence(models.Model):

    notice_page = models.ForeignKey(
        NoticePage,
        on_delete=models.CASCADE,
        related_name="extraction_evidence"
    )

    schema_version = models.CharField(
        max_length=30,
        default="1.0"
    )

    pipeline_version = models.CharField(
        max_length=50
    )

    language = models.CharField(
        max_length=20,
        blank=True
    )

    decision = models.CharField(
        max_length=20,
        choices=[
            ("ACCEPT", "Accept"),
            ("REVIEW", "Review"),
        ]
    )

    notice_category = models.CharField(
        max_length=100,
        blank=True
    )

    payload = models.JSONField()

    payload_hash = models.CharField(
        max_length=64
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        db_table = "notice_extraction_evidence"

        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "notice_page",
                    "payload_hash",
                ],
                name="unique_notice_page_evidence"
            )
        ]

    def __str__(self):

        return (
            f"Evidence {self.pk} - "
            f"NoticePage {self.notice_page_id}"
        )
