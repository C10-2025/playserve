from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from profil.models import Profile 
from main.views import main_view

class MainViewsTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
       
        self.profile = Profile.objects.create(
            user=self.user,
            lokasi='Jakarta',
            instagram='@testinsta',
            avatar='image/avatar1.png'
        )

    def test_main_view_unauthenticated(self):
        response = self.client.get(reverse('main:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        self.assertNotIn('profile', response.context)
        
    def test_main_view_authenticated_has_profile(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('main:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')
        self.assertIn('profile', response.context)
        self.assertEqual(response.context['profile'].lokasi, 'Jakarta')

    def test_main_view_authenticated_no_profile(self):
        User.objects.create_user(username='noprofile', password='password123')
        self.user_no_profile = User.objects.get(username='noprofile')
        self.profile.delete()
        self.client.login(username='noprofile', password='password123')
        response = self.client.get(reverse('main:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('profile', response.context)
        self.assertIsNone(response.context['profile'])