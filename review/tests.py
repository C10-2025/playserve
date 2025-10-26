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
        # check database
        self.assertTrue(Review.objects.filter(field=self.field, rating=4, komentar='Great place').exists())

    def test_ajax_get_returns_fragment_html(self):
        resp = self.client.get(self.add_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('form', content)

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

        # Create review
        self.review = Review.objects.create(
            field=self.field, rating=5, komentar='Excellent!'
        )

        # Create users
        self.admin_user = User.objects.create_superuser(
            username='admin', email='admin@test.com', password='pass1234'
        )
        self.regular_user = User.objects.create_user(
            username='user', email='user@test.com', password='pass1234'
        )

        self.delete_url = reverse('review:delete-review', args=[self.review.id])

    def test_admin_can_delete_review(self):
        """Admin should be able to delete a review successfully."""
        self.client.login(username='admin', password='pass1234')

        response = self.client.post(
            self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        json_data = response.json()
        self.assertEqual(json_data['status'], 'success')

        # Review should be deleted
        self.assertFalse(Review.objects.filter(id=self.review.id).exists())

    def test_non_admin_cannot_delete_review(self):
        """Regular users should not be allowed to delete reviews."""
        self.client.login(username='user', password='pass1234')

        response = self.client.post(
            self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # Expect forbidden or error JSON
        self.assertNotEqual(response.status_code, 200)
        try:
            data = response.json()
            self.assertIn('error', data.get('status', 'error'))
        except Exception:
            self.assertTrue(True)  # Non-JSON response fallback

        # Review should still exist
        self.assertTrue(Review.objects.filter(id=self.review.id).exists())

    def test_unauthenticated_user_cannot_delete_review(self):
        """Unauthenticated users should be redirected or denied."""
        response = self.client.post(
            self.delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertIn(response.status_code, [302, 403])
        self.assertTrue(Review.objects.filter(id=self.review.id).exists())
