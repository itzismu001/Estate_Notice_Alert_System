from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from sources.models import Source


class SourceAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="test_admin",
            password="TestPassword123!",
            is_staff=True,
        )

        self.normal_user = User.objects.create_user(
            username="test_user",
            password="TestPassword123!",
            is_staff=False,
        )

        self.client.force_authenticate(user=self.admin)

        self.source = Source.objects.create(
            name="Test Newspaper",
            source_type=Source.SourceType.NEWSPAPER,
            website_url="https://example.com",
        )

    def test_admin_can_list_sources(self):
        url = reverse("source-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_create_source(self):
        url = reverse("source-list")

        data = {
            "name": "New Court Source",
            "source_type": "COURT",
            "website_url": "https://court.example.com",
            "region": "Karnataka",
            "language": "English",
            "is_active": True,
            "access_notes": "Test source",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Source.objects.filter(name="New Court Source").exists()
        )

    def test_admin_can_retrieve_source(self):
        url = reverse("source-detail", args=[self.source.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Newspaper")

    def test_admin_can_update_source(self):
        url = reverse("source-detail", args=[self.source.id])

        data = {
            "name": "Updated Newspaper",
        }

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.source.refresh_from_db()

        self.assertEqual(self.source.name, "Updated Newspaper")

    def test_admin_can_delete_source(self):
        url = reverse("source-detail", args=[self.source.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Source.objects.filter(id=self.source.id).exists()
        )

    def test_normal_user_cannot_access_sources(self):
        self.client.force_authenticate(user=self.normal_user)

        url = reverse("source-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
