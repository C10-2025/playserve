from django.urls import path
from . import views
from main.views import proxy_image

app_name = 'main'

urlpatterns = [
    path('', views.main_view, name='home'),
    path('proxy-image/', proxy_image, name='proxy_image'),
]