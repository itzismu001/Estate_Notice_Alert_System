from django.contrib import admin
from .models import SourceDocument, DocumentPage


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "title",
        "source",
        "publication_date",
        "document_type",
        "status",
        "downloaded_at",
    )

    list_filter = (
        "status",
        "document_type",
        "publication_date",
        "source",
    )

    search_fields = (
        "title",
        "source__name",
        "file_hash",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)


@admin.register(DocumentPage)
class DocumentPageAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "document",
        "page_number",
        "page_type",
        "processing_status",
    )

    list_filter = (
        "page_type",
        "processing_status",
    )

    search_fields = (
        "document__title",
        "extracted_text",
        "ocr_text",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("document", "page_number")
