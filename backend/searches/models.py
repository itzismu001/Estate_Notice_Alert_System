
from django.db import models
from django.contrib.auth.models import User


class SavedSearch(models.Model):

    class MatchMode(models.TextChoices):
        ALL = "ALL", "Match All Criteria"
        ANY = "ANY", "Match Any Criteria"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_searches"
    )

    name = models.CharField(max_length=255)

    match_mode = models.CharField(
        max_length=10,
        choices=MatchMode.choices,
        default=MatchMode.ALL
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saved_searches"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - User {self.user_id}"


class SavedSearchCriteria(models.Model):

    class FieldType(models.TextChoices):
        PROPERTY_NUMBER = "PROPERTY_NUMBER", "Property Number"
        SURVEY_NUMBER = "SURVEY_NUMBER", "Survey Number"
        SUBDIVISION_NUMBER = "SUBDIVISION_NUMBER", "Subdivision Number"
        TP_NUMBER = "TP_NUMBER", "TP Number"
        PLOT_NUMBER = "PLOT_NUMBER", "Plot Number"
        PROPERTY_ADDRESS = "PROPERTY_ADDRESS", "Property Address"
        LOCATION = "LOCATION", "Location"
        OWNER = "OWNER", "Owner"
        LEGAL_HEIR = "LEGAL_HEIR", "Legal Heir"
        ADVOCATE = "ADVOCATE", "Advocate"

    class MatchType(models.TextChoices):
        EXACT = "EXACT", "Exact Match"
        CONTAINS = "CONTAINS", "Contains"
        PARTIAL = "PARTIAL", "Partial Match"

    saved_search = models.ForeignKey(
        SavedSearch,
        on_delete=models.CASCADE,
        related_name="criteria"
    )

    field_type = models.CharField(
        max_length=30,
        choices=FieldType.choices
    )

    match_type = models.CharField(
        max_length=15,
        choices=MatchType.choices,
        default=MatchType.CONTAINS
    )

    search_value = models.CharField(max_length=500)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "saved_search_criteria"
        ordering = ["id"]

    def __str__(self):
        return f"{self.field_type}: {self.search_value}"

