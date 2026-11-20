from django.contrib import admin
from .models import Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "region",
        "language",
        "is_active",
    )

    list_filter = (
        "source_type",
        "region",
        "language",
        "is_active",
    )

    search_fields = (
        "name",
        "region",
    )

    ordering = ("name",)
