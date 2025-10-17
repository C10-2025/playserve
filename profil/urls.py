from django.urls import path
from . import views

app_name = 'profil'

urlpatterns = [
    path('register/', views.register1, name='register1'),
    path('register/step2/', views.register2, name='register2'),
    path('login/', views.login_ajax, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.profile_update_view, name='profile_update'),
]