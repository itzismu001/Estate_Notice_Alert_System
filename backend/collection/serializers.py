from rest_framework import serializers

from .models import CollectionRun
from sources.models import Source


class CollectionPDFSerializer(serializers.Serializer):

    source_id = serializers.IntegerField(min_value=1)

    pdf_url = serializers.URLField(max_length=1000)

    title = serializers.CharField(max_length=500)

    publication_date = serializers.DateField(
        required=False,
        allow_null=True
    )

    def validate_source_id(self, value):

        if not Source.objects.filter(
            id=value,
            is_active=True
        ).exists():

            raise serializers.ValidationError(
                "Source does not exist or is inactive."
            )

        return value


class CollectionRunCreateSerializer(serializers.Serializer):

    pdf_list = CollectionPDFSerializer(
        many=True,
        allow_empty=False
    )


class CollectionRunSerializer(serializers.ModelSerializer):

    class Meta:
        model = CollectionRun

        fields = [
            "id",
            "started_at",
            "finished_at",
            "status",
            "total_documents",
            "successful_documents",
            "failed_documents",
            "error_message",
        ]

        read_only_fields = fields
