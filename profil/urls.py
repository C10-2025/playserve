from django.urls import path
from . import views

app_name = 'profil'

urlpatterns = [
    path('register/', views.register1, name='register1'),
    path('register/step2/', views.register2, name='register2'),
    path('login/', views.login_ajax, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('edit/', views.profile_update_view, name='profile_update'),
    path('admin/users/', views.manage_users_view, name='manage_users'),
    path('delete-user/<int:user_id>/', views.delete_user_view, name='delete_user'),
]