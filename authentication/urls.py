from django.urls import path
from authentication.views import login, register_step1, register_step2

app_name = 'authentication'

urlpatterns = [
    path('login/', login, name='login'),
    path('register/step1/', register_step1, name='register_step1'),
    path('register/step2/', register_step2, name='register_step2'),
]