from django.urls import path
from review.views import add_review, review_list

app_name = 'review'

urlpatterns = [
    path("add-review/", add_review, name='add_review'),
    path("", review_list, name='review_list'),  # Changed to root path
]