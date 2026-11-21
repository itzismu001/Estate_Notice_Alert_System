
from django.contrib import admin
from .models import SavedSearch, SavedSearchCriteria


class SavedSearchCriteriaInline(admin.TabularInline):
    model = SavedSearchCriteria
    extra = 1


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "user",
        "match_mode",
        "is_active",
        "created_at",
    )

    list_filter = (
        "match_mode",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [SavedSearchCriteriaInline]

    ordering = ("-created_at",)


@admin.register(SavedSearchCriteria)
class SavedSearchCriteriaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "saved_search",
        "field_type",
        "match_type",
        "search_value",
        "created_at",
    )

    list_filter = (
        "field_type",
        "match_type",
        "created_at",
    )

    search_fields = (
        "search_value",
        "saved_search__name",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = ("id",)
from django.contrib import admin

# Register your models here.
