
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from notices.models import Notice
from notifications.models import (
    WhatsAppSubscription,
    NotificationLog,
)


class NotificationModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="notification_test_user",
            password="testpassword123",
        )

        self.subscription = WhatsAppSubscription.objects.create(
            user=self.user,
            phone_number="+919876543210",
            is_opted_in=True,
            is_verified=True,
        )

        self.notice = Notice.objects.create(
            title="Test Property Notice",
            notice_type="ESTATE_PROPERTY_NOTICE",
            notice_text="Test notice text.",
        )

    def test_subscription_default_values(self):
        subscription = WhatsAppSubscription.objects.create(
            user=self.user,
            phone_number="+919876543211",
        )

        self.assertFalse(subscription.is_opted_in)
        self.assertFalse(subscription.is_verified)
        self.assertTrue(subscription.is_active)

    def test_notification_default_status_is_pending(self):
        notification = NotificationLog.objects.create(
            subscription=self.subscription,
            notice=self.notice,
        )

        self.assertEqual(
            notification.status,
            NotificationLog.Status.PENDING,
        )

    def test_duplicate_notification_is_prevented(self):
        NotificationLog.objects.create(
            subscription=self.subscription,
            notice=self.notice,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificationLog.objects.create(
                    subscription=self.subscription,
                    notice=self.notice,
                )

    def test_subscription_deletion_is_protected(self):
        NotificationLog.objects.create(
            subscription=self.subscription,
            notice=self.notice,
        )

        with self.assertRaises(ProtectedError):
            self.subscription.delete()

    def test_notice_deletion_is_protected(self):
        NotificationLog.objects.create(
            subscription=self.subscription,
            notice=self.notice,
        )

        with self.assertRaises(ProtectedError):
            self.notice.delete()
