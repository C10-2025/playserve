from django.urls import path
from review.views import add_review, review_list, view_comments, delete_review

app_name = 'review'

urlpatterns = [
    path("add-review/", add_review, name='add_review'),
    path("", review_list, name='review_list'),
    path("lapangan/<int:lapangan_id>/comments/", view_comments, name='view_comments'),
    path('review/delete-review/<int:review_id>/', delete_review, name='delete-review'),
]