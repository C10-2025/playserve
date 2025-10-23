from django.urls import path
import community.views as views

urlpatterns = [
    path('', views.discover_communities, name='discover_communities'),
    path('join/<int:community_id>/', views.join_community, name='join_community'),
    path('my/', views.my_communities, name='my_communities'),
    path('<int:community_id>/', views.community_detail, name='community_detail'),
    path('<int:community_id>/create_post/', views.create_post, name='create_post'),
    path('reply/<int:post_id>/', views.create_reply, name='create_reply'),

    path('create/', views.create_community, name='create_community'),
    path('<int:community_id>/update/', views.update_community, name='update_community'),
    path('<int:community_id>/delete/', views.delete_community, name='delete_community'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('reply/<int:reply_id>/delete/', views.delete_reply, name='delete_reply'),


]
