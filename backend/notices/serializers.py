
from rest_framework import serializers

from .models import (
    Notice,
    NoticeEntity,
    ReviewHistory,
    NoticePage,
)


class NoticeEntitySerializer(serializers.ModelSerializer):

    class Meta:
        model = NoticeEntity
        fields = "__all__"
        read_only_fields = (
            "id",
            "notice",
            "entity_type",
            "value",
            "confidence",
            "source_text",
            "created_at",
            "updated_at",
        )


class ReviewHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ReviewHistory
        fields = "__all__"
        read_only_fields = (
            "id",
            "notice",
            "reviewed_by",
            "action",
            "previous_status",
            "new_status",
            "comments",
            "changes",
            "created_at",
        )


class NoticePageSerializer(serializers.ModelSerializer):

    class Meta:
        model = NoticePage
        fields = "__all__"
        read_only_fields = (
            "id",
            "notice",
            "document_page",
            "page_sequence",
            "crop_image_path",
            "bounding_box",
            "coordinate_format",
            "coordinate_unit",
            "extracted_text",
            "created_at",
        )


class NoticeSerializer(serializers.ModelSerializer):

    entities = NoticeEntitySerializer(many=True, read_only=True)
    review_history = ReviewHistorySerializer(many=True, read_only=True)
    notice_pages = NoticePageSerializer(many=True, read_only=True)

    class Meta:
        model = Notice

        fields = [
            "id",
            "title",
            "notice_type",
            "notice_text",
            "summary",
            "confidence",
            "status",
            "reviewed_by",
            "reviewed_at",
            "entities",
            "review_history",
            "notice_pages",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
