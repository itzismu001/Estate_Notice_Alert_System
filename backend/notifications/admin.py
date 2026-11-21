from django.contrib import admin
from .models import WhatsAppSubscription, NotificationLog


@admin.register(WhatsAppSubscription)
class WhatsAppSubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "phone_number",
        "is_opted_in",
        "is_verified",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_opted_in",
        "is_verified",
        "is_active",
        "created_at",
    )

    search_fields = (
        "phone_number",
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "subscription",
        "notice",
        "status",
        "provider_message_id",
        "sent_at",
        "delivered_at",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "subscription__phone_number",
        "notice__title",
        "provider_message_id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)
