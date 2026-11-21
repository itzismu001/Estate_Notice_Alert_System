from django.db import models
from django.contrib.auth.models import User


class WhatsAppSubscription(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="whatsapp_subscriptions"
    )

    phone_number = models.CharField(max_length=20)

    is_opted_in = models.BooleanField(default=False)

    is_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    opted_in_at = models.DateTimeField(
        blank=True,
        null=True
    )

    verified_at = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "whatsapp_subscriptions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone_number} - User {self.user_id}"


class NotificationLog(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"

    subscription = models.ForeignKey(
        WhatsAppSubscription,
        on_delete=models.PROTECT,
        related_name="notification_logs"
    )

    notice = models.ForeignKey(
        "notices.Notice",
        on_delete=models.PROTECT,
        related_name="notification_logs"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    provider_message_id = models.CharField(
        max_length=255,
        blank=True
    )

    sent_at = models.DateTimeField(
        blank=True,
        null=True
    )

    delivered_at = models.DateTimeField(
        blank=True,
        null=True
    )

    failed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_logs"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "notice"],
                name="unique_subscription_notice_notification"
            )
        ]

    def __str__(self):
        return f"Notification {self.id} - {self.status}"
