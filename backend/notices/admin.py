
from django.contrib import admin
from .models import Notice, NoticeEntity, ReviewHistory, NoticePage


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "title",
        "notice_type",
        "confidence",
        "status",
        "reviewed_by",
        "created_at",
    )

    list_filter = (
        "status",
        "confidence",
        "notice_type",
        "created_at",
    )

    search_fields = (
        "title",
        "notice_text",
        "summary",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)


@admin.register(NoticeEntity)
class NoticeEntityAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "notice",
        "entity_type",
        "value",
        "confidence",
        "created_at",
    )

    list_filter = (
        "entity_type",
        "confidence",
        "created_at",
    )

    search_fields = (
        "value",
        "source_text",
        "notice__title",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("entity_type", "id")


@admin.register(ReviewHistory)
class ReviewHistoryAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "notice",
        "reviewed_by",
        "action",
        "previous_status",
        "new_status",
        "created_at",
    )

    list_filter = (
        "action",
        "previous_status",
        "new_status",
        "created_at",
    )

    search_fields = (
        "notice__title",
        "comments",
        "reviewed_by__username",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("-created_at",)


@admin.register(NoticePage)
class NoticePageAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "notice",
        "document_page",
        "page_sequence",
        "coordinate_format",
        "coordinate_unit",
        "created_at",
    )

    list_filter = (
        "coordinate_format",
        "coordinate_unit",
        "created_at",
    )

    search_fields = (
        "notice__title",
        "crop_image_path",
        "extracted_text",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("notice", "page_sequence")
