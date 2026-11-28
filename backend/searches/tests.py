
from django.contrib.auth.models import User
from django.test import TestCase

from searches.models import SavedSearch, SavedSearchCriteria


class SavedSearchTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="search_test_user",
            password="testpassword123",
        )

    def test_saved_search_default_values(self):
        saved_search = SavedSearch.objects.create(
            user=self.user,
            name="My Property Search",
        )

        self.assertEqual(
            saved_search.match_mode,
            SavedSearch.MatchMode.ALL,
        )
        self.assertTrue(saved_search.is_active)

    def test_saved_search_can_be_created_for_user(self):
        saved_search = SavedSearch.objects.create(
            user=self.user,
            name="Survey Number Search",
        )

        self.assertEqual(saved_search.user, self.user)
        self.assertEqual(saved_search.name, "Survey Number Search")

    def test_multiple_saved_searches_for_same_user(self):
        SavedSearch.objects.create(
            user=self.user,
            name="Search One",
        )
        SavedSearch.objects.create(
            user=self.user,
            name="Search Two",
        )

        self.assertEqual(
            SavedSearch.objects.filter(user=self.user).count(),
            2,
        )

    def test_user_deletion_removes_saved_searches(self):
        SavedSearch.objects.create(
            user=self.user,
            name="Temporary Search",
        )

        self.user.delete()

        self.assertEqual(SavedSearch.objects.count(), 0)


class SavedSearchCriteriaTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="criteria_test_user",
            password="testpassword123",
        )

        self.saved_search = SavedSearch.objects.create(
            user=self.user,
            name="Property Search",
        )

    def test_criteria_default_match_type(self):
        criteria = SavedSearchCriteria.objects.create(
            saved_search=self.saved_search,
            field_type=SavedSearchCriteria.FieldType.SURVEY_NUMBER,
            search_value="123/4",
        )

        self.assertEqual(
            criteria.match_type,
            SavedSearchCriteria.MatchType.CONTAINS,
        )

    def test_criteria_can_be_created(self):
        criteria = SavedSearchCriteria.objects.create(
            saved_search=self.saved_search,
            field_type=SavedSearchCriteria.FieldType.TP_NUMBER,
            match_type=SavedSearchCriteria.MatchType.EXACT,
            search_value="TP-45",
        )

        self.assertEqual(criteria.saved_search, self.saved_search)
        self.assertEqual(criteria.search_value, "TP-45")
        self.assertEqual(
            criteria.match_type,
            SavedSearchCriteria.MatchType.EXACT,
        )

    def test_multiple_criteria_for_one_saved_search(self):
        SavedSearchCriteria.objects.create(
            saved_search=self.saved_search,
            field_type=SavedSearchCriteria.FieldType.SURVEY_NUMBER,
            search_value="123/4",
        )

        SavedSearchCriteria.objects.create(
            saved_search=self.saved_search,
            field_type=SavedSearchCriteria.FieldType.LOCATION,
            search_value="Bengaluru",
        )

        self.assertEqual(self.saved_search.criteria.count(), 2)

    def test_saved_search_deletion_removes_criteria(self):
        SavedSearchCriteria.objects.create(
            saved_search=self.saved_search,
            field_type=SavedSearchCriteria.FieldType.OWNER,
            search_value="Test Owner",
        )

        self.saved_search.delete()

        self.assertEqual(SavedSearchCriteria.objects.count(), 0)
