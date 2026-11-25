from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SourceAPITests(APITestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="test_admin",
            password="TestPassword123!",
            is_staff=True,
        )

        self.client.force_authenticate(user=self.admin)

    def test_admin_can_list_sources(self):
        url = reverse("source-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

# Create your tests here.
