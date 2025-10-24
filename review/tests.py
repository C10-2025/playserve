from django.test import TestCase, Client
from django.urls import reverse
from review.models import Review
from main.models import Lapangan


class ReviewViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.add_url = reverse('review:add_review')
        self.list_url = reverse('review:review_list')

    def test_post_creates_review_and_returns_json(self):
        lap = Lapangan.objects.create(nama='Test Court', lokasi='Jakarta', harga=100000)
        data = {
            'lapangan': str(lap.id),
            'rating': '4',
            'komentar': 'Great place'
        }
        resp = self.client.post(self.add_url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')
        json = resp.json()
        self.assertEqual(json.get('status'), 'success')
        # check database
        self.assertTrue(Review.objects.filter(lapangan=lap, rating=4, komentar='Great place').exists())

    def test_ajax_get_returns_fragment_html(self):
        resp = self.client.get(self.add_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Should contain form element
        self.assertIn('id="add-review-form', content)

    def test_non_ajax_get_redirects_to_list(self):
        resp = self.client.get(self.add_url)
        # redirect to review list
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self.list_url, resp['Location'])

