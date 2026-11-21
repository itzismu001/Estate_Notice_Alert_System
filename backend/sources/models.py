from django.db import models


class Source(models.Model):

    class SourceType(models.TextChoices):
        NEWSPAPER = "NEWSPAPER", "Newspaper"
        COURT = "COURT", "Court"

    name = models.CharField(max_length=255, unique=True)

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices
    )

    website_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )

    region = models.CharField(
        max_length=100,
        default="Karnataka"
    )

    language = models.CharField(
        max_length=50,
        default="English"
    )

    is_active = models.BooleanField(default=True)
    access_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sources"
        ordering = ["name"]

    def __str__(self):
        return self.name
