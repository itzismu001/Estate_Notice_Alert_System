
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from notices.models import Notice, NoticeEntity, ReviewHistory


class NoticeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.admin_user = User.objects.create_user(
            username="notice_admin",
            password="testpassword123",
            is_staff=True,
        )

        self.normal_user = User.objects.create_user(
            username="notice_user",
            password="testpassword123",
        )

        self.url = reverse("notices-list")

        self.notice = Notice.objects.create(
            title="Property Public Notice",
            notice_type="ESTATE_PROPERTY_NOTICE",
            notice_text="Notice regarding survey number 123.",
            summary="Property ownership claim.",
            confidence=Notice.Confidence.HIGH,
        )

    def test_admin_can_retrieve_notices(self):
        self.client.force_authenticate(user=self.admin_user)

        NoticeEntity.objects.create(
            notice=self.notice,
            entity_type=NoticeEntity.EntityType.SURVEY_NUMBER,
            value="123",
            confidence=Notice.Confidence.HIGH,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["title"],
            "Property Public Notice",
        )
        self.assertEqual(
            response.data[0]["entities"][0]["value"],
            "123",
        )

    def test_non_admin_cannot_retrieve_notices(self):
        self.client.force_authenticate(user=self.normal_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_empty_notice_list(self):
        self.client.force_authenticate(user=self.admin_user)
        self.notice.delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_notice_creation_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            self.url,
            {"title": "New Notice"},
            format="json",
        )

        self.assertEqual(response.status_code, 405)

    def test_admin_can_approve_notice(self):
        self.client.force_authenticate(user=self.admin_user)

        url = reverse(
            "notices-approve",
            args=[self.notice.id],
        )

        response = self.client.post(
            url,
            {"comments": "Property details verified."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.notice.refresh_from_db()

        self.assertEqual(
            self.notice.status,
            Notice.Status.APPROVED,
        )
        self.assertEqual(
            self.notice.reviewed_by,
            self.admin_user,
        )
        self.assertIsNotNone(self.notice.reviewed_at)

        history = ReviewHistory.objects.get(
            notice=self.notice,
        )

        self.assertEqual(
            history.action,
            ReviewHistory.Action.APPROVED,
        )
        self.assertEqual(
            history.previous_status,
            Notice.Status.NEEDS_REVIEW,
        )
        self.assertEqual(
            history.new_status,
            Notice.Status.APPROVED,
        )
        self.assertEqual(
            history.comments,
            "Property details verified.",
        )

    def test_admin_can_reject_notice(self):
        self.client.force_authenticate(user=self.admin_user)

        url = reverse(
            "notices-reject",
            args=[self.notice.id],
        )

        response = self.client.post(
            url,
            {"comments": "Incorrect property information."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.notice.refresh_from_db()

        self.assertEqual(
            self.notice.status,
            Notice.Status.REJECTED,
        )

        history = ReviewHistory.objects.get(
            notice=self.notice,
        )

        self.assertEqual(
            history.action,
            ReviewHistory.Action.REJECTED,
        )
        self.assertEqual(
            history.new_status,
            Notice.Status.REJECTED,
        )

    def test_normal_user_cannot_approve_notice(self):
        self.client.force_authenticate(user=self.normal_user)

        url = reverse(
            "notices-approve",
            args=[self.notice.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_reject_notice(self):
        self.client.force_authenticate(user=self.normal_user)

        url = reverse(
            "notices-reject",
            args=[self.notice.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)

    def test_already_approved_notice_cannot_be_reviewed_again(self):
        self.client.force_authenticate(user=self.admin_user)

        self.notice.status = Notice.Status.APPROVED
        self.notice.save(update_fields=["status"])

        url = reverse(
            "notices-reject",
            args=[self.notice.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            ReviewHistory.objects.filter(notice=self.notice).count(),
            0,
        )
