from django.urls import path
from . import views

app_name = 'matchmaking'

urlpatterns = [
    # Main View
    path('dashboard/', views.matchmaking_dashboard, name='dashboard'), 

    # 2. Endpoints AJAX (ambil/proses data JSON)
    path('api/available-users/', views.get_available_users_ajax, name='api_available_users'),
    path('api/incoming-requests/', views.get_incoming_requests_ajax, name='api_incoming_requests'),
    
    # 3. Endpoints Actions (buat/ubah data)
    path('action/create-request/', views.create_match_request, name='action_create_request'),
    path('action/handle-request/', views.handle_match_request, name='action_handle_request'),
    path('action/finish-session/', views.finish_match_session, name='action_finish_session'),

    path('api/active-session/', views.get_active_session, name='api_active_session'),
]