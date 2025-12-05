from django.urls import path
from authentication.views import login, check_login, register_step1, register_step2, logout, edit_profile, get_user, delete_profile, check_admin_status

app_name = 'authentication'

urlpatterns = [
    path('login/', login, name='login'),
    path('check_login/', check_login, name='check_login'),
    path('register/step1/', register_step1, name='register_step1'),
    path('register/step2/', register_step2, name='register_step2'),
    path('logout/', logout, name='logout'),
    path('edit_profile/', edit_profile, name='edit_profile'),
    path('get_user/', get_user, name='get_user'),
    path('delete_profile/', delete_profile, name='delete_profile'),
    path("check_admin_status/", check_admin_status, name="check_admin_status"),
]