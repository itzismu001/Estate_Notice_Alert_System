from rest_framework import serializers

from .models import (
    SourceDocument,
    DocumentPage,
    ProcessingJob,
)


class SourceDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = SourceDocument

        fields = [
            "id",
            "source",
            "title",
            "source_url",
            "publication_date",
            "file_path",
            "file_hash",
            "document_type",
            "status",
            "downloaded_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "file_path",
            "file_hash",
            "status",
            "downloaded_at",
            "created_at",
            "updated_at",
        ]

    def validate_source(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot register a document for an inactive source."
            )

        return value


class DocumentPageSerializer(serializers.ModelSerializer):

    class Meta:
        model = DocumentPage

        fields = [
            "id",
            "document",
            "page_number",
            "page_type",
            "extracted_text",
            "ocr_text",
            "page_image_path",
            "page_width",
            "page_height",
            "processing_status",
            "error_message",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


class ProcessingJobSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProcessingJob

        fields = [
            "id",
            "document",
            "page",
            "job_type",
            "status",
            "retry_count",
            "max_retries",
            "celery_task_id",
            "started_at",
            "completed_at",
            "error_message",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
