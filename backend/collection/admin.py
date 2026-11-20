from django.contrib import admin
from .models import CollectionRun, CollectionRunDocument


@admin.register(CollectionRun)
class CollectionRunAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "started_at",
        "finished_at",
        "status",
        "total_documents",
        "successful_documents",
        "failed_documents",
    )

    list_filter = (
        "status",
        "started_at",
    )

    search_fields = (
        "error_message",
    )

    readonly_fields = (
        "started_at",
    )

    ordering = ("-started_at",)


@admin.register(CollectionRunDocument)
class CollectionRunDocumentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "collection_run",
        "document",
        "added_at",
    )

    list_filter = (
        "added_at",
    )

    search_fields = (
        "document__title",
    )

    readonly_fields = (
        "added_at",
    )

    ordering = ("-added_at",)
