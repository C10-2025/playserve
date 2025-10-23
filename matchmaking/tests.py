import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from profil.models import Profile
from matchmaking.models import MatchRequest, MatchSession 
from matchmaking.views import create_match_request, handle_match_request, finish_match_session

class MatchmakingViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.user_a = User.objects.create_user(username='A_Tester', password='testpassword')
        self.user_b = User.objects.create_user(username='B_Opponent', password='testpassword')
        self.user_c = User.objects.create_user(username='C_Distant', password='testpassword')
        self.user_d = User.objects.create_user(username='D_Extra', password='testpassword')
        
        self.profile_a = Profile.objects.create(user=self.user_a, lokasi='Jakarta', jumlah_kemenangan=15) 
        self.profile_b = Profile.objects.create(user=self.user_b, lokasi='Jakarta', jumlah_kemenangan=18) 
        self.profile_c = Profile.objects.create(user=self.user_c, lokasi='Bogor', jumlah_kemenangan=5)    
        self.profile_d = Profile.objects.create(user=self.user_d, lokasi='Jakarta', jumlah_kemenangan=15) 

        self.create_req_url = reverse('matchmaking:action_create_request')
        self.handle_req_url = reverse('matchmaking:action_handle_request')
        self.finish_sess_url = reverse('matchmaking:action_finish_session')
        
        self.client.login(username='A_Tester', password='testpassword')

    def test_01_create_request_success_and_duplication_check(self):
        response = self.client.post(self.create_req_url, 
                                    json.dumps({'receiver_id': self.user_b.id}), 
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(MatchRequest.objects.filter(sender=self.user_a, receiver=self.user_b, status='PENDING').exists())

        response = self.client.post(self.create_req_url, 
                                    json.dumps({'receiver_id': self.user_b.id}), 
                                    content_type='application/json')
        self.assertEqual(response.status_code, 409)

    def test_02_re_request_after_rejection_is_allowed(self):
        MatchRequest.objects.create(sender=self.user_a, receiver=self.user_b, status='REJECTED')

        response = self.client.post(self.create_req_url, 
                                    json.dumps({'receiver_id': self.user_b.id}), 
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(MatchRequest.objects.filter(sender=self.user_a, receiver=self.user_b, status='PENDING').count(), 1)


    def test_03_handle_request_accept_and_autocancel_logic(self):
        request_a_b = MatchRequest.objects.create(sender=self.user_a, receiver=self.user_b, status='PENDING')
        request_a_d = MatchRequest.objects.create(sender=self.user_a, receiver=self.user_d, status='PENDING')
        request_c_a = MatchRequest.objects.create(sender=self.user_c, receiver=self.user_a, status='PENDING')

        response = self.client.post(self.handle_req_url,
                                    json.dumps({'request_id': request_c_a.id, 'action': 'ACCEPT'}),
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(MatchSession.objects.filter(player1=self.user_c, player2=self.user_a).exists())
        self.assertEqual(MatchRequest.objects.get(id=request_c_a.id).status, 'ACCEPTED')
        
        request_a_b.refresh_from_db() 
        self.assertEqual(request_a_b.status, 'AUTO_CANCELLED')
        
        request_a_d.refresh_from_db()
        self.assertEqual(request_a_d.status, 'AUTO_CANCELLED')
        
    def test_04_finish_session_win_updates_profile_correctly(self):
        session = MatchSession.objects.create(player1=self.user_a, player2=self.user_b, result='PENDING')
        
        initial_wins = self.profile_a.jumlah_kemenangan

        response = self.client.post(self.finish_sess_url,
                                    json.dumps({'session_id': session.id, 'action': 'WIN'}),
                                    content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        self.profile_a.refresh_from_db()

        self.assertEqual(self.profile_a.jumlah_kemenangan, initial_wins + 1)
        
        session_2 = MatchSession.objects.create(player1=self.user_a, player2=self.user_d, result='PENDING')
        response = self.client.post(self.finish_sess_url,
                                    json.dumps({'session_id': session_2.id, 'action': 'WIN'}),
                                    content_type='application/json')
        
        self.profile_a.refresh_from_db()
        self.assertEqual(self.profile_a.jumlah_kemenangan, initial_wins + 2)