from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from profil.models import Profile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import json

class ProfileViewsTest(TestCase):
    app_name = 'profil'
    
    def setUp(self):
        self.client = Client()
        self.user_data = {'username': 'testuser', 'password': 'password123'}
        self.user = User.objects.create_user(**self.user_data)
       
        self.valid_profile_data = {
            'lokasi': Profile.KOTA_CHOICES[0][0],
            'instagram': '@testinsta',
            'avatar': Profile.AVATAR_CHOICES[0][0]
        }
    
        self.profile = Profile.objects.create(
            user=self.user,
            **self.valid_profile_data
        )

    def test_register1_get(self):
        response = self.client.get(reverse(f'{self.app_name}:register1'))
        self.assertEqual(response.status_code, 200)

    def test_register1_post_success(self):
        data = {'username': 'newuser', 'password': 'newpassword', 'password2': 'newpassword'}
        response = self.client.post(reverse(f'{self.app_name}:register1'), data)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'success', 'redirect_url': '/profile/register/step2/'})
        self.assertIn('registration_data', self.client.session)

    def test_register1_post_username_exists_failure(self):
        data = {'username': 'testuser', 'password': 'anypassword', 'password2': 'anypassword'}
        response = self.client.post(reverse(f'{self.app_name}:register1'), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('errors', response.json())

    def test_register1_post_password_mismatch_failure(self):
        data = {'username': 'userfail', 'password': 'passA', 'password2': 'passB'}
        response = self.client.post(reverse(f'{self.app_name}:register1'), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('password2', response.json()['errors'])

    def test_register2_get_no_session(self):
        response = self.client.get(reverse(f'{self.app_name}:register2'))
        self.assertRedirects(response, reverse(f'{self.app_name}:register1'))

    def test_register2_post_success_and_login(self):
        session = self.client.session
        session['registration_data'] = {'username': 'reg2user', 'password': 'regpassword'}
        session.save()
        
        data_step2 = {
            'lokasi': Profile.KOTA_CHOICES[1][0],
            'instagram': '@newinsta',
            'avatar': Profile.AVATAR_CHOICES[1][0]
        }
        
        response = self.client.post(reverse(f'{self.app_name}:register2'), data_step2)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='reg2user').exists())
        self.assertJSONEqual(response.content, {'status': 'success', 'message': 'Registration successful! Welcome.', 'redirect_url': '/'})
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_register2_post_invalid_form_data(self):
        session = self.client.session
        session['registration_data'] = {'username': 'reg2fail', 'password': 'regpassword'}
        session.save()
       
        invalid_data = {
            'lokasi': 'Venus', 
            'instagram': '@fail',
            'avatar': Profile.AVATAR_CHOICES[1][0]
        }
        
        response = self.client.post(reverse(f'{self.app_name}:register2'), invalid_data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('lokasi', response.json()['errors'])
        self.assertIn('registration_data', self.client.session)
   
    def test_login_success(self):
        data = {'username': 'testuser', 'password': 'password123'}
        response = self.client.post(reverse(f'{self.app_name}:login'), data)
        self.assertEqual(response.status_code, 200)

    def test_login_failure_invalid_credentials(self):
        data = {'username': 'testuser', 'password': 'wrongpassword'}
        response = self.client.post(reverse(f'{self.app_name}:login'), data)
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(response.content, {'status': 'error', 'toast_type': 'error', 'message': 'Invalid username or password.'})

    def test_login_get_request(self):
        response = self.client.get(reverse(f'{self.app_name}:login'))
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse(f'{self.app_name}:logout'))
        self.assertRedirects(response, reverse('main:home'))

    def test_profile_update_get_authenticated(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse(f'{self.app_name}:profile_update'))
        self.assertEqual(response.status_code, 200)

    def test_profile_update_unauthenticated_redirect(self):
        response = self.client.get(reverse(f'{self.app_name}:profile_update'))
        self.assertEqual(response.status_code, 302) 
        self.assertTrue(response.url.startswith('/accounts/login/'))

    def test_profile_update_post_success(self):
        self.client.login(username='testuser', password='password123')
        
        new_data = {
            'lokasi': Profile.KOTA_CHOICES[2][0],
            'instagram': '@updated_ig',
            'avatar': Profile.AVATAR_CHOICES[4][0]
        }
        response = self.client.post(reverse(f'{self.app_name}:profile_update'), new_data)
        
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.lokasi, 'Depok')
        self.assertJSONEqual(response.content, {'status': 'success', 'toast_type': 'success', 'message': 'Profile updated successfully.'})

    def test_profile_update_post_invalid_form_data(self):
        self.client.login(username='testuser', password='password123')
      
        invalid_data = {
            'lokasi': 'Mars', 
            'instagram': '@valid_ig',
            'avatar': Profile.AVATAR_CHOICES[0][0]
        }
        response = self.client.post(reverse(f'{self.app_name}:profile_update'), invalid_data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('lokasi', response.json()['errors'])
        self.assertJSONEqual(response.content, {'status': 'error', 'errors': {'lokasi': ['Select a valid choice. Mars is not one of the available choices.']}, 'toast_type': 'error', 'message': 'Failed to update profile.'})