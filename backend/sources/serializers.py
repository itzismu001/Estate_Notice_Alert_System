from rest_framework import serializers
from .models import Source


class SourceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Source

        fields = [
            "id",
            "name",
            "source_type",
            "website_url",
            "region",
            "language",
            "is_active",
            "access_notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]
