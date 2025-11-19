from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from review.models import Review
from booking.models import PlayingField  


class ReviewViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.add_url = reverse('review:add_review')
        self.list_url = reverse('review:review_list')

        self.field = PlayingField.objects.create(
            name='Test Field', address='Jakarta', price_per_hour=100000, image_url=''
        )

    def test_post_creates_review_and_returns_json(self):
        data = {
            'field': str(self.field.id),
            'rating': '4',
            'komentar': 'Great place'
        }
        resp = self.client.post(self.add_url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')
        json = resp.json()
        self.assertEqual(json.get('status'), 'success')
        self.assertTrue(Review.objects.filter(field=self.field, rating=4, komentar='Great place').exists())

    def test_ajax_get_returns_fragment_html(self):
        resp = self.client.get(self.add_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('form', resp.content.decode('utf-8'))

    def test_non_ajax_get_redirects_to_list(self):
        resp = self.client.get(self.add_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self.list_url, resp['Location'])


# Delete functionality
class DeleteReviewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.field = PlayingField.objects.create(
            name='Admin Field', address='Bandung', price_per_hour=120000, image_url=''
        )
        self.review = Review.objects.create(field=self.field, rating=5, komentar='Excellent!')
        self.admin_user = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='pass1234'
        )
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='pass1234'
        )
        self.delete_url = reverse('review:delete-review', args=[self.review.id])

    def test_admin_can_delete_review(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.post(self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data['status'], 'success')
        self.assertFalse(Review.objects.filter(id=self.review.id).exists())

    def test_non_admin_cannot_delete_review(self):
        self.client.login(username='user', password='pass1234')
        response = self.client.post(self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(Review.objects.filter(id=self.review.id).exists())

    def test_unauthenticated_user_cannot_delete_review(self):
        response = self.client.post(self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertIn(response.status_code, [302, 403])
        self.assertTrue(Review.objects.filter(id=self.review.id).exists())


# New Tests for Search Feature (search-review/)
class ReviewSearchBarTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('review:review_list_search_bar')

        self.field1 = PlayingField.objects.create(
            name='Jakarta Arena',
            address='Central Jakarta',
            city='Jakarta',
            price_per_hour=100000,
            image_url=''
        )
        self.field2 = PlayingField.objects.create(
            name='Bogor Tennis Center',
            address='West Bogor',
            city='Bogor',
            price_per_hour=150000,
            image_url=''
        )
        self.field3 = PlayingField.objects.create(
            name='Bekasi Sports Club',
            address='Bekasi Timur',
            city='Bekasi',
            price_per_hour=90000,
            image_url=''
        )

    def test_search_page_loads_successfully(self):
        """The search page should render successfully."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Check that either heading appears (pengguna biasa atau admin)
        self.assertTrue(
            'Court Reviews' in content or 'Review Management' in content
        )

    def test_search_by_name_returns_correct_field(self):
        """Searching by field name should return matching results."""
        response = self.client.get(self.url, {'search': 'Bogor'})
        content = response.content.decode()
        self.assertContains(response, 'Bogor Tennis Center')
        self.assertNotIn('Jakarta Arena', content)

    def test_search_by_city_returns_correct_field(self):
        """Searching by city should return fields in that city."""
        response = self.client.get(self.url, {'search': 'Bekasi'})
        self.assertContains(response, 'Bekasi Sports Club')
        self.assertNotContains(response, 'Jakarta Arena')

    def test_search_with_no_match_displays_empty_message(self):
        """Non-matching search should display 'No courts found.'"""
        response = self.client.get(self.url, {'search': 'Surabaya'})
        self.assertContains(response, 'No courts found.')

    def test_search_is_case_insensitive(self):
        """Search should not depend on letter casing."""
        response = self.client.get(self.url, {'search': 'jakarta'})
        self.assertContains(response, 'Jakarta Arena')
