from rest_framework import serializers
from .models import SourceDocument


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
