from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from review.models import Review
from booking.models import PlayingField
from statistics import mean, median, mode, StatisticsError
# TODO: fix testing errors (note that the modules work properly)
class ReviewViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.add_url = reverse('review:add_review')
        self.list_url = reverse('review:review_list')

        self.field = PlayingField.objects.create(
            name='Test Field', address='Jakarta', price_per_hour=100000, image_url=''
        )

    def test_post_creates_review_and_returns_json(self):
        User.objects.create_user("tester", "t@test.com", "pass123")
        self.client.login(username="tester", password="pass123")

        data = {
            'field': str(self.field.id),
            'rating': '4',
            'komentar': 'Great place'
        }
        resp = self.client.post(self.add_url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(resp.status_code, 200)


    def test_ajax_get_returns_fragment_html(self):
        resp = self.client.get(self.add_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.content.decode('utf-8'))

    def test_non_ajax_get_redirects_to_list(self):
        resp = self.client.get(self.add_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self.list_url, resp['Location'])


# -------- Delete functionality --------
class DeleteReviewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.field = PlayingField.objects.create(
            name='Admin Field', address='Bandung', price_per_hour=120000, image_url=''
        )
        self.admin_user = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='pass1234'
        )
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='pass1234'
        )
        self.review = Review.objects.create(
            user=self.admin_user,
            field=self.field,
            rating=5,
            komentar='Excellent!'
        )
        self.delete_url = reverse('review:delete-review', args=[self.review.id])

    def test_admin_can_delete_review(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.post(self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        json_data = response.json()
        self.assertEqual(json_data['status'], 'success')
        self.assertFalse(Review.objects.filter(id=self.review.id).exists())

    def test_non_admin_cannot_delete_review(self):
        self.client.login(username='user', password='pass1234')
        response = self.client.post(self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertIn("/login", response.url) #redirected
        self.assertTrue(Review.objects.filter(id=self.review.id).exists())

    def test_unauthenticated_user_cannot_delete_review(self):
        response = self.client.post(self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertIn("/login", response.url) #redirected
        self.assertTrue(Review.objects.filter(id=self.review.id).exists())


# -------- Search Feature --------
class ReviewSearchBarTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('review:review_list_search_bar')

        self.field1 = PlayingField.objects.create(
            name='Jakarta Arena', address='Central Jakarta', city='Jakarta',
            price_per_hour=100000, image_url=''
        )
        self.field2 = PlayingField.objects.create(
            name='Bogor Tennis Center', address='West Bogor', city='Bogor',
            price_per_hour=150000, image_url=''
        )
        self.field3 = PlayingField.objects.create(
            name='Bekasi Sports Club', address='Bekasi Timur', city='Bekasi',
            price_per_hour=90000, image_url=''
        )

    def test_search_page_loads_successfully(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertTrue('Court Reviews' in content or 'Review Management' in content)

    def test_search_by_name_returns_correct_field(self):
        response = self.client.get(self.url, {'search': 'Bogor'})
        content = response.content.decode()
        self.assertContains(response, 'Bogor Tennis Center')
        self.assertNotIn('Jakarta Arena', content)

    def test_search_by_city_returns_correct_field(self):
        response = self.client.get(self.url, {'search': 'Bekasi'})
        self.assertContains(response, 'Bekasi Sports Club')
        self.assertNotContains(response, 'Jakarta Arena')

    def test_search_with_no_match_displays_empty_message(self):
        response = self.client.get(self.url, {'search': 'Surabaya'})
        self.assertContains(response, 'No courts found.')

    def test_search_is_case_insensitive(self):
        response = self.client.get(self.url, {'search': 'jakarta'})
        self.assertContains(response, 'Jakarta Arena')


# For suggested features
class ReviewFeatureExtensionTests(TestCase):
    """
    Tests for new features:
    - One review per user per field
    - Updating reviews
    - Sorting
    - Admin analytics
    """
    def setUp(self):
        self.client = Client()

        # Users
        self.user = User.objects.create_user(
            "regular", "r@test.com", "pass"
        )
        self.admin = User.objects.create_superuser(
            "admin", "a@test.com", "pass"
        )

        # Fields
        self.field1 = PlayingField.objects.create(
            name="Court A", address="A", city="X", price_per_hour=10000
        )
        self.field2 = PlayingField.objects.create(
            name="Court B", address="B", city="X", price_per_hour=20000
        )

    # ---------------------
    # Review overwrite test
    # ---------------------
    def test_review_is_updated_if_user_reviews_again(self):
        self.client.login(username="regular", password="pass")

        # First review
        self.client.post(
            reverse("review:add_review"),
            {"field": self.field1.id, "rating": 5, "komentar": "Great"},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # Update review
        self.client.post(
            reverse("review:add_review"),
            {"field": self.field1.id, "rating": 2, "komentar": "Changed"},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        r = Review.objects.get(field=self.field1, user=self.user)
        self.assertEqual(r.rating, 2)
        self.assertEqual(r.komentar, "Changed")

        # Only one review
        self.assertEqual(
            Review.objects.filter(field=self.field1, user=self.user).count(), 1
        )

    # ---------------------
    # Sorting tests
    # ---------------------
    def test_sort_high_to_low(self):
        Review.objects.create(user=self.admin, field=self.field1, rating=5)
        Review.objects.create(user=self.user, field=self.field2, rating=1)

        url = reverse("review:review_list") + "?sort=avg_desc"
        response = self.client.get(url)

        fields = list(response.context["fields"])
        self.assertEqual(fields[0], self.field1)  # Highest first

    def test_sort_low_to_high(self):
        Review.objects.create(user=self.admin, field=self.field1, rating=5)
        Review.objects.create(user=self.user, field=self.field2, rating=1)

        url = reverse("review:review_list") + "?sort=avg_asc"
        response = self.client.get(url)

        fields = list(response.context["fields"])
        self.assertEqual(fields[0], self.field2)  # Lowest first

    def test_fields_with_no_reviews_count_as_zero(self):
        Review.objects.create(user=self.admin, field=self.field1, rating=4)
        # field2 has zero reviews

        url = reverse("review:review_list") + "?sort=avg_asc"
        response = self.client.get(url)

        fields = list(response.context["fields"])
        self.assertEqual(fields[0], self.field2)

    # ---------------------
    # ADMIN ANALYTICS
    # ---------------------
    def test_admin_can_see_analytics(self):
        Review.objects.create(user=self.admin, field=self.field1, rating=5)
        self.client.login(username="admin", password="pass")

        response = self.client.get(reverse("review:review_list"))
        self.assertIn("analytics", response.context)

    def test_normal_user_cannot_see_analytics(self):
        self.client.login(username="regular", password="pass")
        response = self.client.get(reverse("review:review_list"))
        self.assertEqual(response.context["analytics"], {}) # Empty analytics

    def test_analytics_calculations_are_correct(self):
        Review.objects.create(user=self.admin, field=self.field1, rating=5)
        Review.objects.create(user=self.user, field=self.field2, rating=3)
        Review.objects.create(user=self.user, field=self.field1, rating=1)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("review:review_list"))

        data = response.context["analytics"]

        self.assertEqual(data["total_reviews"], 3)
        self.assertAlmostEqual(data["mean"], 3.0)
        self.assertAlmostEqual(data["median"], 3.0)
        self.assertEqual(data["mode"], 1.0)
