from rest_framework import serializers
from .models import CollectionRun


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
